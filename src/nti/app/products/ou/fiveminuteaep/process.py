#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.app.products.ou import MessageFactory as _

from datetime import datetime

import zope.intid

from zope import component
from zope import interface
from zope.event import notify
from zope import lifecycleevent

from nti.contenttypes.courses.interfaces import ES_CREDIT_NONDEGREE

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseSubInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser

from nti.externalization.interfaces import LocatedExternalDict

from nti.utils.maps import CaseInsensitiveDict

from ..courseware.utils import drop_any_other_enrollments

from .model import PaymentRecord

from .utils import is_true
from .utils import is_false
from .utils import safe_compare
from .utils import get_course_key
from .utils import is_fmaep_capable
from .utils import get_fmaep_key_from_course

from .utils.net import to_json
from .utils.net import response_map
from .utils.net import DEFAULT_TIMEOUT
from .utils.net import request_session as net_request_session

from .interfaces import STATE
from .interfaces import FAILED
from .interfaces import STATUS
from .interfaces import PENDING
from .interfaces import MESSAGE
from .interfaces import SUCCESS
from .interfaces import ADMITTED
from .interfaces import REJECTED
from .interfaces import SUSPENDED
from .interfaces import IFMAEPUser
from .interfaces import IPaymentStorage
from .interfaces import UserAdmittedEvent
from .interfaces import UserRejectedEvent
from .interfaces import IUserAdmissionData
from .interfaces import UserAdmisionPendingEvent
from .interfaces import UserAdmisionSuspendedvent

from . import get_url_map
from . import get_credentials
from . import IS_PAY_DONE_URL

URL = u'URL'
IDENTIFIER = u'Identifier'

def get_uid(obj):
	intids = component.getUtility(zope.intid.IIntIds)
	result = intids.getId(obj)
	return result

def request_session(url=None, tlsv1=True, auth=True, timeout=DEFAULT_TIMEOUT):
	credentials = get_credentials() if auth else None
	result = net_request_session(url, tlsv1=tlsv1, credentials=credentials,
								 timeout=timeout)
	return result

def get_user(user):
	if user is not None:
		result = User.get_user(str(user)) if not IUser.providedBy(user) else user
		return result
	return None

def set_user_state(user, state, PIDM=None, tempmatchid=None, message=None, event=True):
	admin_data = IUserAdmissionData(user)
	if not state:
		admin_data.state = admin_data.tempmatchid = admin_data.PIDM = None
		interface.noLongerProvides(user, IFMAEPUser)
		logger.warn('User not admitted. Possible Server/technical failure. %s', message)
	elif safe_compare(state, ADMITTED):
		if not PIDM:
			raise ValueError("No PIDM was specified for an admitted state")
		admin_data.PIDM = PIDM
		admin_data.state = ADMITTED
		admin_data.tempmatchid = None
		interface.alsoProvides(user, IFMAEPUser)
		if event:
			notify(UserAdmittedEvent(user, message))
		logger.info('User %s admitted with PIDM %s', user, admin_data.PIDM)
	elif safe_compare(state, PENDING):
		if not tempmatchid:
			raise ValueError("No tempmatchid was specified for a pending state")
		admin_data.PIDM = None
		admin_data.state = PENDING
		admin_data.tempmatchid = tempmatchid
		interface.alsoProvides(user, IFMAEPUser)
		if event:
			notify(UserAdmisionPendingEvent(user, message))
		logger.warn('User %s admission state set to pending. tempmatchid %s', user,
					admin_data.tempmatchid)
	elif safe_compare(state, SUSPENDED):
		if not tempmatchid:
			raise ValueError("No tempmatchid was specified for a suspended state")
		admin_data.PIDM = None
		admin_data.state = SUSPENDED
		admin_data.tempmatchid = tempmatchid
		interface.alsoProvides(user, IFMAEPUser)
		if event:
			notify(UserAdmisionSuspendedvent(user, message))
		logger.warn("User %s admission state set to suspended", user)
	elif safe_compare(state, REJECTED):
		admin_data.state = REJECTED
		admin_data.tempmatchid = admin_data.PIDM = None
		interface.noLongerProvides(user, IFMAEPUser)
		if event:
			notify(UserRejectedEvent(user, message))
		logger.warn("User %s admission state set to rejected. %s", user, message)

def process_admission(user, external, admit_url=None):
	session = request_session(admit_url)
	session.headers['content-type'] = 'application/json'
	response = session.post(admit_url, data=to_json(external))
	logger.info("admission response status code %s", response.status_code)

	res_map = response_map(response)
	logger.info('process admission server response %r', res_map)

	result = LocatedExternalDict()
	result.update(res_map)
	result[URL] = admit_url

	status = result.get(STATUS, None)
	message = result.get(MESSAGE, None)
	admin_data = IUserAdmissionData(user)
	identifier = result.get(IDENTIFIER, None)

	if status == 201 and admin_data.state != ADMITTED: # admitted
		set_user_state(user, ADMITTED, PIDM=identifier, message=message)
	elif status == 202 and admin_data.state != PENDING:
		set_user_state(user, PENDING, tempmatchid=identifier, message=message)
	elif status == 400 and admin_data.state != None:
		set_user_state(user, state=None, message=message)
	elif status == 403 and admin_data.state != REJECTED:
		set_user_state(user, REJECTED, message=message)
	elif status == 409:
		logger.error("Possible exact match? Already admitted?. %s admission state %s. %s",
					 user, admin_data.state, message)
	elif status == 422:
		logger.error("Invalid data. %s", message)
		set_user_state(user, state=None, message=message)
	elif status == 500:
		logger.error("Server error. %s", message)
	else:
		logger.info("Server response. %s", message)
	result[STATE] = admin_data.state
	return result

def query_admission(user, tempmatchid=None, admit_url=None, event=True):
	admin_data = IUserAdmissionData(user)
	tempmatchid = admin_data.tempmatchid if not tempmatchid else tempmatchid
	if not tempmatchid:
		raise ValueError("not tempmatch id")

	janux_url = '%s/%s' % (admit_url, tempmatchid)
	session = request_session(janux_url)
	response = session.post(janux_url)
	logger.info("query admission response status code %s", response.status_code)

	result = LocatedExternalDict()
	result.update(response_map(response))
	result[URL] = janux_url

	status = result.get(STATUS, None)
	message = result.get(MESSAGE, None)
	if status == 403:
		if not message:
			result[MESSAGE] = _("The tempmatch id requested is unknown or invalid")
			logger.error("The identifier '%s' is unknown or invalid", tempmatchid)
		else:
			logger.error(message)

		if admin_data.state != REJECTED:
			set_user_state(user, REJECTED, message=message, event=event)
	else:
		if status == 202 and admin_data.state not in (SUSPENDED, PENDING): # suspended
			set_user_state(user, SUSPENDED, tempmatchid=tempmatchid, message=message, event=event)
		elif status == 201 and admin_data.state != ADMITTED: # admitted
			set_user_state(user, ADMITTED, PIDM=result[IDENTIFIER], message=message, event=event)
		else:
			logger.error(message)
	return result

def account_status(user, pidm=None, account_status_url=None, event=True):
	admin_data = IUserAdmissionData(user)
	pidm = admin_data.PIDM if not pidm else pidm
	if not pidm:
		raise ValueError("PIDM not specified")

	janux_url = '%s/%s' % (account_status_url, pidm)
	session = request_session(janux_url)
	response = session.get(janux_url)
	logger.info("account status response status code %s", response.status_code)

	result = LocatedExternalDict()
	result.update(response_map(response))
	result[URL] = janux_url

	state = result.get(STATE, None)
	status = result.get(STATUS, None)
	message = result.get(MESSAGE, None)
	if status == 200:
		if safe_compare(state, ADMITTED) and admin_data.state != ADMITTED:
			set_user_state(user, ADMITTED, PIDM=result[IDENTIFIER], message=message,
						   event=event)
		elif safe_compare(state, REJECTED, SUSPENDED) and \
			 admin_data.state not in (REJECTED, SUSPENDED):
			set_user_state(user, REJECTED, message=message, event=event)
	elif status == 403 and admin_data.state not in (REJECTED, SUSPENDED):
		if not message:
			message = result[MESSAGE] = _("The PIDM requested is unknown or invalid")
			logger.error("The identifier '%s' is unknown or invalid", pidm)
		else:
			logger.error(message)

		if pidm == admin_data.PIDM:
			logger.warn("PIDM in profile no longer valid")
			set_user_state(user, REJECTED, message=message, event=event)
	else:
		logger.error(message)
	return result

def find_ou_courses():
	courses = CaseInsensitiveDict()
	sections = CaseInsensitiveDict()
	catalog = component.getUtility(ICourseCatalog)
	for catalog_entry in catalog.iterCatalogEntries():
		course_instance = ICourseInstance(catalog_entry)
		if is_fmaep_capable(course_instance):
			course_key = get_fmaep_key_from_course(course_instance)
			if not course_key:
				continue
			# check the proper map
			m = sections if ICourseSubInstance.providedBy(course_instance) else courses
			if course_key not in m: # pragma: no cover
				m[course_key] = course_instance
			else:
				raise KeyError("Duplicate course_key %s", course_key)

	# remove anything w/ the same key in sections
	for key in courses.keys():
		sections.pop(key, None)

	result = courses
	result.update(sections)
	return result

def update_member_enrollment(course_instance, user):
	# drop any other enrollments
	drop_any_other_enrollments(course_instance, user)
	
	# enroll properly
	enrollments = ICourseEnrollments(course_instance)
	enrollment_manager = ICourseEnrollmentManager(course_instance)
	enrollment = enrollments.get_enrollment_for_principal(user)
	if enrollment is None: 	# Never before been enrolled
		enrollment_manager.enroll(user, scope=ES_CREDIT_NONDEGREE)
	else:
		# XXX: This branch isn't tested
		logger.info("User %s now paying for course (old_scope %s)",
					user, enrollment.Scope)
		enrollment.Scope = ES_CREDIT_NONDEGREE
		# Must announce it so that permissions get updated
		lifecycleevent.modified(enrollment)
	return True

def enrolled_courses(user, pidm=None, enroll_courses_url=None):
	admin_data = IUserAdmissionData(user)
	pidm = admin_data.PIDM if not pidm else pidm
	if not pidm:
		raise ValueError("PIDM not specified")

	janux_url = "%s/%s" % (enroll_courses_url, pidm)
	session = request_session(janux_url)
	response = session.get(janux_url)
	logger.info("enrolled courses response status code %s", response.status_code)

	result = LocatedExternalDict()
	result.update(response_map(response))
	result[URL] = janux_url

	status = result.get(STATUS, None)
	message = result.get(MESSAGE, None)
	if status in (403,500):
		if status == 403:
			logger.warn("%s is not a valid PIDM", pidm)
		elif status == 500:
			logger.error("Server error %s", message)
		return result
	elif status == 501:
		if not message:
			result[MESSAGE] = _('Unexpected reply from server')
			logger.error('Unexpected reply from server')
		else:
			logger.error(message)
		return result

	items = result['Items'] = []
	course_map = find_ou_courses()
	enrolled = result.pop('Courses', ())
	for course in enrolled:
		crn = course.get('CRN', None)
		term_code = course.get('Term', None)
		course_key = get_course_key(crn, term_code)
		course_instance = course_map.get(course_key)
		if course_instance is not None:
			items.append(course_instance)
		else:
			logger.warn("Course %s,%s was not found", crn, term_code)
	return result

def course_details(crn, term_code, course_details_url=None):
	session = request_session(course_details_url)
	session.params['crn'] = crn
	session.params['term_code'] = term_code
	response = session.get(course_details_url)
	logger.info("course details response status code %s", response.status_code)

	result = LocatedExternalDict()
	result.update(response_map(response))

	status = result.get(STATUS, None)
	if status >= 300:
		logger.error(result.get(MESSAGE))
	return result

def is_pay_done(user, pidm, crn, term_code, is_pay_done_url):
	session = request_session(is_pay_done_url)
	session.params['crn'] = crn
	session.params['pidm'] = pidm
	session.params['term_code'] = term_code
	response = session.get(is_pay_done_url)
	logger.info("is pay done response status code %s", response.status_code)

	# log respons
	res_map = response_map(response)
	logger.info('is pay done server response %r', res_map)

	result = LocatedExternalDict()
	result.update(res_map)
	result[URL] = is_pay_done_url

	state = result.get(STATE, None)
	status = result.get(STATUS, None)
	message = result.get(MESSAGE, None)
	key = get_course_key(crn, term_code)

	# handle the case where the message field has actual
	# state of the query
	if status == 200 and not state and safe_compare(message, 'true', 'false'):
		state = message
		logger.warn("State adjusted to %s", state)

	if status != 200:
		logger.error(message)
	elif is_true(state):
		result[STATE] = True
		storage = IPaymentStorage(user)
		record = storage.get(key)
		if record is None: # how do we get here?
			record = PaymentRecord()
			record.attempts = 1
			record.started = datetime.utcnow()
			storage[key] = record
		# record success
		record.state = SUCCESS
		record.updateLastMod()
		record.completed = datetime.utcnow()
	elif is_false(state) or is_false(message):
		result[STATE] = False
		storage = IPaymentStorage(user)
		if key in storage:
			del storage[key] # delete record
	else:
		logger.error("Unknown or missing state. %r", result)
	return result

def payment_completed(user, pidm, crn, term_code):
	user = get_user(user)
	is_pay_done_url = get_url_map()[IS_PAY_DONE_URL]
	result = is_pay_done(user, pidm, crn, term_code, is_pay_done_url=is_pay_done_url)
	state = result.get(STATE, None)
	if state is None:
		logger.warn("cannnot execute enrollment due to missing state")
	elif state == True:
		course_map = find_ou_courses()
		course_key = get_course_key(crn, term_code)
		course_instance = course_map.get(course_key)
		if course_instance is None:
			logger.warn("Course %s,%s could not be found", crn, term_code)
		elif ICourseInstance.providedBy(course_instance):
			update_member_enrollment(course_instance, user)
		logger.info("%s made a successful payment for %s, %s", user, crn, term_code)
	elif state == False:
		logger.warn("Payment for course %s,%s failed", crn, term_code)
	return result

def process_pay(user, pidm, crn, term_code, return_url, pay_url):

	data = {'pidm':pidm, 'crn':crn, 'term_code': term_code,
			'return_url':return_url }

	session = request_session(pay_url)
	session.headers['content-type'] = 'application/json'
	response = session.post(pay_url, data=to_json(data))
	logger.info("payment response status code %s", response.status_code)

	result = CaseInsensitiveDict()
	result.update(response_map(response))
	result[STATE] = FAILED

	status = result.get(STATUS, None)
	message = result.get(MESSAGE, None)
	course_key = get_course_key(crn, term_code)
	if status == 202:
		result[STATE] = SUCCESS		
		# create payment record
		payURL = result[URL]
		storage = IPaymentStorage(user)
		record = storage.get(course_key)
		if record is None: 
			record = PaymentRecord(state=PENDING, started=datetime.utcnow(), 
							   	   payURL=payURL, attempts=1)
			storage[course_key] = record
		else:
			record.attempts += 1
			record.payURL = payURL
			record.updateLastMod()
		logger.info("Redirecting to pay URL %s", payURL)
	elif status == 403:
		logger.warn("You already pay for this course")
		payment_completed(user, pidm, crn, term_code)
	else:
		logger.error("Unexpected response %s", message)
	return result

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.app.products.ou import MessageFactory as _

import re
import sys
import urllib
import isodate
from datetime import datetime
from urlparse import urljoin, urlparse

from zope import schema
from zope.schema.interfaces import ValidationError

from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.error import handle_validation_error
from nti.app.externalization.error import raise_json_error as raise_error
from nti.app.externalization.error import handle_possible_validation_error
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver.users import User
from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth
from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import EmailAddressInvalid

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields

from nti.schema.interfaces import InvalidValue
from nti.schema.jsonschema import JsonSchemafier

from nti.utils.property import LazyOnClass
from nti.utils.maps import CaseInsensitiveDict

from ..views import JanuxPathAdapter

from .utils import is_true
from .utils import is_false
from .utils import safe_compare
from .utils import get_course_key
from .utils.geo import get_states
from .utils.geo import get_countries
from .utils.cypher import create_token
from .utils.cypher import get_plaintext
from .utils.links import create_fmaep_link

from .model import UserAdmissionProfile

from .interfaces import STATE
from .interfaces import FAILED
from .interfaces import STATUS
from .interfaces import SUCCESS
from .interfaces import IPaymentStorage
from .interfaces import IUserAdmissionData
from .interfaces import IUserAdmissionProfile

from .process import is_pay_done
from .process import process_pay
from .process import account_status
from .process import course_details
from .process import find_ou_courses
from .process import query_admission
from .process import enrolled_courses
from .process import payment_completed
from .process import process_admission

from . import get_url_map

from . import ADMIT_URL
from . import IS_PAY_DONE_URL
from . import ACCOUNT_STATUS_URL
from . import COURSE_DETAILS_URL
from . import PAY_AND_ENROLL_URL
from . import ENROLLED_COURSES_URL

LINKS = StandardExternalFields.LINKS

UNITED_STATES = u'United States'

# Admission

def _check_email(email, request, field):
	try:
		checkEmailAddress(email)
	except EmailAddressInvalid, e:
		exc_info = sys.exc_info()
		raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{ 	'message': _("Please provide a valid ${field}.",
									 mapping={'field': field} ),
						'field': field,
						'code': e.__class__.__name__ },
					exc_info[2])

def _validate_nation(name, request, field):
	countries = get_countries()
	if not name or name not in countries:
		raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{ 	'message': _("Please provide a valid ${field}.",
									 mapping={'field': field} ),
						'field': field
					}, None)
	return countries[name].upper()

def _validate_state(name, request, field):
	states = get_states()
	if not name or name not in states:
		raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{ 	'message': _("Please provide a valid ${field}.",
									 mapping={'field': field} ),
						'field': field
					}, None)
	return states[name].upper()

def convert_bool(v):
	if is_true(v):
		v = u'Y'
	elif is_false(v):
		v = u'N'
	return v

def _validate_user_data(data, request, user=None):
	data.pop('PIDM', None)
	bool_data = {	'high_school_graduate': 'Y',
					'attended_other_institution' : None,
					'still_attending': None,
					'good_academic_standing': None,
					'bachelors_or_higher': None,
					'is_seeking_ou_credit': 'Y',
					'is_currently_attending_ou': 'Y',
					'is_currently_attending_highschool': 'N'}

	placeholder_data = {'years_of_oklahoma_residency': 0}
	placeholder_data.update(bool_data)

	for k, v in placeholder_data.items():
		if k not in data:
			data[k] = v

	for k in bool_data.keys():
		data[k] = convert_bool(data[k])

	# birthdate
	try:
		date_of_birth = data.pop('date_of_birth', None)
		date_of_birth = isodate.parse_date(date_of_birth)
	except (TypeError, isodate.ISO8601Error, ValueError) as e:
		exc_info = sys.exc_info()
		raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{	'message': _("Please provide a valid birthdate."),
						'field': 'date_of_birth',
						'code': e.__class__.__name__ },
					exc_info[2])

	if datetime(*(date_of_birth.timetuple()[:6])) >= datetime.utcnow():
		raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{	'message': _("Birthdate cannot be in the future."),
						'field': 'date_of_birth'},
					None)

	# sooner_id
	value = data.get( 'sooner_id' )
	if value and len( value ) > 9:
		raise_error(request,
			hexc.HTTPUnprocessableEntity,
			{	'message': _("Must provide a valid Sooner ID."),
				'field': 'sooner_id' },
			None)

	# email
	_check_email(data.get('email'), request, 'email')

	# address
	for name in ('street_line1', 'city'):
		value = data.get(name)
		if not value:
			raise_error(request,
				hexc.HTTPUnprocessableEntity,
				{	'message': _("Must provide a valid address."),
					'field': name },
				None)

	# If they passed us a mailing address, validate it separately.
	if data.pop( 'has_mailing_address', None ):
		for name in ('mailing_street_line1', 'mailing_city'):
			value = data.get(name)
			if not value:
				raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{	'message': _("Must provide a valid mailing address."),
						'field': name },
					None)
	else:
		# No mailing address, sub all of our address fields in.
		for name in ('street_line1', 'street_line2', 'street_line3', 'street_line4',
					 'street_line5', 'city', 'state', 'postal_code', 'nation_code'):
			value = data.get(name)
			mailing_name ='mailing_%s' % name
			data[mailing_name] = value

	code = _validate_nation(data.get('nation_code'), request, 'nation')
	data['nation_code'] = code

	code = _validate_nation(data.get('mailing_nation_code'), request, 'mailing nation')
	data['mailing_nation_code'] = code

	state = data.get('state')
	if state:
		code = _validate_state(state, request, 'state')
		data['state'] = code

	mailing_state = data.get('mailing_state')
	if mailing_state:
		code = _validate_state(mailing_state, request, 'mailing state')
		data['mailing_state'] = code

	if not data.get('country_of_citizenship'):
		raise_error(request,
				hexc.HTTPUnprocessableEntity,
				{	'message': _("Must provide a valid country of citizenship."),
					'field': 'country_of_citizenship' },
				None)
	else:
		nation = data.get('country_of_citizenship')
		code = _validate_nation(nation, request, 'country of citizenship')
		data['country_of_citizenship'] = code

	ssn = data.get('social_security_number')
	if ssn and not re.search('[0-9]{9}', ssn):
		raise_error(request,
					hexc.HTTPUnprocessableEntity,
					{	'message': _("Invalid social security number."),
						'field': 'social_security_number'},
					None)
	elif not ssn:
		data.pop('social_security_number', None)

	years_of_oklahoma_residency = data.get('years_of_oklahoma_residency', '0')
	try:
		int(years_of_oklahoma_residency)
		data['years_of_oklahoma_residency'] = years_of_oklahoma_residency
	except ValueError as e:
		raise_error(
			request,
			hexc.HTTPUnprocessableEntity,
			{	'message': _("Must provide a valid number of years of Oklahoma residency."),
				'field': 'years_of_oklahoma_residency',
				'code': e.__class__.__name__ },
			None)

	try:
		converted_date = date_of_birth.strftime('%m/%d/%Y')
	except ValueError as e:
		raise_error(
			request,
			hexc.HTTPUnprocessableEntity,
			{	'message': _("Please provide a valid birthdate."),
				'field': 'date_of_birth',
				'code': e.__class__.__name__ },
			None)

	try:
		profile = UserAdmissionProfile()
		for name, value in list(data.items()):
			if name in IUserAdmissionProfile:
				setattr(profile, name, value)
			else:
				data.pop(name)

		# set data of birth
		profile.date_of_birth = date_of_birth
		errors = schema.getValidationErrors(IUserAdmissionProfile, profile)
		if errors:
			__traceback_info__ = errors
			try:
				raise errors[0][1]
			except schema.interfaces.SchemaNotProvided as e:
				exc_info = sys.exc_info()
				if not e.args: # zope.schema doesn't fill in the details, which sucks
					e.args = (errors[0][0],)
				raise exc_info[0], exc_info[1], exc_info[2]

		# set back date
		data['date_of_birth'] = converted_date
	except ValidationError as e:
		handle_validation_error(request, e)
	except InvalidValue as e:
		handle_validation_error(request, e)
	except Exception as e:
		handle_possible_validation_error(request, e)

	return data, profile

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_admission_preflight',
			 renderer='rest',
			 request_method='POST',
			 permission=nauth.ACT_READ,
			 context=JanuxPathAdapter)
class AdmissionPreflightView(AbstractAuthenticatedView,
						 	 ModeledContentUploadRequestUtilsMixin):
	def _do_call(self):
		externalValue = self.readInput()
		externalValue, _ = _validate_user_data(externalValue, self.request)
		ext_schema = JsonSchemafier(IUserAdmissionProfile).make_schema()
		self.request.response.status_int = 200
		return LocatedExternalDict({'ProfileSchema': ext_schema,
									'Input': externalValue})

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_admission',
			 renderer='rest',
			 request_method='POST',
			 permission=nauth.ACT_READ,
			 context=JanuxPathAdapter)
class AdmissionView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def _do_call(self):
		admin_data = IUserAdmissionData(self.remoteUser)
		if admin_data.is_admitted():
			logger.warn("%s already admitted", self.remoteUser)
			raise hexc.HTTPConflict("User already admitted")
		elif admin_data.is_pending() or admin_data.is_suspended():
			logger.warn("%s has already submitted an admission request", self.remoteUser)
			raise hexc.HTTPConflict("Admission in pending state")

		data = self.readInput()
		data, _ = _validate_user_data(data, self.request, self.remoteUser)
		try:
			admit_url = get_url_map()[ADMIT_URL]
			result = process_admission(self.remoteUser, data, admit_url=admit_url)
			if admin_data.is_admitted():
				# this is done in the context of a course
				# return links for the client
				links = result.setdefault(LINKS, [])
				links.append(create_fmaep_link(self.remoteUser, 'fmaep_pay_and_enroll'))
			self.request.response.status_int = result[STATUS]
		except ValueError as e:
			logger.exception("Invalid input data")
			raise hexc.HTTPUnprocessableEntity(str(e))
		except Exception:
			logger.exception('Could not connect to server')
			raise hexc.HTTPServerError("Error while connecting to server")
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_query_admission',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_READ,
			 context=JanuxPathAdapter)
class QueryAdmissionView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		admission_data = IUserAdmissionData(self.remoteUser)
		request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
		tempmatchid = admission_data.tempmatchid if not len(request.subpath) == 1 else request.subpath[0]
		if not tempmatchid:
			raise hexc.HTTPUnprocessableEntity("Must provide a tempmatchid")
		elif not safe_compare(tempmatchid, admission_data.tempmatchid):
			raise hexc.HTTPUnauthorized("Specified tempmatchid is not for this user")

		try:
			admit_url = get_url_map()[ADMIT_URL]
			result = query_admission(self.remoteUser, tempmatchid, admit_url=admit_url)
			self.request.response.status_int = result[STATUS]
		except ValueError as e:
			raise hexc.HTTPUnprocessableEntity(str(e))
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_account_status',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_READ,
			 context=JanuxPathAdapter)
class AccountStatusCheckView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		admission_data = IUserAdmissionData(self.remoteUser)
		pidm = admission_data.PIDM if not len(request.subpath) == 1 else request.subpath[0]
		if not pidm:
			raise hexc.HTTPUnprocessableEntity("Must provide a PIDM")
		elif not safe_compare(pidm, admission_data.PIDM):
			raise hexc.HTTPUnauthorized("Specified PIDM is not for this user")

		self.request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
		try:
			account_status_url = get_url_map()[ACCOUNT_STATUS_URL]
			result = account_status(self.remoteUser, pidm,
									account_status_url=account_status_url)
			self.request.response.status_int = result[STATUS]
		except ValueError as e:
			raise hexc.HTTPUnprocessableEntity(str(e))
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_country_names',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter)
class CountryNamesView(object):

	def __init__(self, request):
		self.request = request

	@LazyOnClass
	def countries(self):
		result = LocatedExternalList(get_countries().keys())
		result.sort()
		try:
			result.pop(result.index(UNITED_STATES))
			result.insert(0, UNITED_STATES)
		except ValueError:
			pass
		return result

	def __call__(self):
		return self.countries

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_state_names',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter)
class StateNamesView(object):

	def __init__(self, request):
		self.request = request

	@LazyOnClass
	def states(self):
		result = LocatedExternalList(get_states().keys())
		return result

	def __call__(self):
		return self.states

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_enrolled_courses',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter)
class EnrolledCoursesView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		admission_data = IUserAdmissionData(self.remoteUser)
		pidm = admission_data.PIDM if not len(request.subpath) == 1 else request.subpath[0]
		if not pidm:
			raise hexc.HTTPUnprocessableEntity("Must provide a PIDM")
		if not safe_compare(pidm, admission_data.PIDM):
			raise hexc.HTTPUnauthorized("Specified PIDM is not for this user")
		try:
			enroll_courses_url = get_url_map()[ENROLLED_COURSES_URL]
			result = enrolled_courses(self.remoteUser, pidm,
									  enroll_courses_url=enroll_courses_url)
			self.request.response.status_int = result[STATUS]
		except ValueError as e:
			logger.exception(e)
			raise hexc.HTTPUnprocessableEntity(str(e))
		except Exception, e:
			logger.exception(e)
			raise hexc.HTTPServerError(str(e))
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_course_details',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter)
class CourseDetailsView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		params = CaseInsensitiveDict(request.params)
		crn = params.get('CRN')
		term_code = params.get('term_code') or params.get('term') or params.get('termcode')
		__traceback_info__ = crn, term_code
		if not crn:
			raise hexc.HTTPUnprocessableEntity("Must provide a CRN")
		if not term_code:
			raise hexc.HTTPUnprocessableEntity("Must provide a term code")

		course_details_url = get_url_map()[COURSE_DETAILS_URL]
		result = course_details(crn, term_code,course_details_url=course_details_url)
		self.request.response.status_int = result.get(STATUS) or 200
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_is_pay_done',
			 renderer='rest',
			 request_method='POST',
			 context=JanuxPathAdapter)
class IsPayDoneView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		admission_data = IUserAdmissionData(self.remoteUser)
		data = CaseInsensitiveDict(self.readInput())
		crn = data.get('CRN')
		term_code = data.get('term_code') or data.get('termcode') or data.get('term')
		__traceback_info__ = crn, term_code
		if not crn:
			raise hexc.HTTPUnprocessableEntity("Must provide a CRN")
		if not term_code:
			raise hexc.HTTPUnprocessableEntity("Must provide a term code")

		pidm = data.get('pidm') or admission_data.PIDM
		if not pidm:
			raise hexc.HTTPUnprocessableEntity("Must provide a PIDM")
		elif not safe_compare(pidm, admission_data.PIDM):
			raise hexc.HTTPUnauthorized("Specified PIDM is not for this user")

		is_pay_done_url = get_url_map()[IS_PAY_DONE_URL]
		result = is_pay_done(self.remoteUser, pidm, crn, term_code,
							 is_pay_done_url=is_pay_done_url)
		self.request.response.status_int = result[STATUS]
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_payment_completed',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter)
class PaymentCompletedView(object):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		params = self.request.params
		username = params.get('username', u'')
		user = User.get_user(username)
		if not user:
			raise hexc.HTTPUnprocessableEntity("Invalid user in request")
		username = username.lower()

		ciphertext = params.get('token')
		if not ciphertext:
			raise hexc.HTTPUnprocessableEntity("No token in request")

		try:
			plaintext = get_plaintext(user, ciphertext)
		except Exception:
			raise hexc.HTTPUnprocessableEntity("Invalid token")

		splits = plaintext.split("\t")
		name, pidm, crn, term_code, return_url, timestamp = splits
		if name != username:
			raise hexc.HTTPUnprocessableEntity("Invalid user in token")
	
		__traceback_info__ = (username, pidm, crn, term_code, return_url, timestamp)
		# We may be upgrading from an open enrollment status.
		self.request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
		result = payment_completed(user, pidm, crn, term_code )

		# return to orignal url
		params = urllib.urlencode({STATE:result.get(STATE, FAILED)})
		if urlparse(return_url)[4]:
			return_url = return_url + '&' + params
		else:
			return_url = return_url + '?' + params
		return hexc.HTTPFound(location=return_url)

@view_config(name='fmaep_pay')
@view_config(name='fmaep_pay_and_enroll')
@view_defaults(route_name='objects.generic.traversal',
			   name='fmaep_pay',
			   renderer='rest',
			   request_method='POST',
			   context=JanuxPathAdapter)
class PayView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		data = CaseInsensitiveDict(self.readInput())
		__traceback_info__ = data

		crn = data.get('CRN')
		term_code = data.get('term_code') or data.get('termcode') or data.get('term')
		if not crn:
			raise hexc.HTTPUnprocessableEntity("Must provide a CRN")
		if not term_code:
			raise hexc.HTTPUnprocessableEntity("Must provide a term code")

		return_url = data.get('return_url')
		if not return_url:
			raise hexc.HTTPUnprocessableEntity("Must provide a return URL")

		course_key = get_course_key(crn, term_code)
		storage = IPaymentStorage(self.remoteUser)
		record = storage.get(course_key)
		if record is not None:
			if record.is_success():
				raise hexc.HTTPConflict("Course already purchased")
			else:
				logger.warn("A previous purchase request was issued (%s)", record)

		admission_data = IUserAdmissionData(self.remoteUser)
		pidm = data.get('pidm') or admission_data.PIDM
		if not pidm:
			raise hexc.HTTPUnprocessableEntity("Must provide a PIDM")
		elif not safe_compare(pidm, admission_data.PIDM):
			raise hexc.HTTPUnauthorized("Specified PIDM is not for this user")

		course_map = find_ou_courses()
		course_instance = course_map.get(course_key)
		if course_instance is None:
			logger.error("Course %s,%s could not be found", crn, term_code)
			raise hexc.HTTPNotFound("Course not found")

		ciphertext = create_token(self.remoteUser, pidm, crn, term_code, return_url)
		params = urllib.urlencode({'username': self.remoteUser.username.lower(),
								   'token': ciphertext})

		return_url = self.request.url
		return_url = return_url[:-1] if return_url.endswith('/') else return_url
		return_url = urljoin(return_url, 'fmaep_payment_completed')
		return_url = "%s?%s" % (return_url, params)

		pay_url = get_url_map()[PAY_AND_ENROLL_URL]
		result = process_pay(self.remoteUser, pidm, crn, term_code, return_url, pay_url)
		if result.get(STATE) == SUCCESS:
			url = result['url']
			self.request.response.status_int = 202
			logger.debug("Redirectig on success to %s", url)
			return Link(url, rel='redirect')
		elif result.get(STATUS) == 403:
			logger.debug("Redirectig on 403 to %s", return_url)
			self.request.response.status_int = 202
			return Link(return_url, rel='redirect')
		raise hexc.HTTPNotFound("no link to redirect")

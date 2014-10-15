#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from .. import MessageFactory as _

import isodate
import datetime

from zope import component
from zope.i18n import translate
from zope.lifecycleevent import IObjectAddedEvent

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.security.interfaces import IPrincipal
from zope.security.management import queryInteraction

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.mailer.interfaces import ITemplatedMailer

from nti.contenttypes.courses.interfaces import ICourseSubInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ES_CREDIT_NONDEGREE
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IEmailAddressable

from nti.externalization.externalization import to_external_object

from nti.intid.interfaces import IIntIdRemovedEvent

from .utils import is_fmaep_capable
from .utils import get_fmaep_key_from_course

from .interfaces import IUserAdmittedEvent
from .interfaces import IUserRejectedEvent
from .interfaces import IUserAdmisionPendingEvent
from .interfaces import IUserAdmisionSuspendedEvent

ADMITTED_CONFIRMED_SUBJECT = 'Welcome to OU!'
ADMITTANCE_STATUS_SUBJECT = 'OU Janux - Your Application Status'

def _check_fmaep(course):
	course_key = get_fmaep_key_from_course(course) 
	result = is_fmaep_capable(course) or \
			 (course_key and ICourseSubInstance.providedBy(course))
	return result

def _send_email(event, user, profile, email, args, template, subject):
	# TODO This flow is repeated in quite a few places.
	# Hopefully, we won't have to handle pre-enroll/in-progress.
	request = getattr(event, 'request', get_current_request())
	if not request or not email:
		# TODO Will we have a current_request (we fire on events)? Is it important?
		# If so, we could make sure we add it to the event.
		logger.warn("Not sending an enrollment email because of no email or request "
					"(user=%s) (email=%s)", user, email )
		return

	assert getattr(IPrincipal(profile, None), 'id', None) == user.username
	assert getattr(IEmailAddressable(profile, None), 'email', None) == email
	try:
		mailer = component.getUtility(ITemplatedMailer)
		mailer.queue_simple_html_text_email(
							template,
							subject=subject,
							recipients=[profile],
							template_args=args,
							request=request,
							package='nti.app.products.ou.fiveminuteaep')
	except Exception:
		logger.exception('Error while sending five minute enrollment email to %s', user )

def _build_base_args( event, user, profile ):
	user_ext = to_external_object(user)
	informal_username = user_ext.get('NonI18NFirstName', profile.realname) or user.username
	# TODO This is used for admittance emails.  How would
	# we determine this?
	term = 'Fall'
	args = {'profile': profile,
			'context': event,
			'user': user,
			'term': term,
			'informal_username': informal_username,
			'today': isodate.date_isoformat(datetime.datetime.now()) }
	return args

def _build_enrollment_args( event, user, profile, course ):
	args = _build_base_args( event, user, profile )

	request = getattr(event, 'request', get_current_request())
	catalog_entry = ICourseCatalogEntry(course)

	course_start_date = ''

	if catalog_entry.StartDate:
		locale = IBrowserRequest(request).locale
		dates = locale.dates
		formatter = dates.getFormatter('date', length='long')
		course_start_date = formatter.format( catalog_entry.StartDate )

	html_sig = catalog_entry.InstructorsSignature.replace('\n', "<br />")

	subject = translate(_("Welcome to ${title}",
						mapping={'title': catalog_entry.Title}))

	course_args = {	'course': catalog_entry,
					'instructors_html_signature': html_sig,
					'subject': subject,
					'course_start_date': course_start_date }
	args.update( course_args )
	return args

@component.adapter(ICourseInstanceEnrollmentRecord,IObjectAddedEvent)
def _user_enrolled(record,event):
	# We only want our type here.
	if record.Scope != ES_CREDIT_NONDEGREE:
		return

	creator = event.object.Principal
	profile = IUserProfile(creator)
	email = getattr(profile, 'email', None)
	course = record.CourseInstance
	if not _check_fmaep(course):
		return
	
	template = 'fivemeap_enrollment_confirmation_email'
	args = _build_enrollment_args( event, creator, profile, course )
	subject = args.pop('subject')

	_send_email(event, creator, profile, email, args, template, subject)

def _do_admission_email( event, subject, template ):
	creator = event.user
	profile = IUserProfile(creator)
	email = getattr(profile, 'email', None)

	args = _build_base_args( event, creator, profile )
	_send_email(event, creator, profile, email, args, template, subject)

@component.adapter(IUserAdmittedEvent)
def _user_admitted(event):
	template = 'fivemeap_admitted_email'
	subject = translate(_(ADMITTED_CONFIRMED_SUBJECT))
	_do_admission_email( event, subject, template )

@component.adapter(IUserRejectedEvent)
def _user_rejected(event):
	template = 'fivemeap_rejected_email'
	subject = translate(_(ADMITTANCE_STATUS_SUBJECT))
	_do_admission_email( event, subject, template )

@component.adapter(IUserAdmisionPendingEvent)
def _user_admission_pending(event):
	template = 'fivemeap_pending_email'
	subject = translate(_(ADMITTANCE_STATUS_SUBJECT))
	_do_admission_email( event, subject, template )

@component.adapter(IUserAdmisionSuspendedEvent)
def _user_admission_suspended(event):
	template = 'fivemeap_pending_email'
	subject = translate(_(ADMITTANCE_STATUS_SUBJECT))
	_do_admission_email( event, subject, template )

@component.adapter(ICourseInstanceEnrollmentRecord, IIntIdRemovedEvent)
def _enrollment_record_dropped(record, event):
	course = record.CourseInstance
	if course is None:
		return

	# cannot let drop the course if the scope is credit non degree
	# and either the course if 5meap capable or there is 5meap related info
	# and the course is a section
	if record.Scope == ES_CREDIT_NONDEGREE:
		# raise exception if we are in an interaction
		if _check_fmaep(course) and queryInteraction() is not None:
			raise hexc.HTTPForbidden('Cannot drop a five minute enrollment class')

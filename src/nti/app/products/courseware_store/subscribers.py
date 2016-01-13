#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import os
import six
import isodate

import pytz
from pytz import timezone

from urlparse import urljoin
from datetime import datetime
from base64 import urlsafe_b64encode

from zope import component
from zope import lifecycleevent
from zope.i18n import translate

from zope.dottedname import resolve as dottedname

from zope.event import notify

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.security.interfaces import IPrincipal

from zope.security.management import queryInteraction

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.app.products.courseware_store.interfaces import IStoreEnrollmentEvent

from nti.app.products.courseware.interfaces import ICoursesWorkspace
from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_store.interfaces import StoreEnrollmentEvent

from nti.app.products.courseware_store.purchasable import sync_purchasable_course
from nti.app.products.courseware_store.purchasable import sync_purchasable_course_choice_bundles

from nti.app.store.subscribers import safe_send_purchase_confirmation
from nti.app.store.subscribers import store_purchase_attempt_successful

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.workspaces.interfaces import IUserService

from nti.contenttypes.courses.interfaces import ES_PURCHASED

from nti.contenttypes.courses.interfaces import AlreadyEnrolledException

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import ICourseCatalogDidSyncEvent
from nti.contenttypes.courses.interfaces import ICourseVendorInfoSynchronized
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.contenttypes.courses.utils import get_enrollment_record
from nti.contenttypes.courses.utils import drop_any_other_enrollments

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IEmailAddressable

from nti.externalization.externalization import to_external_object

from nti.intid.interfaces import IIntIdRemovedEvent

from nti.invitations.interfaces import IInvitationAcceptedEvent

from nti.mailer.interfaces import ITemplatedMailer

from nti.store.store import get_gift_code
from nti.store.purchasable import get_purchasable

from nti.store.interfaces import IPurchaseAttempt
from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IGiftPurchaseAttempt
from nti.store.interfaces import IPurchaseAttemptRefunded
from nti.store.interfaces import IRedeemedPurchaseAttempt
from nti.store.interfaces import IStorePurchaseInvitation
from nti.store.interfaces import IInvitationPurchaseAttempt
from nti.store.interfaces import IPurchaseAttemptSuccessful
from nti.store.interfaces import IGiftPurchaseAttemptRedeemed

#: The package to find enrollment templates.
DEFAULT_ENROLL_PACKAGE = 'nti.app.products.courseware'

def _get_policy_package():
	"""
	Get the policy defined package for this site, useful for
	looking up site/context specific templates.
	"""
	policy = component.getUtility(ISitePolicyUserEventListener)
	return getattr( policy, 'PACKAGE', None )

def _get_entry_id( entry ):
	return entry.ProviderUniqueID.replace(' ', '').lower()

def get_template(catalog_entry, base_template, default_package=None):
	"""
	Look for a specific context defined template for this catalog
	entry.  Returns the package where this template should be found.
	"""
	package = _get_policy_package()
	package = dottedname.resolve(package)
	provider_unique_id = _get_entry_id( catalog_entry )
	full_provider_id = provider_unique_id.replace('-', '')
	template = full_provider_id + "_" + base_template

	path = os.path.join(os.path.dirname(package.__file__), 'templates')
	if not os.path.exists(os.path.join(path, template + ".pt")):
		# Full path doesn't exist; Drop our specific id part and try that
		provider_unique_prefix = provider_unique_id.split('-')[0]
		provider_unique_prefix = provider_unique_prefix.split('/')[0]
		template = provider_unique_prefix + "_" + base_template
		if not os.path.exists(os.path.join(path, template + ".pt")):
			template = base_template
	if template == base_template:
		# Use our default package if not context specific template
		# is found in our site.
		package = default_package
	return template, package

def get_user(user):
	result = User.get_user(str(user)) if user and not IUser.providedBy(user) else user
	return result

def _parent_course_instance_enrollemnt(course, user):
	enrollment = component.queryMultiAdapter((course, user),
											 ICourseInstanceEnrollment)
	if enrollment is not None:
		service = IUserService(user, None)
		workspace = ICoursesWorkspace(service, None)
		parent = workspace['EnrolledCourses'] if workspace is not None else None
		if parent is not None and not enrollment.__parent__:
			enrollment.__parent__ = parent

def _enroll(course, user, purchasable=None, request=None, check_enrollment=False):
	enrollment = get_enrollment_record(course, user)
	if enrollment is not None and enrollment.Scope == ES_PURCHASED and check_enrollment:
		raise AlreadyEnrolledException(_("You are already enrolled in this course."))

	send_event = True
	if enrollment is None or enrollment.Scope != ES_PURCHASED:
		drop_any_other_enrollments(course, user)
		if enrollment is None:  # Never before been enrolled
			enrollment_manager = ICourseEnrollmentManager(course)
			enrollment = enrollment_manager.enroll(user, scope=ES_PURCHASED,
												   context=purchasable)
			_parent_course_instance_enrollemnt(course, user)

		elif enrollment.Scope != ES_PURCHASED:
			logger.info("User %s now paying for course (old_scope %s)",
						user, enrollment.Scope)
			# change scope and mark record
			enrollment.Scope = ES_PURCHASED
			# notify to reflect changes
			lifecycleevent.modified(enrollment)
	else:
		send_event = False

	if send_event:
		# notify store based enrollment
		request = request or get_current_request()
		notify(StoreEnrollmentEvent(enrollment, purchasable, request))
	return send_event

def _unenroll(course, user, purchasable=None):
	enrollments = ICourseEnrollments(course)
	enrollment = enrollments.get_enrollment_for_principal(user)
	if enrollment is not None:
		enrollment_manager = ICourseEnrollmentManager(course)
		enrollment_manager.drop(user)
		return True
	return False

def _get_courses_from_purchasables(purchasables=()):
	catalog = component.getUtility(ICourseCatalog)
	for item in purchasables or ():
		purchasable = get_purchasable(item)
		if not IPurchasableCourse.providedBy(purchasable):
			continue
		for name in purchasable.Items:
			try:
				entry = catalog.getCatalogEntry(name)
				course = ICourseInstance(entry)
				yield course, purchasable
			except KeyError:
				logger.error("Could not find course entry %s", name)

def _to_sequence(items=(), unique=True):
	result = items.split() if isinstance(items, six.string_types) else items
	return set(result or ()) if unique else result

def _process_successful_purchase(purchasables, user=None, request=None, check=False):
	result = False
	user = get_user(user)
	if user is not None:
		purchasables = _to_sequence(purchasables)
		for course, purchasable in _get_courses_from_purchasables(purchasables):
			_enroll(course, user, purchasable, request=request, check_enrollment=check)
			result = True
	return result

@component.adapter(IPurchaseAttempt, IPurchaseAttemptSuccessful)
def _purchase_attempt_successful(purchase, event):
	# CS: use Items property of the purchase object in case it has been proxied
	if 	not IGiftPurchaseAttempt.providedBy(purchase) and \
		_process_successful_purchase(purchase.Items,
									 user=purchase.creator,
									 request=event.request):
		logger.info("Course purchase %s was successful", purchase.id)

@component.adapter(IInvitationAcceptedEvent)
def _purchase_invitation_accepted(event):
	invitation = event.object
	if 	IStorePurchaseInvitation.providedBy(invitation) and \
		IInvitationPurchaseAttempt.providedBy(invitation.purchase):
		original = invitation.purchase
		# CS: use Items property of the purchase object in case it has been proxied
		_process_successful_purchase(original.Items, user=event.user)
		logger.info("Course invitation %s was accepted", invitation.code)

def _process_refunded_purchase(purchase, user=None):
	result = False
	user = get_user(user if user is not None else purchase.creator)
	if user is not None:
		for course, purchasable in _get_courses_from_purchasables(purchase.Items):
			_unenroll(course, user, purchasable)
			result = True
	return result

@component.adapter(IPurchaseAttempt, IPurchaseAttemptRefunded)
def _purchase_attempt_refunded(purchase, event):
	if	not IGiftPurchaseAttempt.providedBy(purchase) and \
		_process_refunded_purchase(purchase):
		logger.info("Course purchase %s was refunded", purchase.id)

@component.adapter(IRedeemedPurchaseAttempt, IPurchaseAttemptRefunded)
def _redeemed_purchase_attempt_refunded(purchase, event):
	_process_refunded_purchase(purchase)

@component.adapter(IGiftPurchaseAttempt, IGiftPurchaseAttemptRedeemed)
def _gift_purchase_attempt_redeemed(purchase, event):
	user = event.user
	request = event.request
	# CS: use Items property of the purchase object  in case it has been proxied
	if _process_successful_purchase(purchase.Items, user, request=request, check=True):
		code = event.code or get_gift_code(purchase)
		logger.info("Course gift %s has been redeemed", code)

@component.adapter(ICourseInstanceEnrollmentRecord, IIntIdRemovedEvent)
def _enrollment_record_dropped(record, event):
	if record.Scope == ES_PURCHASED and queryInteraction() is not None:
		raise hexc.HTTPForbidden('Cannot drop a purchased course.')

# course subscribers

@component.adapter(ICourseVendorInfoSynchronized)
def on_course_vendor_info_synced(event):
	if component.getSiteManager() != component.getGlobalSiteManager():
		sync_purchasable_course(event.object)

@component.adapter(ICourseCatalogDidSyncEvent)
def on_course_catalog_did_sync(event):
	if component.getSiteManager() != component.getGlobalSiteManager():
		sync_purchasable_course_choice_bundles()

@component.adapter(ICourseInstance, IObjectRemovedEvent)
def on_course_instance_removed(course, event):
	if component.getSiteManager() != component.getGlobalSiteManager():
		purchasable = IPurchasableCourse(course, None)
		if purchasable is not None:
			purchasable.Public = False
			lifecycleevent.modified(purchasable)

def _build_base_args(event, user, profile):
	policy = component.getUtility(ISitePolicyUserEventListener)

	if IUser.providedBy(user):
		user_ext = to_external_object(user)
		informal_username = user_ext.get('NonI18NFirstName', profile.realname) or user.username
	else:
		informal_username = profile.realname or str(user)

	for_credit_url = getattr(policy, 'FOR_CREDIT_URL', '')
	site_alias = getattr(policy, 'COM_ALIAS', '')

	args = {'profile': profile,
			'context': event,
			'user': user,
			'for_credit_url': for_credit_url,
			'site_alias': site_alias,
			'support_email': policy.SUPPORT_EMAIL,
			'brand': policy.BRAND,
			'informal_username': informal_username,
			'today': isodate.date_isoformat(datetime.now()) }
	return args

def _queue_email(request, username, profile, args, template, subject, package, text_template_extension='.txt'):
	try:
		mailer = component.getUtility(ITemplatedMailer)
		mailer.queue_simple_html_text_email(
							template,
							subject=subject,
							recipients=[profile],
							template_args=args,
							request=request,
							package=package,
							text_template_extension=text_template_extension)
		return True
	except Exception:
		logger.exception('Error while sending store enrollment email to %s', username)
		return False

def _send_email(event, user, profile, email, args, template, subject, package):

	request = getattr(event, 'request', get_current_request())
	if not request or not email:
		logger.warn("Not sending an enrollment email because of no email or request "
					"(user=%s) (email=%s) (request=%s)", user, email, request is None)
		return

	username = user.username
	assert getattr(IPrincipal(profile, None), 'id', None) == username
	assert getattr(IEmailAddressable(profile, None), 'email', None) == email

	_queue_email(request=request,
				 username=username,
				 profile=profile,
				 args=args,
				 template=template,
				 subject=subject,
				 package=package,
				 text_template_extension='.mak')

def _get_start_date(catalog_entry, request):
	course_start_date = ''
	if catalog_entry.StartDate:
		locale = IBrowserRequest(request).locale
		dates = locale.dates
		formatter = dates.getFormatter('date', length='long')
		course_start_date = formatter.format(catalog_entry.StartDate)

	return course_start_date

def _get_course_start_date(course_ntiid, request):
	catalog = component.getUtility(ICourseCatalog)
	catalog_entry = catalog.getCatalogEntry(course_ntiid)

	return _get_start_date(catalog_entry, request)

def _get_purchase_args(attempt, purchasable, request):
	"Add gift specific args for purchase email."
	purchase_item_suffix = ''
	redeem_by_clauses = {}

	if IGiftPurchaseAttempt.providedBy(attempt):
		purchase_item_suffix = _(' - Gift')

		for entry in purchasable.Items:
			redeem_by = _get_course_start_date(entry, request)
			# Not sure if this correct, implies one course per purchasable.
			redeem_by_clauses[purchasable.NTIID] = _("Must redeem by ${redeem_by}",
													mapping={'redeem_by' : redeem_by })

	args = {'purchase_item_suffix' : purchase_item_suffix,
			'redeem_by_clauses' : redeem_by_clauses }

	return args

@component.adapter(IPurchaseAttempt, IPurchaseAttemptSuccessful)
def _purchase_attempt_email_notification(purchase, event):
	items = purchase.Items
	purchasable = get_purchasable(items[0]) if items else None
	if purchasable is None or not IPurchasableCourse.providedBy(purchasable):
		return

	request = getattr(event, 'request', get_current_request())
	if request is None:
		return

	user = purchase.creator
	profile = purchase.Profile
	add_args = _build_base_args(event, user, profile)

	purchase_args = _get_purchase_args(purchase, purchasable, request)
	add_args.update(purchase_args)

	store_purchase_attempt_successful(event, add_args=add_args)

	# Send to additional addresses
	settings = component.queryUtility(IApplicationSettings) or {}
	email_line = settings.get('purchase_additional_confirmation_addresses', '')
	for email in email_line.split():
		safe_send_purchase_confirmation(event, email, add_args=add_args)

def _web_root():
	settings = component.getUtility(IApplicationSettings)
	web_root = settings.get('web_app_root', '/NextThoughtWebApp/')
	return web_root

def _get_redeem_link(request, catalog_entry, redemption_code):
	ntiid = getattr(catalog_entry, 'ntiid', None)

	# The webapp does this dance to get to the course library page
	ntiid = '!@%s' % ntiid
	encoded = urlsafe_b64encode(ntiid)
	encoded_ntiid = encoded.replace('=', '')
	url = '#!library/availablecourses/%s/redeem/%s' % (encoded_ntiid, redemption_code)

	app_url = request.application_url
	redemption_link = urljoin(app_url, _web_root())
	redemption_link = urljoin(redemption_link, url)
	return redemption_link

def _get_session_length_args(catalog_entry):
	"""
	For a catalog entry, return a tuple of formatted strings displaying
	the length of the course.
	"""
	course_session_length = ''
	course_session_date = ''

	duration = catalog_entry.Duration
	if duration.days:
		duration_days = duration.days // 7
		course_session_length = '%s WEEK SESSION' % duration_days

	if catalog_entry.StartDate and catalog_entry.EndDate:
		# Localize times to UTC to match catalog, then
		# view as local timezone. Currently hard-coded to Central
		# time. May want to consider adding a default timezone to
		# policies if we make this more general at some point.
		localTimeZone = timezone('US/Central')
		utc_start_date = pytz.utc.localize(catalog_entry.StartDate)
		utc_end_date = pytz.utc.localize(catalog_entry.EndDate)
		local_start_date = utc_start_date.astimezone(localTimeZone)
		local_end_date = utc_end_date.astimezone(localTimeZone)

		start_format = local_start_date.strftime("%B %d")
		end_format = local_end_date.strftime("%B %d, %Y")
		course_session_date = '%s-%s' % (start_format, end_format)

	return course_session_length, course_session_date

def _get_gift_args(entry_ntiid, redemption_code, event, request):
	try:
		catalog = component.getUtility(ICourseCatalog)
		catalog_entry = catalog.getCatalogEntry(entry_ntiid)
	except KeyError:
		logger.error("Could not find catalog entry %s", entry_ntiid)
		return

	course_args = _build_course_args(event, catalog_entry)
	redemption_link = _get_redeem_link(request, catalog_entry, redemption_code)
	course_session_length, course_session_date = _get_session_length_args(catalog_entry)
	course_args.update({'redemption_link' : redemption_link,
						'catalog_entry' : catalog_entry,
						'course_session_length' : course_session_length,
						'course_session_date' : course_session_date })
	result = catalog_entry, course_args
	return result

def _send_entry_gift_email(purchase, purchase_ntiids, event, request):
	redemption_code = get_gift_code(purchase)
	# Get all of the purchase options for our courses
	purchase_options = [_get_gift_args(x, redemption_code, event, request)
						for x in purchase_ntiids]

	creator_email = purchase.Creator
	receiver_email = purchase.Receiver

	base_template = 'gift_certificate_email'
	first_catalog_entry = purchase_options[0][0]
	# FIXME: default gift email
	template, package = get_template(first_catalog_entry, base_template)

	if len(purchase_options) > 1:
		gift_subject = translate(_("Janux Gift Certificate"))
	else:
		gift_subject = translate(_("Janux Gift Certificate: ${course_title}",
									mapping={ 'course_title' : first_catalog_entry.title }))

	gift_subject_copy = translate(_("${gift_subject} (copy)",
									mapping={ 'gift_subject' : gift_subject }))

	outbound_params = []
	# Find out which emails to send
	if receiver_email and creator_email != receiver_email:
		# Two different email addresses; two different emails.
		outbound_params.append((receiver_email, gift_subject, None))
		header_msg = _("Below is a copy of the gift certificate that was sent to ${rec_email}.",
						mapping={ 'rec_email' : receiver_email })

		outbound_params.append((creator_email, gift_subject_copy, header_msg))
	else:
		# We do not have a receiver or the two emails are the same; just send to buyer.
		header_msg = _("""Please forward this gift certificate to the email address of your
						intended recipient.  You can also print this certificate out
						and pass it to a person of your choosing.""")
		outbound_params.append((creator_email, gift_subject, header_msg))

	policy = component.getUtility(ISitePolicyUserEventListener)
	for_credit_url = getattr(policy, 'FOR_CREDIT_URL', '')
	site_alias = getattr(policy, 'COM_ALIAS', '')

	# Sort by course start date; grab our final cutoff date for the gift.
	gift_options = sorted(purchase_options, key=lambda x: x[0].StartDate)
	gift_options = [x[1] for x in gift_options]
	final_course_start_date = gift_options[-1].get('course_start_date')

	args = {
		'sender_name' : purchase.SenderName,
		'receiver_name' : purchase.ReceiverName,
		'gift_message' : purchase.Message,
		'for_credit_url': for_credit_url,
		'site_alias': site_alias,
		'final_course_start_date' : final_course_start_date,
		'redemption_code' : redemption_code,
		'support_email' : policy.SUPPORT_EMAIL,
		'gift_options' : gift_options
	}

	# Now start sending emails
	for _email, _subject, _header in outbound_params:
		args.update({ 'header' : _header })
		_queue_email(request=request,
				 	username=_email,
				 	profile=_email,
				 	args=args,
				 	template=template,
				 	subject=_subject,
				 	package=package,
				 	text_template_extension='.mak')

@component.adapter(IGiftPurchaseAttempt, IPurchaseAttemptSuccessful)
def _gift_purchase_attempt_email_notification(purchase, event):
	items = purchase.Items
	purchasable = get_purchasable(items[0]) if items else None
	if purchasable is None or not IPurchasableCourse.providedBy(purchasable):
		return

	request = getattr(event, 'request', get_current_request())
	if request is None:
		return

	_send_entry_gift_email(purchase, purchasable.Items, event, request)

def _build_course_args(event, catalog_entry):
	request = getattr(event, 'request', get_current_request())
	course_start_date = _get_start_date(catalog_entry, request)
	course_end_date = catalog_entry.EndDate
	course_archived = course_end_date and course_end_date < datetime.utcnow()
	course_preview = catalog_entry.Preview

	html_sig = catalog_entry.InstructorsSignature.replace('\n', "<br />")

	course_args = {	'course': catalog_entry,
					'instructors_html_signature': html_sig,
					'course_preview': course_preview,
					'course_archived': course_archived,
					'course_start_date': course_start_date }
	return course_args

def _build_enrollment_args(event, user, profile, catalog_entry):
	args = _build_base_args(event, user, profile)
	course_args = _build_course_args(event, catalog_entry)
	args.update(course_args)

	subject = translate(_("Welcome to ${title}",
						mapping={'title': catalog_entry.Title}))

	course_args = {	'subject': subject }
	args.update(course_args)
	return args

@component.adapter(IStoreEnrollmentEvent)
def _user_enrolled(event):
	record = event.record
	if record is not None and record.Scope == ES_PURCHASED:
		creator = record.Principal
		creator = get_user(creator)
		profile = IUserProfile(creator)
		email = getattr(profile, 'email', None)

		course = record.CourseInstance
		catalog_entry = ICourseCatalogEntry(course)

		base_template = 'enrollment_confirmation_email'
		template, package = get_template(catalog_entry, base_template, DEFAULT_ENROLL_PACKAGE)

		args = _build_enrollment_args(event, creator, profile, catalog_entry)
		subject = args.pop('subject')

		_send_email(event, creator, profile, email, args, template, subject, package)

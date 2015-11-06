#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import six

from zope import component
from zope import lifecycleevent

from zope.event import notify

from zope.security.management import queryInteraction

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.app.products.courseware.interfaces import ICoursesWorkspace
from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.appserver.workspaces.interfaces import IUserService

from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import AlreadyEnrolledException
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.contenttypes.courses.utils import get_enrollment_record
from nti.contenttypes.courses.utils import drop_any_other_enrollments

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser

from nti.intid.interfaces import IIntIdRemovedEvent

from nti.invitations.interfaces import IInvitationAcceptedEvent

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

from .interfaces import StoreEnrollmentEvent

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

from zope.component.hooks import site as current_site

from nti.processlifetime import IApplicationTransactionOpenedEvent

from nti.site.hostpolicy import get_all_host_sites

from .register import register_purchasables

@component.adapter(IApplicationTransactionOpenedEvent)
def register_course_purchasables(*args, **kwargs):
	result = []
	for site in get_all_host_sites():
		with current_site(site):
			registered = register_purchasables()
			result.extend(registered)
	return result

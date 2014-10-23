#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.event import notify
from zope import lifecycleevent

from zope.security.management import queryInteraction

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.app.products.courseware.utils import drop_any_other_enrollments

from nti.appserver.invitations.interfaces import IInvitationAcceptedEvent

from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.intid.interfaces import IIntIdRemovedEvent

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

def _enroll(course, user, purchasable=None, request=None):
	drop_any_other_enrollments(course, user)
	enrollments = ICourseEnrollments(course)
	enrollment_manager = ICourseEnrollmentManager(course)
	enrollment = enrollments.get_enrollment_for_principal(user)
	if enrollment is None: 	# Never before been enrolled
		enrollment = enrollment_manager.enroll(user, scope=ES_PURCHASED,
											   context=purchasable)
	else:
		logger.info("User %s now paying for course (old_scope %s)",
					user, enrollment.Scope)
		## change scope and mark record
		enrollment.Scope = ES_PURCHASED
		## notify to reflect changes
		lifecycleevent.modified(enrollment)
		
	# notify store based enrollment
	request = request or get_current_request()
	notify(StoreEnrollmentEvent(enrollment, purchasable, request))
	return True

def _unenroll(course, user, purchasable=None):
	enrollments = ICourseEnrollments(course)
	enrollment = enrollments.get_enrollment_for_principal(user)
	if enrollment is not None:
		enrollment_manager = ICourseEnrollmentManager(course)
		enrollment_manager.drop(user)
		return True
	return False

def _get_courses_from_purchase(purchase):
	catalog = component.getUtility(ICourseCatalog)
	for item in purchase.Items:
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

def _process_successful_purchase(purchase, user=None, request=None):
	user = user or purchase.creator
	for course, purchasable in _get_courses_from_purchase(purchase):
		_enroll(course, user, purchasable, request=request)
		
@component.adapter(IPurchaseAttempt, IPurchaseAttemptSuccessful)
def _purchase_attempt_successful(purchase, event):
	_process_successful_purchase(purchase, request=event.request)

@component.adapter(IStorePurchaseInvitation, IInvitationAcceptedEvent)
def _purchase_invitation_accepted(invitation, event):
	if 	IStorePurchaseInvitation.providedBy(invitation) and \
		IInvitationPurchaseAttempt.providedBy(invitation.purchase):
		original = invitation.purchase
		_process_successful_purchase(original)

def _process_refunded_purchase(purchase, user=None):
	user = user or purchase.creator
	for course, purchasable in _get_courses_from_purchase(purchase):
		_unenroll(course, user, purchasable)
		
@component.adapter(IPurchaseAttempt, IPurchaseAttemptRefunded)
def _purchase_attempt_refunded(purchase, event):
	_process_refunded_purchase(purchase)

@component.adapter(IGiftPurchaseAttempt, IGiftPurchaseAttemptRedeemed)
def _gift_purchase_attempt_redeemed(purchase, event):
	_process_successful_purchase(purchase, event.user, event.request)

@component.adapter(IRedeemedPurchaseAttempt, IPurchaseAttemptRefunded)
def _redeemed_purchase_attempt_refunded(purchase, event):
	_process_refunded_purchase(purchase)

@component.adapter(ICourseInstanceEnrollmentRecord, IIntIdRemovedEvent)
def _enrollment_record_dropped(record, event):
	if record.Scope == ES_PURCHASED and queryInteraction() is not None:
		raise hexc.HTTPForbidden('Cannot drop a purchased course')

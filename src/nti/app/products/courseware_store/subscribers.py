#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope import lifecycleevent

from nti.app.products.courseware.utils import drop_any_other_enrollments

from nti.appserver.invitations.interfaces import IInvitationAcceptedEvent

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ES_CREDIT_NONDEGREE
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecordCreatedEvent

from nti.store.purchasable import get_purchasable

from nti.store.interfaces import IPurchaseAttempt
from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IPurchaseAttemptRefunded
from nti.store.interfaces import IStorePurchaseInvitation
from nti.store.interfaces import IInvitationPurchaseAttempt
from nti.store.interfaces import IPurchaseAttemptSuccessful

from .interfaces import IPurchasableCourseEnrollmentRecord

def _enroll(course, user, purchasable=None):
	drop_any_other_enrollments(course, user)
	enrollments = ICourseEnrollments(course)
	enrollment_manager = ICourseEnrollmentManager(course)
	enrollment = enrollments.get_enrollment_for_principal(user)
	if enrollment is None: 	# Never before been enrolled
		enrollment_manager.enroll(user, scope=ES_CREDIT_NONDEGREE, context=purchasable)
	else:
		logger.info("User %s now paying for course (old_scope %s)",
					user, enrollment.Scope)
		## change scope and mark record
		enrollment.Scope = ES_CREDIT_NONDEGREE
		interface.alsoProvides(enrollment, IPurchasableCourseEnrollmentRecord)
		## notify to reflect changes
		lifecycleevent.modified(enrollment)
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

def _process_successful_purchase(purchase):
	user = purchase.creator
	for course, purchasable in _get_courses_from_purchase(purchase):
		_enroll(course, user, purchasable)

@component.adapter(ICourseInstanceEnrollmentRecord, ICourseInstanceEnrollmentRecordCreatedEvent)
def _on_course_enrollment_record_created(record, event):
	if IPurchasableCourse.providedBy(event.context):
		interface.alsoProvides(record, IPurchasableCourseEnrollmentRecord)
		
@component.adapter(IPurchaseAttempt, IPurchaseAttemptSuccessful)
def _purchase_attempt_successful(purchase, event):
	_process_successful_purchase(purchase)

@component.adapter(IStorePurchaseInvitation, IInvitationAcceptedEvent)
def _purchase_invitation_accepted(invitation, event):
	if 	IStorePurchaseInvitation.providedBy(invitation) and \
		IInvitationPurchaseAttempt.providedBy(invitation.purchase):
		original = invitation.purchase
		_process_successful_purchase(original)

def _process_refunded_purchase(purchase):
	user = purchase.creator
	for course, purchasable in _get_courses_from_purchase(purchase):
		_unenroll(course, user, purchasable)
		
@component.adapter(IPurchaseAttempt, IPurchaseAttemptRefunded)
def _purchase_attempt_refunded(purchase, event):
	_process_refunded_purchase(purchase)

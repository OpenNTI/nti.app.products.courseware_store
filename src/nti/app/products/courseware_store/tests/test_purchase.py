#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property 

from zope import component

from zope.event import notify

from nti.appserver.interfaces import IApplicationSettings

from nti.app.products.courseware_store.utils import find_allow_vendor_updates_users

from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import AlreadyEnrolledException

from nti.dataserver.users import User

from nti.store.interfaces import PA_STATE_STARTED
from nti.store.interfaces import PA_STATE_SUCCESS
from nti.store.interfaces import PA_STATE_REFUNDED
from nti.store.interfaces import PA_STATE_REDEEMED
from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import PurchaseAttemptRefunded
from nti.store.interfaces import PurchaseAttemptSuccessful
from nti.store.interfaces import GiftPurchaseAttemptRedeemed

from nti.store.purchasable import get_purchasable
from nti.store.pricing import create_pricing_results
from nti.store.purchase_order import create_purchase_item
from nti.store.purchase_order import create_purchase_order
from nti.store.purchase_attempt import create_purchase_attempt
from nti.store.purchase_history import register_purchase_attempt
from nti.store.gift_registry import register_gift_purchase_attempt
from nti.store.purchase_attempt import create_gift_purchase_attempt

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

class TestPurchase(ApplicationLayerTest):
	
	layer = InstructedCourseApplicationTestLayer

	processor = 'stripe'
	default_username = 'ichigo'
	
	default_origin = str('http://janux.ou.edu')
	purchasable_id = 'tag:nextthought.com,2011-10:NTI-purchasable_course-Fall2013_CLC3403_LawAndJustice'
	course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'
	
	def catalog_entry(self):
		catalog = component.getUtility(ICourseCatalog)
		for entry in catalog.iterCatalogEntries():
			if entry.ntiid == self.course_ntiid:
				return entry

	def create_purchase_attempt(self, item, quantity=None, state=None):
		state = state or PA_STATE_STARTED
		item = create_purchase_item(item, 1)
		order = create_purchase_order(item, quantity=quantity)
		pricing = create_pricing_results(purchase_price=999.99, non_discounted_price=0.0)
		result = create_purchase_attempt(order, processor=self.processor, state=state,
										 context={"AllowVendorUpdates":True})
		result.Pricing = pricing
		return result

	def create_gift_attempt(self, creator, item, state=None):
		state = state or PA_STATE_STARTED
		item = create_purchase_item(item, 1)
		order = create_purchase_order(item, quantity=None)
		pricing = create_pricing_results(purchase_price=999.99, non_discounted_price=0.0)
		result = create_gift_purchase_attempt(order=order, processor=self.processor, 
										  	  state=state, creator=creator,
										  	  context={"AllowVendorUpdates":True})
		result.Pricing = pricing
		return result
	
	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_enrollment(self):	
		settings = component.getUtility(IApplicationSettings)
		settings['purchase_additional_confirmation_addresses'] = 'foo@bar.com\nbiz@baz.com'
		
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			p = get_purchasable(self.purchasable_id)
			assert_that(p, is_not(none()))
			assert_that(IPurchasableCourse.providedBy(p), is_(True))

			purchase = self.create_purchase_attempt(self.purchasable_id)
			user = User.get_user(self.default_username)
			register_purchase_attempt(purchase, user)
			
			notify(PurchaseAttemptSuccessful(purchase))
			assert_that(purchase.State, is_(PA_STATE_SUCCESS))
			
			entry = self.catalog_entry()
			course = ICourseInstance(entry)
			enrollments = ICourseEnrollments(course)
			enrollment = enrollments.get_enrollment_for_principal(user)
			assert_that(enrollment, is_not(none()))
			assert_that(enrollment, has_property('Scope', ES_PURCHASED))
			
			# test report
			usernames = find_allow_vendor_updates_users(entry)
			assert_that(usernames, has_length(1))
			assert_that(self.default_username, is_in(usernames))
			
			# test refund
			notify(PurchaseAttemptRefunded(purchase))
			assert_that(purchase.State, is_(PA_STATE_REFUNDED))

			enrollments = ICourseEnrollments(course)
			enrollment = enrollments.get_enrollment_for_principal(user)
			assert_that(enrollment, is_(none()))
			
	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_gift_redeemed(self):	
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			ichigo = 'ichigo@bleach.org'
			gift = self.create_gift_attempt(ichigo, self.purchasable_id,
											state=PA_STATE_SUCCESS)
			gid = register_gift_purchase_attempt(ichigo, gift)
			assert_that(gid, is_not(none()))
		
			user = User.get_user(self.default_username)
			notify(GiftPurchaseAttemptRedeemed(gift, user))
			assert_that(gift.State, is_(PA_STATE_REDEEMED))
			
			entry = self.catalog_entry()
			course = ICourseInstance(entry)
			enrollments = ICourseEnrollments(course)
			enrollment = enrollments.get_enrollment_for_principal(user)
			assert_that(enrollment, is_not(none()))
			assert_that(enrollment, has_property('Scope', ES_PURCHASED))

			with self.assertRaises(AlreadyEnrolledException):
				gift.State = PA_STATE_SUCCESS
				notify(GiftPurchaseAttemptRedeemed(gift, user))
		
			usernames = find_allow_vendor_updates_users(entry)
			assert_that(usernames, has_length(1))
			assert_that(self.default_username, is_in(usernames))
		
			# restore
			gift.State = PA_STATE_REDEEMED				
			notify(PurchaseAttemptRefunded(gift))
			assert_that(gift.State, is_(PA_STATE_REFUNDED))

			enrollments = ICourseEnrollments(course)
			enrollment = enrollments.get_enrollment_for_principal(user)
			assert_that(enrollment, is_(none()))

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string
does_not = is_not

import time
import transaction
from quopri import decodestring

from zope import component
from zope.event import notify
from zope.component import eventtesting

from pyramid.testing import DummyRequest

from nti.app.products.ou.store.utils import register_purchasables

from nti.appserver.interfaces import IApplicationSettings

from nti.dataserver.users import User

from nti.store.interfaces import PA_STATE_STARTED
from nti.store.interfaces import PA_STATE_SUCCESS
from nti.store.interfaces import PurchaseAttemptSuccessful
from nti.store.interfaces import IPurchaseAttemptSuccessful

from nti.store.payment_charge import UserAddress
from nti.store.payment_charge import PaymentCharge
from nti.store.pricing import create_pricing_results
from nti.store.purchase_order import create_purchase_item
from nti.store.purchase_order import create_purchase_order
from nti.store.purchase_attempt import create_purchase_attempt
from nti.store.purchase_history import register_purchase_attempt

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.testing import ITestMailDelivery
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

class TestPurchaseEmail(ApplicationLayerTest):
	
	layer = InstructedCourseApplicationTestLayer

	processor = 'stripe'
	
	default_origin = str('http://janux.ou.edu')
	item = purchasable_id = 'tag:nextthought.com,2011-10:NTI-purchasable_course-CLC_3403'
	course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'

	default_username = 'jason.madden@nextthought.com'
		
	def create_payment_charge(self, amount, currency='USD'):
		address = UserAddress.create("1 Infinite Loop", None, "Cupertino", "CA", 
									 "95014", "USA")
		charge = PaymentCharge(Amount=amount, Currency=currency,
							   Created=time.time(), CardLast4=4242,
							   Address=address, Name="Jason")
		return charge
	
	def create_purchase_attempt(self, item, amount, quantity=None, currency='USD'):
		state = PA_STATE_STARTED
		p_item = create_purchase_item(item, 1)
		p_order = create_purchase_order(p_item, quantity=quantity)
		p_pricing = create_pricing_results(purchase_price=amount, 
										   non_discounted_price=0.0,
										   currency=currency)
		result = create_purchase_attempt(p_order, processor=self.processor, state=state)
		result.Pricing = p_pricing
		return result

	def _save_message(self, msg):
		import codecs
		with codecs.open('/tmp/file.html', 'w', encoding='utf-8') as f:
			f.write( msg.html )
			print(msg.body)
			print(msg.html)

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_purchase_email(self):
		settings = component.getUtility(IApplicationSettings)
		settings['purchase_additional_confirmation_addresses'] = 'foo@bar.com\nbiz@baz.com'
		
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			register_purchasables()
			
			amount = 599.99
			username = self.default_username
			purchase = self.create_purchase_attempt(self.item, amount, 1)
			user = User.get_user(self.default_username)
			register_purchase_attempt(purchase, user)
			charge = self.create_payment_charge(amount)
			
			notify(PurchaseAttemptSuccessful(purchase, charge, request=DummyRequest()))
			assert_that(purchase.State, is_(PA_STATE_SUCCESS))
			
			assert_that(eventtesting.getEvents(IPurchaseAttemptSuccessful),
						has_length(1))
			event = eventtesting.getEvents(IPurchaseAttemptSuccessful)[0]
			purchase = event.object

			mailer = component.getUtility(ITestMailDelivery)
			assert_that( mailer.queue, has_length(2))
			msg = mailer.queue[0]

			assert_that( msg, has_property( 'body'))
			body = decodestring(msg.body)
			assert_that( body, contains_string(username ) )
			assert_that( body, contains_string('Infinite Loop' ) )
			assert_that( body, contains_string('Law and Justice' ) )
			assert_that( body, does_not( contains_string('\xa599.00') ) )
			
			# self._save_message(msg)
			
			assert_that( msg, has_property('html'))
			html = decodestring(msg.html)
			assert_that( html, contains_string(username) )
			assert_that( html, contains_string('Infinite Loop' ) )
			assert_that( html, contains_string('Law and Justice' ) )
			assert_that( html, contains_string('US$599.00' ) )

			# Send the event again, this time with a discount
			del mailer.queue[:]

			purchase.Order.Coupon = '1$ off'
			purchase.Pricing.TotalNonDiscountedPrice = 800.0
			notify(PurchaseAttemptSuccessful(purchase, charge, request=DummyRequest()))

			assert_that( mailer.queue, has_length(2) )
			msg = mailer.queue[0]
			assert_that( msg, has_property( 'body'))
			body = decodestring(msg.body)
			assert_that( body, contains_string( 'Discount' ) )

			assert_that( msg, has_property( 'html'))
			html = decodestring(msg.html)
			assert_that( html, contains_string( 'DISCOUNTS' ) )

			transaction.abort()

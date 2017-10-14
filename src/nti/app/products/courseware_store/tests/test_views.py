#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from zope.event import notify

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.users.users import User

from nti.dataserver.tests import mock_dataserver

from nti.store.interfaces import PA_STATE_STARTED
from nti.store.interfaces import PA_STATE_SUCCESS
from nti.store.interfaces import PurchaseAttemptSuccessful

from nti.store.pricing import create_pricing_results

from nti.store.purchase_attempt import create_purchase_attempt

from nti.store.purchase_history import register_purchase_attempt

from nti.store.purchase_order import create_purchase_item
from nti.store.purchase_order import create_purchase_order


class TestViews(ApplicationLayerTest):

    layer = InstructedCourseApplicationTestLayer

    processor = u'stripe'

    default_origin = 'http://janux.ou.edu'

    course_ntiid = u'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'
    purchasable_id = u'tag:nextthought.com,2011-10:NTI-purchasable_course-Fall2013_CLC3403_LawAndJustice'

    def create_purchase_attempt(self, item, quantity=None, state=None):
        state = state or PA_STATE_STARTED
        item = create_purchase_item(item, 1)
        order = create_purchase_order(item, quantity=quantity)
        pricing = create_pricing_results(purchase_price=999.99,
                                         non_discounted_price=0.0)
        result = create_purchase_attempt(order, processor=self.processor, state=state,
                                         context={u"AllowVendorUpdates": True})
        result.Pricing = pricing
        return result

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_course_allow_vendor_updates(self):

        with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
            purchase = self.create_purchase_attempt(self.purchasable_id)
            user = User.get_user(self.default_username)
            register_purchase_attempt(purchase, user)
            notify(PurchaseAttemptSuccessful(purchase))
            assert_that(purchase.State, is_(PA_STATE_SUCCESS))

        res = self.testapp.get('/dataserver2/CourseAdmin/@@VendorUpdatesPurchasedCourse',
                               params={'ntiid': self.course_ntiid})
        assert_that(res.body,
                    is_('username,name,email\r\n'
                        'sjohnson@nextthought.com,sjohnson@nextthought.com,\r\n'))

        assert_that(res.content_disposition,
                    is_('attachment; filename="updates.csv"'))

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import greater_than_or_equal_to
does_not = is_not

from nti.app.products.courseware_store.model import create_course

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.externalization.externalization import to_external_object


class TestPurchasableCourse(ApplicationLayerTest):

    processor = 'stripe'

    def test_create_course(self):
        default_date_str = u"2015-06-13T04:59:00+00:00"

        course = create_course(
            ntiid=u'tag:nextthought.com,2011-10:NTI-purchasable_course-LSTD_1153',
            name=u"A History of the United States",
            provider=u"Janux",
            amount=500,
            items=(u"tag:nextthought.com,2011-10:NTI-CourseInfo-Spring2015_LSTD_1153",),
            title=u"A History of the United States",
            author=u"Janux",
            giftable=True,
            description=u"History is about more than the people",
            vendor_info={u"CRN": 34846, u"Term": 201410},
            purchase_cutoff_date=default_date_str,
            redeem_cutoff_date=default_date_str
        )
        ext = to_external_object(course)
        assert_that(ext,
                    has_entries('Amount', 500.0,
                                'Class', 'PurchasableCourse',
                                'Currency', u'USD',
                                'Description', u'History is about more than the people',
                                'Giftable', True,
                                'NTIID', u'tag:nextthought.com,2011-10:NTI-purchasable_course-LSTD_1153',
                                'MimeType', 'application/vnd.nextthought.store.purchasablecourse',
                                'Public', True,
                                'Redeemable', False,
                                'Title', u'A History of the United States',
                                'PurchaseCutOffDate', default_date_str,
                                'RedeemCutOffDate', default_date_str,
                                'VendorInfo', has_entries('CRN', 34846, 
                                                          'Term', 201410)))

        ext = to_external_object(course, name="summary")
        assert_that(ext, does_not(has_key('Icon')))
        assert_that(ext, does_not(has_key('Public')))
        assert_that(ext, does_not(has_key('License')))
        assert_that(ext, does_not(has_key('Thumbnail')))
        assert_that(ext, does_not(has_key('Description')))
        assert_that(ext, does_not(has_key('EndDate')))
        assert_that(ext, does_not(has_key('Preview')))
        assert_that(ext, does_not(has_key('Featured')))
        assert_that(ext, does_not(has_key('Duration')))
        assert_that(ext, does_not(has_key('StartDate')))
        assert_that(ext, does_not(has_key('Signature')))
        assert_that(ext, does_not(has_key('Department')))
        assert_that(ext, does_not(has_key('Communities')))
        assert_that(ext, 
                    has_entry('VendorInfo', has_length(greater_than_or_equal_to(2))))

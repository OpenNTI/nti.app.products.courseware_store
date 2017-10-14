#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import contains
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.products.courseware_store.interfaces import IPurchasableCourseChoiceBundle

from nti.app.products.courseware_store.purchasable import create_course_choice_bundle

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.externalization.tests import externalizes

from nti.store.purchasable import get_purchasable


class TestPurchasable(ApplicationLayerTest):

    layer = InstructedCourseApplicationTestLayer

    purchasable_id = 'tag:nextthought.com,2011-10:NTI-purchasable_course-Fall2013_CLC3403_LawAndJustice'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_create_course_choice_bundle(self):

        with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
            purchasables = (get_purchasable(self.purchasable_id),)

            bundle = create_course_choice_bundle(u"LAW", purchasables)
            assert_that(bundle, is_not(none()))

            assert_that(bundle,
                        verifiably_provides(IPurchasableCourseChoiceBundle))
            assert_that(bundle,
                        has_property('NTIID',
                                     'tag:nextthought.com,2011-10:Janux-purchasable_course_choice_bundle-LAW'))

            assert_that(bundle, has_property('Giftable', is_(True)))
            assert_that(bundle, has_property('Provider', is_('Janux')))
            assert_that(bundle, has_property('Description', is_('LAW')))
            assert_that(bundle, has_property('Title', is_('LAW')))
            assert_that(bundle, has_property('Public', is_(True)))
            assert_that(bundle, has_property('Redeemable', is_(True)))
            assert_that(bundle, has_property('Amount', is_(599.0)))
            assert_that(bundle,
                        has_property('Items',
                                     contains('tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice')))
            assert_that(bundle,
                        has_property('Purchasables',
                                     contains('tag:nextthought.com,2011-10:NTI-purchasable_course-Fall2013_CLC3403_LawAndJustice')))

            assert_that(bundle,
                        externalizes(has_entries('Class', 'PurchasableCourseChoiceBundle',
                                                 'MimeType', 'application/vnd.nextthought.store.purchasablecoursechoicebundle')))

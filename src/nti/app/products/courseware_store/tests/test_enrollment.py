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
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
does_not = is_not

from zope import component

from nti.app.products.courseware.utils import get_enrollment_options

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.products.courseware_store.utils import get_purchasable_course_bundles

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.dataserver.tests import mock_dataserver

from nti.externalization.externalization import to_external_object


class TestEnrollmentOptions(ApplicationLayerTest):

    layer = InstructedCourseApplicationTestLayer

    course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'

    def catalog_entry(self):
        catalog = component.getUtility(ICourseCatalog)
        for entry in catalog.iterCatalogEntries():
            if entry.ntiid == self.course_ntiid:
                return entry

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_get_enrollment_options(self):
        with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
            entry = self.catalog_entry()
            bundles = get_purchasable_course_bundles(entry)
            assert_that(bundles, has_length(0))

            options = get_enrollment_options(entry)
            assert_that(options, is_not(none()))
            assert_that(options, has_entry('StoreEnrollment',
                                           has_property('Purchasables', is_not(none()))))

            ext_obj = to_external_object(options)
            assert_that(ext_obj,
                        has_entry('Items',
                                  has_entry('StoreEnrollment',
                                            has_entries('Enabled', is_(True),
                                                        'IsSeatAvailable', is_(True),
                                                        'RequiresAdmission', is_(False),
                                                        'AllowVendorUpdates', is_(True),
                                                        'MimeType', 'application/vnd.nextthought.courseware.storeenrollmentoption',
                                                        'Purchasables', has_entries('Items', has_length(1),
                                                                                    'DefaultGiftingNTIID', is_not(none()),
                                                                                    'DefaultPurchaseNTIID', is_not(none()))))))

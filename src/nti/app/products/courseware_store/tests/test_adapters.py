#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from zope import component
from zope import interface

from nti.app.products.courseware.interfaces import ICoursePublishableVendorInfo

from nti.app.products.courseware_store.interfaces import ICoursePrice
from nti.app.products.courseware_store.vendorinfo import _CourseCatalogPublishableVendorInfo

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import AlreadyEnrolledException

from nti.store.interfaces import IRedemptionError
from nti.store.interfaces import IPurchasableCourse

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

class TestAdapters(ApplicationLayerTest):

	layer = InstructedCourseApplicationTestLayer

	default_origin = str('http://janux.ou.edu')
	course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'

	@classmethod
	def catalog_entry(self):
		catalog = component.getUtility(ICourseCatalog)
		for entry in catalog.iterCatalogEntries():
			if entry.ntiid == self.course_ntiid:
				return entry

	@WithSharedApplicationMockDS(testapp=True,users=True)
	@fudge.patch('nti.app.products.courseware_store.adapters.is_course_enabled_for_purchase')
	def test_adapter(self, mock_isce):
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			# is enabled
			mock_isce.is_callable().with_args().returns(True)
			# test
			entry = self.catalog_entry()
			purchasable = IPurchasableCourse(entry, None)
			assert_that(purchasable, is_not(none()))
			assert_that(purchasable, has_property('NTIID', is_('tag:nextthought.com,2011-10:NTI-purchasable_course-Fall2013_CLC3403_LawAndJustice')))
			assert_that(purchasable, has_property('Items', has_length(1)))
			assert_that(purchasable, has_property('Amount', is_(599.0)))
			assert_that(purchasable, has_property('Currency', is_('USD')))
			assert_that(purchasable, has_property('Name', is_('Law and Justice')))
			assert_that(purchasable, has_property('Title', is_('Law and Justice')))
			assert_that(purchasable, has_property("PurchaseCutOffDate", is_("2024-08-29T05:00:00+00:00")))
			assert_that(purchasable, has_property("RedeemCutOffDate", is_("2024-08-23T04:59:00+00:00")))
			items = list(purchasable.Items)
			assert_that(items, is_(['tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice']))

	@fudge.patch('nti.app.products.courseware_store.utils.get_vendor_info')
	def test_nti_course_price_finder(self, mock_vi):
		fake_course = fudge.Fake()
		interface.alsoProvides(fake_course, ICourseInstance)

		mock_vi.is_callable().with_args().returns(
		{
			"NTI": {
				"Purchasable":{
					'Price':300,
					'Currency':'COP'
				}
			}
		})
		course_price = component.queryAdapter(fake_course, ICoursePrice, name="nti")
		assert_that(course_price, is_not(none()))
		assert_that(course_price, has_property(u'Amount', is_(300)))
		assert_that(course_price, has_property(u'Currency', is_('COP')))

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_course_catalog_vendor_info(self):

		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			catalog_entry = self.catalog_entry()
			course = ICourseInstance( catalog_entry )
			vendor_infos = component.subscribers((course,), ICoursePublishableVendorInfo)

			vendor_info = None

			for vi in vendor_infos:
				if isinstance( vi, _CourseCatalogPublishableVendorInfo ):
					vendor_info = vi.info()

			assert_that( vendor_info, not_none() )
			assert_that( vendor_info, has_key( 'StartDate' ))
			assert_that( vendor_info, has_key( 'EndDate' ))
			assert_that( vendor_info, has_key( 'Duration' ))
			assert_that( vendor_info, has_key( 'Title' ))
			
	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_already_enrolled_exception(self):
		e = AlreadyEnrolledException()
		error = IRedemptionError(e, None)
		assert_that(error, is_not(none()))

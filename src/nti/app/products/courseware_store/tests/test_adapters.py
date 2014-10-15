#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from zope import component

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.store.interfaces import IPurchasableCourse

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

class TestAdapters(ApplicationLayerTest):
	
	layer = InstructedCourseApplicationTestLayer

	default_origin = str('http://janux.ou.edu')
	course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'

	def _catalog_entry(self):
		catalog = component.getUtility(ICourseCatalog)
		for entry in catalog.iterCatalogEntries():
			if entry.ntiid == self.course_ntiid:
				return entry

	@WithSharedApplicationMockDS(testapp=True,users=True)
	@fudge.patch('nti.app.products.ou.store.adapters.get_course_price',
				 'nti.app.products.ou.store.adapters.is_course_enabled_for_purchase')
	def test_adapter(self, mock_gcp, mock_isce):
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			# fake price
			price = mock_gcp.is_callable().with_args().returns_fake()
			price.has_attr(Amount=100)
			price.has_attr(Currency='EUR')
			# is enabled
			mock_isce.is_callable().with_args().returns(True)
			# test
			entry = self._catalog_entry()
			purchasable = IPurchasableCourse(entry, None)
			assert_that(purchasable, is_not(none()))
			assert_that(purchasable, has_property('NTIID', is_('tag:nextthought.com,2011-10:NTI-purchasable_course-CLC_3403')))
			assert_that(purchasable, has_property('Items', has_length(1)))
			assert_that(purchasable, has_property('Amount', is_(100)))
			assert_that(purchasable, has_property('Currency', is_('EUR')))
			items = list(purchasable.Items)
			assert_that(items, is_(['tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice']))

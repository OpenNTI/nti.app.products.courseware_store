#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property

from zope import component

from nti.app.products.courseware.interfaces import ILegacyCommunityBasedCourseInstance

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.authorization_acl import ACL

from nti.externalization.tests import externalizes

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.products.courseware.tests import LegacyInstructedCourseApplicationTestLayer

from nti.dataserver.tests import mock_dataserver
from nti.testing.matchers import validly_provides

class TestApplicationCatalogFromContent(ApplicationLayerTest):

	layer = LegacyInstructedCourseApplicationTestLayer

	@WithSharedApplicationMockDS(users=True)
	def test_course_from_content_package(self):

		lib = component.getUtility(IContentPackageLibrary)

		# New, complete info
		assert_that( lib.pathToNTIID('tag:nextthought.com,2011-10:OU-HTML-ENGR1510_Intro_to_Water.engr_1510_901_introduction_to_water'),
					 is_not( none() ) )
		# Old, legacy info
		assert_that( lib.pathToNTIID("tag:nextthought.com,2011-10:OU-HTML-CLC3403_LawAndJustice.clc_3403_law_and_justice"),
					 is_not( none() ) )

		# These content units can be adapted to course instances
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			for package in lib.contentPackages:
				inst = ICourseInstance(package)
				assert_that( inst, validly_provides(ILegacyCommunityBasedCourseInstance))
				assert_that( inst, externalizes( has_entries( 'Class', 'LegacyCommunityBasedCourseInstance',
															  'MimeType', 'application/vnd.nextthought.courses.legacycommunitybasedcourseinstance',
															  'LegacyScopes', has_entries('restricted', not_none(),
																						  'public', not_none() ) ) ) )

				acl = ACL(inst, None)
				assert_that( acl, is_( not_none() ))

				if 'LawAndJustice' in package.ntiid:
					assert_that( inst.instructors, has_length( 1 ))
					assert_that( acl, has_item(has_item(inst.instructors[0])))
					assert_that( inst.Outline, has_length(6))
					assert_that( inst.Outline["0"], has_property('title', 'Introduction'))
					assert_that( inst.Outline["0"]["0"].AvailableBeginning, is_(not_none()))
					assert_that( inst.Outline["0"]["0"].AvailableEnding, is_(not_none()))
					assert_that( inst.Outline["0"]["0"], externalizes(has_entry('AvailableEnding',
																				'2013-08-22T04:59:59Z')))

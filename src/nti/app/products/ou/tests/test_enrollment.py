#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string

from zope import component

from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.testing import ITestMailDelivery
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

class TestOuEnrollment(ApplicationLayerTest):
	layer = InstructedCourseApplicationTestLayer

	default_origin = str('http://janux.ou.edu')

	# Configure the webapp to be at the root URL
	@classmethod
	def _extra_app_settings(cls):
		return {'web_app_root': '/'}

	def _do_test_enrollment_email(self, ntiid, subject):

		username = self.extra_environ_default_user.lower()

		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(username)
			profile = IUserProfile(user)
			profile.email = 'jason.madden@nextthought.com'
			comm = Community.create_community(self.ds, username='OU')
			user.record_dynamic_membership(comm)
			user.follow(comm)

		path = '/dataserver2/users/sjohnson@nextthought.com/Courses/EnrolledCourses'

		self.testapp.post_json( path,
								{'ntiid': ntiid},
								status=201 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) ) # Not actually queueing yet
		msg = mailer.queue[0]

		assert_that( msg, has_property( 'subject', subject ) )
		return msg

	def _catalog_entry(self):
		cc = component.getUtility(ICourseCatalog)
		for cce in cc.iterCatalogEntries():
			if cce.ntiid == self.course_ntiid:
				return cce

	course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'
	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_archived_enrollment_confirmation_email(self):
		msg = self._do_test_enrollment_email( self.course_ntiid,
											  'Welcome to Law and Justice' )
		assert_that( msg, has_property( 'body', contains_string('concluded') ) )

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_enrollment_confirmation_email(self):
		with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
			cce = self._catalog_entry()
			ed = cce.EndDate
			cce.EndDate = None
			pv = cce.Preview
			cce.Preview = True

		try:
			msg = self._do_test_enrollment_email( self.course_ntiid,
												  'Welcome to Law and Justice' )
			assert_that( msg, has_property( 'body', contains_string('soon') ) )
		finally:
			with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
				cce = self._catalog_entry()
				cce.EndDate = ed
				cce.Preview = pv

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_inprogress_enrollment_confirmation_email(self):
		with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
			cce = self._catalog_entry()
			ed = cce.EndDate
			cce.EndDate = None
			pv = cce.Preview
			cce.Preview = False

		try:
			msg = self._do_test_enrollment_email( self.course_ntiid,
												  'Welcome to Law and Justice' )
			assert_that( msg, has_property( 'body', contains_string('progress') ) )
		finally:
			with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
				cce = self._catalog_entry()
				cce.EndDate = ed
				cce.Preview = pv

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_gateway_hack(self):
		with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
			cce = self._catalog_entry()
			title = cce.Title
			cce.Title = 'Gateway to College Learning'
			ed = cce.EndDate
			cce.EndDate = None
			pv = cce.Preview
			cce.Preview = True

		try:
			msg = self._do_test_enrollment_email( self.course_ntiid,
												  "Welcome to Gateway to College Learning" )
			assert_that( msg, has_property( 'body', contains_string('freshmen') ) )
		finally:
			with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
				cce = self._catalog_entry()
				cce.Title = title
				cce.EndDate = ed
				cce.Preview = pv

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string
does_not = is_not

from zope import component

from nti.app.products.ou.interfaces import IOUUserProfile

from nti.dataserver import users
from nti.dataserver.users.interfaces import IUserProfile

from nti.externalization.representation import to_json_representation

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.testing import ITestMailDelivery
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.testing.matchers import validly_provides

class TestApplicationCreateUser(ApplicationLayerTest):

	default_origin = str('http://janux.ou.edu') # only works when authenticated
	extra_environ = {str("HTTP_ORIGIN"): default_origin}

	@WithSharedApplicationMockDS(testapp=True, users=True, default_authenticate=False)
	def test_export_interested_in_credit( self ):

		app = self.testapp

		data = to_json_representation(  {'Username': 'ChrisCummings',
										 'password': 'pass123word',
										 'realname': 'Chr\u00f6s Cummings',
										 'birthdate': '1982-01-31',
										 'interested_in_credit': True,
										 'affiliation': 'school',
										 'email': 'foo@bar.com' } )

		path = b'/dataserver2/account.create'
		app.post(path, data, extra_environ=self.extra_environ)

		app = TestApp(self.app)
		res = app.get('/dataserver2/janux/UsersInterestedInCredit.csv',
					  extra_environ=self._make_extra_environ())
		assert_that(res.body,
					is_(
						b'Username,Email,Alias,Real Name\r\n'
						b'ChrisCummings,foo@bar.com,Chr\xc3\xb6s Cummings,Chr\xc3\xb6s Cummings\r\n') )

		assert_that(res.content_disposition,
					is_('attachment; filename="UsersInterestedInCredit.csv"'))


	@WithSharedApplicationMockDS(testapp=True)
	def test_create_user_ou_policy_censoring_username( self ):
		app = self.testapp
		data = to_json_representation(  {'Username': 'ChrisCummings',
										 'password': 'pass123word',
										 'realname': 'Chris Cummings',
										 'birthdate': '1982-01-31',
										 'interested_in_credit': True,
										 'affiliation': 'school',
										 'email': 'foo@bar.com' } )

		# preflight doesn't censor
		path = b'/dataserver2/account.preflight.create'
		app.post(path, data, extra_environ=self.extra_environ)
		# neither does actual
		path = b'/dataserver2/account.create'
		app.post(path, data, extra_environ=self.extra_environ)


	@WithSharedApplicationMockDS(testapp=True)
	def test_create_user_ou_policy( self ):
		app = self.testapp
		data = to_json_representation(  {'Username': 'jason2_nextthought_com',
										 'password': 'pass123word',
										 'realname': 'Joe Bananna',
										 'birthdate': '1982-01-31',
										 'interested_in_credit': True,
										 'affiliation': 'school',
										 'email': 'foo@bar.com' } )

		path = b'/dataserver2/account.create'

		res = app.post( path, data, extra_environ=self.extra_environ)
		# The right HTTP status and headers
		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )
		# The right logon cookies
		assert_that( app.cookies, has_key( 'nti.auth_tkt' ) )

		# The right User data
		assert_that( res.json_body, has_entry( 'Username', 'jason2_nextthought_com' ) )
		assert_that( res.json_body, has_entry( 'email', 'foo@bar.com' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to Janux' ) ) )
		# Be sure we picked up the right template
		assert_that( mailer.queue, has_item( has_property( 'body', contains_string( 'JANUX' ) ) ) )

		# Be sure the profile was committed correctly
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( res.json_body['Username'] )
			profile = IUserProfile(user)
			assert_that( profile, validly_provides(IOUUserProfile) )
			assert_that( profile,
						 has_property( 'email', res.json_body['email'] ) )
			assert_that( profile,
						 has_property( 'interested_in_credit', True ) )

		# And check the profile...it's correct even outside the site
		res = app.get('/dataserver2/users/jason2_nextthought_com/@@account.profile',
					  extra_environ=self._make_extra_environ(username='jason2_nextthought_com',
															 user_password='pass123word'))
		assert_that( res.json_body, has_entry( 'ProfileSchema', has_key('interested_in_credit')))

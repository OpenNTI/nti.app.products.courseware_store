#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import raises
from hamcrest import calling
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import less_than_or_equal_to

from zope.component.hooks import site

from nti.appserver.policies.site_policies import InvalidUsernamePattern

from nti.app.products.ou.logon import save_attributes
from nti.app.products.ou.views import SET_RESEARCH_VIEW
from nti.app.products.ou.interfaces import IUserResearchStatus

from nti.dataserver.users import User

from nti.externalization import externalization

from nti.site.site import get_site_for_site_names

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

# If we are using 'sites', we are an application layer
# test and must extend the appropriate test base.
# One symptom of not doing so are the problems described
# in AbstractSharedTestBase; another is the failure of
# application policies
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestUsers(ApplicationLayerTest):

	default_origin = str('http://platform.ou.edu')

	def __create_user(self, username,
					 password='temp001',
					 soonerID=None,
					 OU4x4=None,
					 **kwargs):
		ds = mock_dataserver.current_mock_ds
		user = User.create_user(ds, username=username, password=password, **kwargs)
		save_attributes(user, soonerID, OU4x4)
		return user

	@WithMockDSTrans
	def test_create_user(self):
		# This is only applicable for the OU policy
		with site( get_site_for_site_names( ('platform.ou.edu',) ) ):
			assert_that( calling(self.__create_user).with_args(username='cald3307',
															   soonerID='112133307',
															   OU4x4='cald3307'),
						 raises(InvalidUsernamePattern) )

			user = self.__create_user(username='cald3307',
									  soonerID='112133307',
									  OU4x4='cald3307',
									  external_value={'realname':'Carlos Sanchez', 'email': 'foo@bar.com'},
									  meta_data={'check_4x4':False})
			ext = externalization.to_external_object(user)

		assert_that(ext, has_entry('OUID', is_('112133307')))
		assert_that(ext, has_entry('OU4x4', is_('cald3307')))


	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_profile_fields_censored_via_direct_put(self):

		username = self.extra_environ_default_user.lower()

		bad_word = 'c2hpdA==\n'.decode('base64') # the S word
		path = '/dataserver2/users/' + username + '/++fields++affiliation'
		res = self.testapp.put( path, '"' + bad_word + '"' )

		assert_that( res, has_property( 'status_int', 200 ) )

		assert_that( res.json_body, has_entry( 'affiliation', is_not( bad_word ) ) )

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_user_research_study(self):
		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			user = User.create_user( 	username='new_user1', dataserver=self.ds,
										external_value={'realname':'Jim Bob', 'email': 'foo@bar.com'} )

			user_research = IUserResearchStatus( user )

			assert_that( user_research, not_none() )
			assert_that( user_research.allow_research, is_( False ))
			recent_mod_time = user_research.lastModified
			assert_that( recent_mod_time, not_none())

		url = '/dataserver2/users/new_user1/' + SET_RESEARCH_VIEW
		extra_environ={b'HTTP_ORIGIN': b'http://platform.ou.edu'}
		# Toggle
		data = {'allow_research':True}
		self.testapp.post_json( url, data, extra_environ=extra_environ )

		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			user = User.get_user( 'new_user1' )
			user_research = IUserResearchStatus( user )

			assert_that( user_research, not_none() )
			assert_that( user_research.allow_research, is_( True ))
			assert_that( user_research.lastModified, not_none())
			assert_that( recent_mod_time, less_than_or_equal_to( user_research.lastModified ))
			recent_mod_time = user_research.lastModified

		# And back again
		data = {'allow_research':False}
		self.testapp.post_json( url, data, extra_environ=extra_environ )

		with mock_dataserver.mock_db_trans(self.ds, site_name='platform.ou.edu'):
			user = User.get_user( 'new_user1' )
			user_research = IUserResearchStatus( user )

			assert_that( user_research, not_none() )
			assert_that( user_research.allow_research, is_( False ))
			assert_that( user_research.lastModified, not_none())
			assert_that( recent_mod_time, less_than_or_equal_to(user_research.lastModified ))

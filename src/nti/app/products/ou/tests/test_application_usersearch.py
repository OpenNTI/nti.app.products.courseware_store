#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from zope.lifecycleevent import modified

from nti.dataserver.users import Community
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestApplicationUserSearch(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_user_search_ou_policy(self):
		#"On the OU site, we cannot ONLY search for realname or alias"
		with mock_dataserver.mock_db_trans(self.ds):
			u1 = self._create_user()
			modified( u1 ) # update catalog
			u2 = self._create_user( username='sj2@nextthought.com' )
			IFriendlyNamed(u2).alias = u"Steve"
			IFriendlyNamed(u2).realname = u"Steve Jay Johnson"
			modified( u2 )
			community = Community.create_community( username='TheCommunity' )
			u1.record_dynamic_membership( community )
			u2.record_dynamic_membership( community )

		testapp = TestApp( self.app )

		# OU search is locked down to be only the username
		path = '/dataserver2/UserSearch/steve' # alias
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://janux.ou.edu'
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], contains( has_entry( 'Username', 'sj2@nextthought.com' ) ) )

		path = '/dataserver2/UserSearch/sj2@nextthought.com' # username
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://janux.ou.edu'
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.json_body['Items'], has_length( 0 ) )

		# (Though we find it elsewhere )
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.json_body['Items'], has_length( 1 ) )

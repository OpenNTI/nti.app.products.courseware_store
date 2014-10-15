#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from zope import interface

from nti.app.products.ou.logon import _is_4x4
from nti.app.products.ou.interfaces import IOUUser
from nti.app.products.ou.views import SET_RESEARCH_VIEW

from nti.dataserver import users

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.webtest import TestApp
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.testing.matchers import is_true
from nti.testing.matchers import verifiably_provides

class TestLogon(ApplicationLayerTest):

	def test_is_4x4(self):
		assert_that(_is_4x4('cald3307'), is_not(none()))
		# Some 4x4 are actually longer than that
		assert_that(_is_4x4('calton3652'), is_not(none()))
		assert_that(_is_4x4('XYZW5625'), is_not(none()))
		assert_that(_is_4x4('wu6253'), is_not(none()))
		assert_that(_is_4x4('utz1233'), is_not(none()))
		assert_that(_is_4x4('3307cald'), is_(none()))
		assert_that(_is_4x4('cald3307('), is_(none()))
		assert_that(_is_4x4('cald'), is_(none()))
		assert_that(_is_4x4('3307'), is_(none()))

	@WithSharedApplicationMockDS
	@fudge.patch('nti.app.products.ou.logon.connection_pool',
				 'nti.app.products.ou.logon.is_valid_ou_user')
	def test_create_user_using_ldap(self, mock_pool, mock_is):

		fakePool = mock_pool.is_callable().returns_fake()
		fakeConn = fakePool.provides('connection').returns_fake()
		fakeConn.provides('simple_bind_s').is_callable()

		# there seems to be a bug in fudge that prevents faking
		# context managers in python 2.6/2.8
		# https://bitbucket.org/kumar303/fudge/issue/12/use-as-a-context-manager-doesnt-work-in
		# to make it work set the CM methods a the class level
		fakeConn.__class__.__exit__ = lambda s, *args, **kwargs: True
		fakeConn.__class__.__enter__ = lambda s, *args, **kwargs: s

		mock_is.is_callable().with_args().returns([('CN=36684,OU=General',
													{'givenName':['Carlos Sanchez'],
													 'employeeNumber': ['112133307']})])
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp(self.app)
		# This works with both @@logon.ldap.ou and the bare version,
		# due to views being used when traversal stop
		path = '/dataserver2/logon.ldap.ou'
		environ = self._make_extra_environ(user=b'cald3307', user_password=b'saulo213')
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(username=b'112133307')
			assert_that( user, has_property('soonerID', '112133307') )
			assert_that( user, verifiably_provides( IOUUser ) )
			assert_that( user.has_password(), is_true() )
			assert_that( user.password.checkPassword('saulo213'), is_true() )

		# And hitting again updates the password, if needed
		environ = self._make_extra_environ(user=b'cald3307', user_password=b'abcd')
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(username=b'112133307')
			assert_that( user, has_property('soonerID', '112133307') )
			assert_that( user, verifiably_provides( IOUUser ) )
			assert_that( user.has_password(), is_true() )
			assert_that( user.password.checkPassword('abcd'), is_true() )

		# Make sure we don't get back a password logon link
		# drop cookies so we're not authd
		testapp = TestApp(self.app)
		res = testapp.post('/dataserver2/logon.handshake', params={'username': 'cald3307'},
							extra_environ={b'HTTP_ORIGIN': b'http://platform.ou.edu'} )

		self.require_link_href_with_rel( res.json_body, 'logon.ldap.ou' )

	@WithSharedApplicationMockDS(testapp=True,
								 users=None,
								 user_hook=lambda u: interface.alsoProvides( u, IOUUser))
	@fudge.patch('nti.app.products.ou.logon.is_valid_ou_user')
	def test_link_for_user(self, mock_is):
		mock_is.is_callable().returns(True)
		testapp = self.testapp

		# In the site, we get the link for missing users
		res = testapp.post( '/dataserver2/logon.handshake?username=madd2844',
						   extra_environ={b'HTTP_ORIGIN': b'http://platform.ou.edu'})
		href = self.require_link_href_with_rel( res.json_body, 'logon.ldap.ou' )
		assert_that( href, is_( '/dataserver2/@@logon.ldap.ou' ) )

	extra_environ_default_user = 'new_user1'

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_research_status_link(self):
		url = '/dataserver2/users/new_user1/' + SET_RESEARCH_VIEW
		extra_environ={b'HTTP_ORIGIN': b'http://platform.ou.edu'}
		res = self.resolve_user( extra_environ=extra_environ )
		href = self.require_link_href_with_rel( res, SET_RESEARCH_VIEW )
		assert_that( href, is_( url ) )

		self.require_link_href_with_rel( res, 'irb_pdf' )
		self.require_link_href_with_rel( res, 'irb_html' )

		# Set
		data = {'allow_research':True}
		self.testapp.post_json( url, data, extra_environ=extra_environ )

		# Subsequent call does not have link
		href = self.forbid_link_with_rel(self.resolve_user( extra_environ=extra_environ ),
										 SET_RESEARCH_VIEW )

	@WithSharedApplicationMockDS(testapp=True,
								 users=False,
								 user_hook=lambda u: interface.alsoProvides(u, IOUUser))
	@fudge.patch('nti.app.products.ou.logon.is_valid_ou_user')
	def test_exception_view_for_backend_failure(self, fake_is):
		from ldappool import BackendError
		def _r(*args):
			raise BackendError('Error', None)
		fake_is.is_callable().calls(_r)
		self.testapp.post( '/dataserver2/logon.handshake?username=madd2844',
						   extra_environ={b'HTTP_ORIGIN': b'http://platform.ou.edu'},
						   status=502)

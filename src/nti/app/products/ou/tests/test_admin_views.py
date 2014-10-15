#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import simplejson as json

from nti.dataserver import users

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.app.products.ou.views import SET_RESEARCH_VIEW

class TestAdminViews(ApplicationLayerTest):

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_set_user_attributes(self):
		username = 'cald3307'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.post('/dataserver2/janux/ou_set_user_attributes',
						   json.dumps({'username': 'cald3307'}),
						   extra_environ=environ,
						   status=200)
		if not res.json_body['Errors']:
			assert_that(res.json_body['Items'], has_length(1))
			with mock_dataserver.mock_db_trans(self.ds):
				user = users.User.get_user(username)
				assert_that(user, has_property('OU4x4', is_('cald3307')))
				assert_that(user, has_property('soonerID', is_('112133307')))

		testapp = TestApp(self.app)
		res = testapp.post('/dataserver2/janux/ou_set_user_attributes',
						   extra_environ=environ,
						   status=200)
		if not res.json_body['Errors']:
			assert_that(res.json_body['Items'], has_length(0))

		username = 'tryt3968'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)

		res = testapp.post('/dataserver2/janux/ou_set_user_attributes',
						   json.dumps({'term': 'tryt'}),
						   extra_environ=environ,
						   status=200)
		if not res.json_body['Errors']:
			assert_that(res.json_body['Items'], has_length(1))

			with mock_dataserver.mock_db_trans(self.ds):
				user = users.User.get_user(username)
				assert_that(user, has_property('OU4x4', is_('tryt3968')))
				assert_that(user, has_property('soonerID', is_('112113968')))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_get_research_stats(self):
		username = 'cald3307'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get('/dataserver2/janux/ou_user_research_stats',
						   None,
						   extra_environ=environ,
						   status=200)
		body = res.json_body
		assert_that( body['AllowResearchCount'], is_( 0 ))
		assert_that( body['DenyResearchCount'], is_( 0 ))
		assert_that( body['ToBePromptedCount'], is_( 2 ))

		url = '/dataserver2/users/cald3307/' + SET_RESEARCH_VIEW
		# Set
		data = {'allow_research':True}
		testapp.post_json( url, data, extra_environ=environ )

		# Re-query
		res = testapp.get('/dataserver2/janux/ou_user_research_stats',
						   None,
						   extra_environ=environ,
						   status=200)
		body = res.json_body
		assert_that( body['AllowResearchCount'], is_( 1 ))
		assert_that( body['DenyResearchCount'], is_( 0 ))
		assert_that( body['ToBePromptedCount'], is_( 1 ))

		# Reverse
		data = {'allow_research':False}
		testapp.post_json( url, data, extra_environ=environ )

		# Re-query
		res = testapp.get('/dataserver2/janux/ou_user_research_stats',
						   None,
						   extra_environ=environ,
						   status=200)
		body = res.json_body
		assert_that( body['AllowResearchCount'], is_( 0 ))
		assert_that( body['DenyResearchCount'], is_( 1 ))
		assert_that( body['ToBePromptedCount'], is_( 1 ))

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property
does_not = is_not

import unittest

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

class TestOUStaticViewsWebappAtRoot(ApplicationLayerTest):

	# Configure the webapp to be at the root URL
	@classmethod
	def _extra_app_settings(cls):
		return {'web_app_root': '/'}

	@unittest.skip("Doesn't test much and doesn't work in the layer; expensive")
	@WithSharedApplicationMockDS(testapp=True)
	def test_get_webapp_site_css_at_root(self):

		path = '/resources/css/site.css'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		self.testapp.get(path, extra_environ=environ, status=200)

class TestOUStaticViewsWebappAtDefault(ApplicationLayerTest):

	# Configure the webapp to be at the usual URL
	@classmethod
	def _extra_app_settings(cls):
		return {'web_app_root': '/NextThoughtWebApp/'}

	hosts = (b'ou-test.nextthought.com', b'ou-alpha.nextthought.com',
			 b'platform.ou.edu', b'janux.ou.edu')

	@WithSharedApplicationMockDS(testapp=True)
	def test_get_webapp_site_css_at_full(self):

		for host in self.hosts:
			path = '/NextThoughtWebApp/resources/css/site.css'
			environ = self._make_extra_environ()
			environ[b'HTTP_ORIGIN'] = b'http://' + host

			self.testapp.get(path, extra_environ=environ, status=200)

	@WithSharedApplicationMockDS(testapp=True)
	def test_get_webapp_test_site_js_at_full(self):

		for host in self.hosts:

			path = '/NextThoughtWebApp/resources/strings/site.js'
			environ = self._make_extra_environ()
			environ[b'HTTP_ORIGIN'] = b'http://' + host

			res = self.testapp.get(path, extra_environ=environ, status=200)
			assert_that( res, has_property( 'content_length',
											greater_than( 0 ) ) )

	@WithSharedApplicationMockDS(testapp=True)
	def test_create_disabled_outest(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://ou-test.nextthought.com'
		self.testapp.get('/dataserver2/account.create',
						 extra_environ=environ,
						 status=401)

		res = self.testapp.get('/dataserver2/logon.ping', extra_environ=environ)
		__traceback_info__ = res.json_body
		assert_that( res.json_body['Links'],
					 does_not( has_item( has_entry( 'rel', 'account.create'))))

	@WithSharedApplicationMockDS(testapp=True)
	def test_create_enabled_janux(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://janux.ou.edu'

		res = self.testapp.get('/dataserver2/logon.ping', extra_environ=environ)
		__traceback_info__ = res.json_body
		assert_that( res.json_body['Links'],
					 has_item( has_entry( 'rel', 'account.create')))


	@WithSharedApplicationMockDS(testapp=True)
	def test_create_enabled_oualpha(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://ou-alpha.nextthought.com'

		res = self.testapp.get('/dataserver2/logon.ping', extra_environ=environ)
		__traceback_info__ = res.json_body
		assert_that( res.json_body['Links'],
					 has_item( has_entry( 'rel', 'account.create')))

from nti.app.testing.application_webtest import Library
from nti.app.testing.application_webtest import GCLayerMixin
from nti.app.testing.application_webtest import DSInjectorMixin
from nti.app.testing.application_webtest import PyramidLayerMixin
from nti.app.testing.application_webtest import ZopeComponentLayer
from nti.app.testing.application_webtest import ConfiguringLayerMixin
from nti.app.testing.application_webtest import AppCreatingLayerHelper

class AtAppLayer(ZopeComponentLayer,
				 PyramidLayerMixin,
				 GCLayerMixin,
				 ConfiguringLayerMixin,
				 DSInjectorMixin):
	features = ('forums',)
	set_up_packages = () # None, because configuring the app will do this
	APP_IN_DEVMODE = True
	configure_events = False # We have no packages, but we will set up the listeners ourself when configuring the app

	@classmethod
	def _setup_library(cls, *args, **kwargs):
		return Library()

	# Configure the webapp to be at the usual URL
	@classmethod
	def _extra_app_settings(cls):
		return {'web_app_root': '/app/'}

	@classmethod
	def setUp(cls):
		AppCreatingLayerHelper.appSetUp(cls)

	@classmethod
	def tearDown(cls):
		AppCreatingLayerHelper.appTearDown(cls)

	@classmethod
	def testSetUp(cls, test=None):
		AppCreatingLayerHelper.appTestSetUp(cls, test)

	@classmethod
	def testTearDown(cls, test=None):
		AppCreatingLayerHelper.appTestTearDown(cls, test)

class TestOUStaticViewsWebappAtApp(ApplicationLayerTest):

	layer = AtAppLayer

	hosts = (b'ou-test.nextthought.com', b'ou-alpha.nextthought.com',
			 b'platform.ou.edu', b'janux.ou.edu')

	@WithSharedApplicationMockDS(testapp=True)
	def test_get_webapp_site_css_at_full(self):

		for host in self.hosts:
			path = '/app/resources/css/site.css'
			environ = self._make_extra_environ()
			environ[b'HTTP_ORIGIN'] = b'http://' + host

			self.testapp.get(path, extra_environ=environ, status=200)

	@WithSharedApplicationMockDS(testapp=True)
	def test_get_webapp_test_site_js_at_full(self):

		for host in self.hosts:

			path = '/app/resources/strings/site.js'
			environ = self._make_extra_environ()
			environ[b'HTTP_ORIGIN'] = b'http://' + host

			res = self.testapp.get(path, extra_environ=environ, status=200)
			assert_that( res, has_property( 'content_length',
											greater_than( 0 ) ) )

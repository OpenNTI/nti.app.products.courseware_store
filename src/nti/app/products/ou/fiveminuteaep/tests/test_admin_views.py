#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_string

import fudge

from nti.app.products.ou.fiveminuteaep.utils import get_course_key

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges

from nti.app.products.ou.fiveminuteaep.tests import FiveMinuteAEPApplicationLayerTest

class TestAdminViews(FiveMinuteAEPApplicationLayerTest):

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session',
				 'nti.app.products.ou.fiveminuteaep.process.find_ou_courses')
	def test_set_state(self, mock_rs, mock_fc):
		course_key = get_course_key('13004', '201350')
		mock_fc.is_callable().returns({course_key: fudge.Fake('course')})

		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('get').is_callable().with_args().returns_fake()
		response.has_attr(status_code=200)
		response.provides('json').is_callable().returns(
		{
    		"Status": 200,
    		"State": True,
		  	'MESSAGE': 'Success'
		})

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		# DNE
		user_dne = 'testuser@nextthought.com'
		testapp.post_json('/dataserver2/janux/fmaep_set_state',
				 		  {	"username": user_dne, "state": 'Admitted', "PIDM":'12345'},
							extra_environ=environ,
						   	status=422)

		# Valid user; bad-state
		user_valid = self.extra_environ_default_user
		testapp.post_json('/dataserver2/janux/fmaep_set_state',
			 			  {"username": user_valid, "state" : 'accepted', "PIDM":'12345'},
						  extra_environ=environ,
						  status=422)

		# Admitted
		res = testapp.post_json('/dataserver2/janux/fmaep_set_state',
					 				{ "username": user_valid, "state" : 'admitted', "PIDM":'12345'},
							   		extra_environ=environ,
							   		status=200)

		result = res.json_body
		assert_that(result, has_entry(user_valid, contains_string( 'Admitted' ) ) )

		# Pending
		res = testapp.post_json('/dataserver2/janux/fmaep_set_state',
					 				{ "username": user_valid, "state" : 'pending', "tempmatchid":'12345'},
							   		extra_environ=environ,
							   		status=200)

		result = res.json_body
		assert_that(result, has_entry(user_valid, contains_string( 'Pending' ) ) )

		# Rejected
		res = testapp.post_json('/dataserver2/janux/fmaep_set_state',
					 				{ "username": user_valid, "state" : 'REJECTED', "tempmatchid":'12345'},
							   		extra_environ=environ,
							   		status=200)

		result = res.json_body
		assert_that(result, has_entry(user_valid, contains_string( 'Rejected' ) ) )

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_urls(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get('/dataserver2/janux/fmaep_urls',
						  extra_environ=environ,
						  status=200)
			
		result = res.json_body
		assert_that(result, has_length(8))

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property

import unittest

from requests.exceptions import Timeout

from nti.app.products.ou.fiveminuteaep.utils.net import request_session

class TestNet(unittest.TestCase):

	def test_request_session(self):
		session = request_session(tlsv1=False, timeout=5)
		assert_that(session, has_property('timeout', is_(5)))
		try:
			res = session.get('http://www.google.com')
			assert_that(res, has_property('content', has_length(greater_than(0))))
		except Timeout:
			pass

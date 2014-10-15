#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import fudge

from nti.dataserver.users import User

from nti.app.products.ou.fiveminuteaep.utils.cypher import create_token
from nti.app.products.ou.fiveminuteaep.utils.cypher import get_plaintext

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

class TestCypher(DataserverLayerTest):

    def _create_user(self, username='nt@nti.com', password='temp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr
    
    @WithMockDSTrans
    @fudge.patch('nti.app.products.ou.fiveminuteaep.utils.cypher.get_uid')
    def test_request_session(self, mock_uid):
        mock_uid.is_callable().with_args().returns(100)
        user = self._create_user()
        token = create_token(user, '123', 13004, '201350', 'https://bleach.org', 2)
        assert_that(token, is_('X0RwX0RZH1NfXDkBAwM5AAMAAQQ5AwABAgUAOFhERUBDCx8fU1xVUFNYH19CVjkC'))
        text = get_plaintext(user, token)
        assert_that(text, is_('nt@nti.com\t123\t13004\t201350\thttps://bleach.org\t2'))

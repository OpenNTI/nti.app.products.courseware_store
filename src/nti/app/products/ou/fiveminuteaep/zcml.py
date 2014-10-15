#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from .model import Credentials
from .interfaces import ICredentials

class IRegisterCredentials(interface.Interface):
	name = fields.TextLine(title="credential identifier", required=False, default='')
	username = fields.TextLine(title="username", required=True)
	password = fields.TextLine(title="password", required=True)
	
def registerCredentials(_context, username, password, name=''):
	factory = functools.partial(Credentials, username=username, password=password)
	utility(_context, provides=ICredentials, factory=factory, name=name)

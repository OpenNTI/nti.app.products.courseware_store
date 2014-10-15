#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.deprecation import deprecated
from zope.annotation.factory import factory as an_factory

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser

from .interfaces import IOUUser
from .interfaces import IUserResearchStatus

deprecated('OUUser', 'Use OU Profile')
@interface.implementer(IOUUser)
class OUUser(User):
	__external_class_name__ = 'User'

	OU4x4 = soonerID = None

	def __init__(self, username, **kwargs):
		OU4x4 = kwargs.pop('OU4x4', None)
		soonerID = kwargs.pop('soonerID', None)
		super(OUUser, self).__init__(username, **kwargs)
		if OU4x4:
			self.OU4x4 = OU4x4
		if soonerID:
			self.soonerID = soonerID

@component.adapter(IUser)
@interface.implementer(IUserResearchStatus)
class _Researchable(PersistentCreatedAndModifiedTimeObject):

	_SET_CREATED_MODTIME_ON_INIT = False

	def __init__(self):
		PersistentCreatedAndModifiedTimeObject.__init__(self)
		self.allow_research = False
		self.lastModified = None

_UserResearchStatus = an_factory(_Researchable, 'research_status')

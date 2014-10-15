#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.container.contained import Contained
from zope.annotation import factory as an_factory

from persistent import Persistent
from persistent.mapping import PersistentMapping

from nti.externalization.persistence import NoPickle
from nti.externalization.representation import WithRepr

from nti.dataserver.interfaces import IUser
from nti.dataserver.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

from nti.schema.schema import EqHash
from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.zodb.persistentproperty import PersistentPropertyHolder

from .interfaces import PENDING
from .interfaces import SUCCESS
from .interfaces import ADMITTED
from .interfaces import SUSPENDED

from .interfaces import ICredentials
from .interfaces import IPaymentRecord
from .interfaces import IPaymentStorage
from .interfaces import IUserAdmissionData
from .interfaces import IEnrollmentStorage
from .interfaces import IUserAdmissionProfile

@interface.implementer(ICredentials)
@NoPickle
@WithRepr
@EqHash('username')
class Credentials(SchemaConfigured):
	createDirectFieldProperties(ICredentials)

	def __str__(self):
		return self.username

# profile

@interface.implementer(IUserAdmissionProfile)
class UserAdmissionProfile(Contained, SchemaConfigured, Persistent):
	createDirectFieldProperties(IUserAdmissionProfile)

	def __init__(self, *args, **kwargs):
		Persistent.__init__(self)
		SchemaConfigured.__init__(self, *args, **kwargs) # not cooperative

# admision

@component.adapter(IUser)
@interface.implementer(IUserAdmissionData)
class UserAdmissionData(Contained, SchemaConfigured, Persistent):
	createDirectFieldProperties(IUserAdmissionData)

	def __init__(self, *args, **kwargs):
		Persistent.__init__(self)
		SchemaConfigured.__init__(self, *args, **kwargs) # not cooperative
		
	def is_pending(self):
		return self.state == PENDING

	def is_admitted(self):
		return self.state == ADMITTED
	
	def is_suspended(self):
		return self.state == SUSPENDED

_UserAdmissionDataFactory = an_factory(UserAdmissionData)

# Payment

@interface.implementer(IPaymentRecord)
@WithRepr
class PaymentRecord(Contained,
					SchemaConfigured,
					CreatedAndModifiedTimeMixin,
					PersistentPropertyHolder):
	createDirectFieldProperties(IPaymentRecord)

	payURL = None
	attempts = 0

	def __init__(self, *args, **kwargs):
		PersistentPropertyHolder.__init__(self)
		SchemaConfigured.__init__(self, *args, **kwargs)
		CreatedAndModifiedTimeMixin.__init__(self)

	def is_pending(self):
		return self.state == PENDING
	
	def is_success(self):
		return self.state == SUCCESS

@component.adapter(IUser)
@interface.implementer(IPaymentStorage)
class DefaultPaymentStorage(CaseInsensitiveCheckingLastModifiedBTreeContainer):
	pass

_DefaultPaymentStorageFactory = an_factory(DefaultPaymentStorage)

# enrollment

@component.adapter(IUser)
@interface.implementer(IEnrollmentStorage)
class DefaultEnrollmentStorage(PersistentMapping):
	pass

_DefaultEnrollmentStorageFactory = an_factory(DefaultEnrollmentStorage)

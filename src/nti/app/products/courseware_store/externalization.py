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

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from .interfaces import IStoreEnrollmentOption

CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE

@component.adapter(IStoreEnrollmentOption)
@interface.implementer(IInternalObjectExternalizer)
class _StoreEnrollmentOptionExternalizer(object):
	
	def __init__(self, obj):
		self.obj = obj

	def toExternalObject(self, *args, **kwargs):
		result = LocatedExternalDict()
		result[MIMETYPE] = self.obj.mimeType
		result[CLASS] = self.obj.__external_class_name__
		result['RequiresAdmission'] = False
		result['IsEnabled'] = self.obj.IsEnabled
		result['AllowVendorUpdates'] = self.obj.AllowVendorUpdates
		## purchasables
		items = []
		result['Purchasables'] = { ITEMS:items }
		for purchasable in self.obj.Purchasables:
			ext_obj = to_external_object(purchasable, name='summary')
			items.append(ext_obj)
		## legacy
		result['Purchasable'] = items[0]
		result['Price'] = items[0].get('Amount', None)
		result['Currency'] = items[0].get('Currency', None)
		return result

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
		defaultGifting = None
		defaultPurchase = None
		length = len(self.obj.Purchasables)
		result['Purchasables'] = { ITEMS:items }
		for idx in range(length):
			purchasable = self.obj.Purchasables[idx]
			if not defaultPurchase:
				defaultPurchase = purchasable.NTIID
			ext_obj = to_external_object(purchasable, name='summary')
			items.append(ext_obj)
			purchasable = self.obj.Purchasables[length-idx-1]
			if not defaultGifting:
				defaultGifting = purchasable.NTIID
		result['Purchasables']['DefaultGiftingNTIID'] = defaultGifting
		result['Purchasables']['DefaultPurchaseNTIID'] = defaultPurchase
		return result

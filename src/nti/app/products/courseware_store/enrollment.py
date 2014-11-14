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
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.app.products.courseware.enrollment import EnrollmentOption
from nti.app.products.courseware.interfaces import IEnrollmentOptionProvider

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.externalization.persistence import NoPickle
from nti.externalization.representation import WithRepr
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.externalization import to_external_object
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.store.purchasable import get_purchasable

from .interfaces import IStoreEnrollmentOption

from .utils import allow_vendor_updates
from .utils import get_entry_purchasable_ntiid
from .utils import get_entry_purchasable_provider

CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE

@interface.implementer(IStoreEnrollmentOption, IInternalObjectExternalizer)
@WithRepr
@NoPickle
class StoreEnrollmentOption(EnrollmentOption):

	__external_class_name__ = "StoreEnrollment"
	mime_type = mimeType = 'application/vnd.nextthought.courseware.storeenrollmentoption'

	Purchasable = FP(IStoreEnrollmentOption['Purchasable'])
	AllowVendorUpdates = FP(IStoreEnrollmentOption['AllowVendorUpdates'])
	
	def is_enrolled(self, context):
		pass
		
	def toExternalObject(self, *args, **kwargs):
		result = LocatedExternalDict()
		result[MIMETYPE] = self.mimeType
		result[CLASS] = self.__external_class_name__
		ext_obj = to_external_object(self.Purchasable, name='summary')
		result['Purchasable'] = ext_obj
		result['RequiresAdmission'] = False
		result['Price'] = ext_obj.get('Amount', None)
		result['Currency'] = ext_obj.get('Currency', None)
		result['AllowVendorUpdates'] = self.AllowVendorUpdates
		return result

@component.adapter(ICourseCatalogEntry)
@interface.implementer(IEnrollmentOptionProvider)
class StoreEnrollmentOptionProvider(object):

	def __init__(self, context):
		self.context = context
		
	def iter_options(self):
		provider = get_entry_purchasable_provider(self.context)
		ntiid = get_entry_purchasable_ntiid(self.context, provider)
		purchasable = get_purchasable(ntiid) if ntiid else None
		if purchasable is not None and purchasable.Public:
			result = StoreEnrollmentOption()
			result.Purchasable = purchasable
			result.CatalogEntryNTIID = self.context.ntiid
			result.AllowVendorUpdates = allow_vendor_updates(self.context)
			return (result,)
		return ()

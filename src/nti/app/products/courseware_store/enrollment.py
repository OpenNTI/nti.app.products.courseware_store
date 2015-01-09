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

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseSubInstance
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
		
	def get_purchasable(self, context):
		provider = get_entry_purchasable_provider(context)
		ntiid = get_entry_purchasable_ntiid(context, provider)
		purchasable = get_purchasable(ntiid) if ntiid else None
		return purchasable
	
	def get_context(self):
		course = ICourseInstance(self.context)
		purchasable = self.get_purchasable(self.context)
		## CS: if we cannot get a purchasable and the context course is a 
		## sub-instance try with its parent course. This may happen
		## with mapped courses
		if 	(purchasable is None or not purchasable.Public) and \
			ICourseSubInstance.providedBy(course):
			result = ICourseCatalogEntry(course.__parent__.__parent__)
		else:
			result = self.context
		return result
		
	def iter_options(self):
		context = self.get_context()
		purchasable = self.get_purchasable(context)
		if purchasable is not None and purchasable.Public:
			result = StoreEnrollmentOption()
			result.Purchasable = purchasable
			result.CatalogEntryNTIID = context.ntiid
			result.AllowVendorUpdates = allow_vendor_updates(context)
			return (result,)
		return ()

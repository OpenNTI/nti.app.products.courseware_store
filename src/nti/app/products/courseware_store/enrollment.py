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

from nti.common.representation import WithRepr

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseSubInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.store.purchasable import get_purchasable

from .interfaces import IStoreEnrollmentOption

from .utils import allow_vendor_updates
from .utils import get_entry_purchasable_ntiid
from .utils import get_entry_purchasable_provider
from .utils import get_purchasable_course_bundles

def get_entry_purchasable(context):
	provider = get_entry_purchasable_provider(context)
	ntiid = get_entry_purchasable_ntiid(context, provider)
	purchasable = get_purchasable(ntiid) if ntiid else None
	return purchasable
	
def get_entry_context(context):
	course = ICourseInstance(context)
	purchasable = get_entry_purchasable(context)
	# CS: if we cannot get a purchasable and the context course is a 
	# sub-instance try with its parent course. This may happen
	# with mapped courses
	if 	(purchasable is None or not purchasable.Public) and \
		ICourseSubInstance.providedBy(course):
		result = ICourseCatalogEntry(course.__parent__.__parent__)
	else:
		result = context
	return result

@WithRepr
@interface.implementer(IStoreEnrollmentOption)
class StoreEnrollmentOption(EnrollmentOption):

	__external_class_name__ = "StoreEnrollment"
	mime_type = mimeType = 'application/vnd.nextthought.courseware.storeenrollmentoption'

	IsEnabled = FP(IStoreEnrollmentOption['IsEnabled'])
	Purchasables = FP(IStoreEnrollmentOption['Purchasables'])
	AllowVendorUpdates = FP(IStoreEnrollmentOption['AllowVendorUpdates'])

@component.adapter(ICourseCatalogEntry)
@interface.implementer(IEnrollmentOptionProvider)
class StoreEnrollmentOptionProvider(object):

	def __init__(self, context):
		self.context = context
		
	def get_purchasables(self, context):
		result = []
		direct = get_entry_purchasable(context)
		if direct is not None and direct.Public: # direct purchasable
			result.append(direct)
		result.extend(get_purchasable_course_bundles(context))
		return result

	def get_context(self):
		return get_entry_context(self.context)

	def iter_options(self):
		context = self.get_context()
		purchasables = self.get_purchasables(context)
		if purchasables:
			result = StoreEnrollmentOption()
			result.Purchasables = purchasables
			IsEnabled = reduce(lambda x,y: x or y.Public, purchasables, False)
			result.IsEnabled = IsEnabled
			# CS: We want to use the original data
			result.CatalogEntryNTIID = self.context.ntiid
			result.AllowVendorUpdates = allow_vendor_updates(self.context)
			return (result,)
		return ()

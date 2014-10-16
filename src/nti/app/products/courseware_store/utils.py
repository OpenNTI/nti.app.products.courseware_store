#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from itertools import chain

from zope import component
from zope.traversing.api import traverse

from dolmen.builtins.interfaces import IString

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.store.interfaces import IPurchasableCourse

from .model import CoursePrice
from .interfaces import ICoursePrice

def get_vendor_info(course):
	return ICourseInstanceVendorInfo(course, {})

def is_course_enabled_for_purchase(course):
	vendor_info = get_vendor_info(course)
	result = traverse(vendor_info, 'NTI/Purchasable/Enabled', default=False)
	return result

def is_course_giftable(course):
	vendor_info = get_vendor_info(course)
	result = traverse(vendor_info, 'NTI/Purchasable/Giftable', default=False)
	return result

def get_course_purchasable_provider(course):
	vendor_info = get_vendor_info(course)
	result = traverse(vendor_info, 'NTI/Purchasable/Provider', default=None)
	return result

def get_course_price(course, *names):
	names = chain(names, ('',)) if names else ('',)
	for name in names:
		result = component.queryAdapter(course,  ICoursePrice, name=name)
		if result is not None:
			return result
	return None

def get_course_purchasable_ntiid(entry, name=None):
	result = None
	entry = ICourseCatalogEntry(entry)
	if name:
		result = component.queryAdapter(entry, IString, name=name)
	if not result:
		result = component.getAdapter(entry, IString, name="purchasable_course_ntiid")
	return result

def get_nti_course_price(context):
	course = ICourseInstance(context, None)
	vendor_info = get_vendor_info(course)
	amount = traverse(vendor_info, 'NTI/Purchasable/Price', default=None)
	currency = traverse(vendor_info, 'NTI/Purchasable/Currency', default='USD')
	if amount:
		result = CoursePrice(Amount=float(amount), Currency=currency)
		return result
	return None

def register_purchasables():
	result = []
	catalog = component.getUtility(ICourseCatalog)
	for catalog_entry in catalog.iterCatalogEntries():
		purchasable = IPurchasableCourse(catalog_entry, None)
		name = getattr(purchasable, 'NTIID', None)
		if 	purchasable is not None and name and \
			component.queryUtility(IPurchasableCourse, name=name) is None:
			logger.info("Registering course purchasable %s", purchasable.NTIID)
			component.provideUtility(purchasable, IPurchasableCourse, name=name)
			result.append(purchasable)
	return result

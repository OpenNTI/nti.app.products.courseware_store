#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.traversing.api import traverse
from zope.component.interfaces import IComponents
from zope.component.hooks import site as current_site

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.processlifetime import IApplicationTransactionOpenedEvent

from nti.site.interfaces import IHostPolicyFolder
from nti.site.site import get_site_for_site_names

from nti.store.interfaces import IPurchasableCourse

from .. import sites as ou_sites
from ..courseware.interfaces import ICoursePrice

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

def get_course_price(course):
	result = ICoursePrice(course, None)
	return result

def register_purchasables():
	catalog = component.getUtility(ICourseCatalog)
	for catalog_entry in catalog.iterCatalogEntries():
		purchasable = IPurchasableCourse(catalog_entry, None)
		name = getattr(purchasable, 'NTIID', None)
		if 	purchasable is not None and \
			component.queryUtility(IPurchasableCourse, name=name) is None:
			logger.info("Registering course purchasable %s", purchasable.NTIID)
			component.provideUtility(purchasable, IPurchasableCourse, name=name)

@component.adapter(IApplicationTransactionOpenedEvent)
def register_site_purchasables(*args, **kwargs):
	for v in ou_sites.__dict__.values():
		if not IComponents.providedBy(v):
			continue
		name  = v.__name__
		site = get_site_for_site_names((name,))
		if not IHostPolicyFolder.providedBy(site):
			continue
		with current_site(site):
			register_purchasables()

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
from zope import lifecycleevent
from zope.traversing.api import traverse
from zope.security.interfaces import IPrincipal

from dolmen.builtins.interfaces import IString

from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.ntiids.ntiids import get_parts

from nti.store.store import get_purchasable
from nti.store.store import get_purchase_history_by_item

from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IInvitationPurchaseAttempt

from nti.utils.maps import CaseInsensitiveDict

from .model import CoursePrice

from .interfaces import ICoursePrice

def get_vendor_info(context):
	course = ICourseInstance(context, None)
	return ICourseInstanceVendorInfo(course, {})

def is_course_enabled_for_purchase(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/Enabled', default=False)
	return result

def is_course_giftable(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/Giftable', default=False)
	return result

def is_course_redeemable(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/Giftable', default=False)
	return result

def get_course_purchasable_provider(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/Provider', default=None)
	return result

def get_course_purchasable_name(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/Name', default=None)
	return result

def get_course_purchasable_title(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/Title', default=None)
	return result

def get_entry_purchasable_provider(context):
	entry = ICourseCatalogEntry(context)
	course = ICourseInstance(entry)
	parts = get_parts(entry.ntiid)
	provider = get_course_purchasable_provider(course) or parts.provider
	return provider

def get_course_price(context, *names):
	course = ICourseInstance(context, None)
	names = chain(names, ('',)) if names else ('',)
	for name in names:
		result = component.queryAdapter(course,  ICoursePrice, name=name)
		if result is not None:
			return result
	return None

def get_course_purchasable_ntiid(context, name=None):
	result = None
	entry = ICourseCatalogEntry(context)
	if name:
		result = component.queryAdapter(entry, IString, name=name)
	if not result:
		result = component.getAdapter(entry, IString, name="purchasable_course_ntiid")
	return result
get_entry_purchasable_ntiid = get_course_purchasable_ntiid

def get_nti_course_price(context):
	vendor_info = get_vendor_info(context)
	amount = traverse(vendor_info, 'NTI/Purchasable/Price', default=None)
	currency = traverse(vendor_info, 'NTI/Purchasable/Currency', default='USD')
	if amount:
		result = CoursePrice(Amount=float(amount), Currency=currency)
		return result
	return None

def allow_vendor_updates(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/AllowVendorUpdates', default=False)
	return bool(result) if result is not None else False

def register_purchasables(catalog=None):
	result = []
	catalog = catalog or component.getUtility(ICourseCatalog)
	for catalog_entry in catalog.iterCatalogEntries():
		purchasable = IPurchasableCourse(catalog_entry, None)
		name = getattr(purchasable, 'NTIID', None)
		if 	purchasable is not None and name and \
			component.queryUtility(IPurchasableCourse, name=name) is None:
			component.provideUtility(purchasable, IPurchasableCourse, name=name)
			result.append(purchasable)
			lifecycleevent.created(purchasable)
			logger.debug("Purchasable %s was registered for course %s",
						 purchasable.NTIID, catalog_entry.ntiid)
	return result

def find_allow_vendor_updates_users(entry, invitation=False):
	catalog = component.getUtility(ICourseCatalog)
	try:
		if not ICourseCatalogEntry.providedBy(entry):
			entry = catalog.getCatalogEntry(str(entry))
		
		provider = get_entry_purchasable_provider(entry)
		ntiid = get_entry_purchasable_ntiid(entry, provider)
		purchasable = get_purchasable(ntiid)
		if purchasable is not None and purchasable.Public:
			result = []
			course = ICourseInstance(entry)
			enrollments = ICourseEnrollments(course)
			for enrollment in enrollments.iter_enrollments():
				# check purchase enrollments only
				if enrollment.Scope != ES_PURCHASED:
					continue
				
				user = enrollment.Principal
				if IPrincipal(user, None) is None:
					# ignore dup enrollment
					continue
				
				purchases = get_purchase_history_by_item(user, ntiid)
				for purchase in purchases or ():
					if invitation and IInvitationPurchaseAttempt.providedBy(purchase):
						continue
					context = CaseInsensitiveDict(purchase.Context or {})
					if context.get('AllowVendorUpdates', False):
						result.append(user.username)
						break
			return result
	except KeyError:
		logger.debug("Could not find course entry %s", entry)
	return ()

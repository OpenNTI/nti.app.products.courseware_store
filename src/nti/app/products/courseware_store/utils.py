#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from itertools import chain

import zope.intid

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.traversing.api import traverse

from zope.security.interfaces import IPrincipal

from ZODB.interfaces import IBroken
from ZODB.POSException import POSError

from nti.common.maps import CaseInsensitiveDict

from nti.contenttypes.courses import get_course_vendor_info
from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.dataserver.metadata_index import IX_MIMETYPE, IX_CREATOR
from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME

from nti.ntiids.ntiids import get_parts
from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.store import PURCHASABLE_COURSE
from nti.store.store import get_purchasables

from nti.store.interfaces import IPurchaseAttempt
from nti.store.interfaces import IInvitationPurchaseAttempt
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.utils import PURCHASE_ATTEMPT_MIME_TYPES

from .model import CoursePrice

from .interfaces import ICoursePrice

def get_vendor_info(context):
	info = get_course_vendor_info(context, False)
	return info or {}

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

def get_purchasable_redeem_cutoff_date(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/RedeemCutOffDate', default=None)
	return result

def get_purchasable_cutoff_date(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/PurchaseCutOffDate', default=None)
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
	entry = ICourseCatalogEntry(context)
	parts = get_parts(entry.ntiid)
	ntiid = make_ntiid(date=parts.date, provider=parts.provider,
					   nttype=PURCHASABLE_COURSE, specific=parts.specific)
	return ntiid
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

def get_nti_choice_bundles(context):
	vendor_info = get_vendor_info(context)
	result = traverse(vendor_info, 'NTI/Purchasable/ChoiceBundles', default=())
	result = result.split() if isinstance(result, six.string_types) else result
	result = set(result) if result else ()
	return result

def find_catalog_entry(context):
	if isinstance(context, six.string_types):
		result = find_object_with_ntiid(context)
		if result is None:
			try:
				catalog = component.getUtility(ICourseCatalog)
				result = catalog.getCatalogEntry(context)
			except (LookupError, KeyError):
				result = None
	else:
		result = context
	result = ICourseCatalogEntry(result, None)
	return result

def safe_find_catalog_entry(context):
	try:
		result = find_catalog_entry(context)
	except Exception:
		result = None
	return result

def find_allow_vendor_updates_purchases(entry, invitation=False):
	entry = find_catalog_entry(entry)
	if entry is None:
		return ()
	
	mime_types = PURCHASE_ATTEMPT_MIME_TYPES
	catalog = component.getUtility(ICatalog, METADATA_CATALOG_NAME)
	intids_purchases = catalog[IX_MIMETYPE].apply({'any_of': mime_types})
	if not intids_purchases:
		return ()
		
	usernames = []
	enrollments = ICourseEnrollments(ICourseInstance(entry))
	for enrollment in enrollments.iter_enrollments():
		principal = IPrincipal(enrollment.Principal, None)
		if principal is not None and enrollment.Scope == ES_PURCHASED:
			usernames.append(principal.id.lower())	
			
	creator_intids = catalog[IX_CREATOR].apply({'any_of': usernames})
	intids_purchases = catalog.family.IF.intersection(intids_purchases,
													  creator_intids )
		
	provider = get_entry_purchasable_provider(entry)
	ntiid = get_entry_purchasable_ntiid(entry, provider)
			
	result = []
	intids = component.getUtility(zope.intid.IIntIds)	
	for uid in intids_purchases:
		try:
			purchase = intids.queryObject(uid)
			# filter any invalid object
			if 	purchase is None or IBroken.providedBy(purchase) or \
				not IPurchaseAttempt.providedBy(purchase):
				continue
			# invitations may not be required
			if not invitation and IInvitationPurchaseAttempt.providedBy(purchase):
				continue
			# check the purchasable is in the purchase
			if ntiid not in purchase.Items:
				continue
			# check vendor updates
			context = CaseInsensitiveDict(purchase.Context or {})
			if not context.get('AllowVendorUpdates', False):
				continue
			result.append(purchase)
		except (POSError, TypeError):
			continue	
	return result

def find_allow_vendor_updates_users(entry, invitation=False):
	purchases = find_allow_vendor_updates_purchases(entry, invitation)
	result = {getattr(x.creator, 'username', x.creator) for x in purchases}
	return result

def get_purchasable_course_bundles(entry):
	result = []
	ntiid = getattr(entry, 'ntiid', entry)
	for purchasable in get_purchasables(provided=IPurchasableCourseChoiceBundle):
		if purchasable.Public and ntiid in purchasable.Items:
			result.append(purchasable)
	return result

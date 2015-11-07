#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import isodate

from datetime import date
from datetime import datetime
from datetime import timedelta

from numbers import Number

from collections import defaultdict

from zope import component

from zope.proxy import ProxyBase

from nti.contentlibrary.interfaces import IContentUnitHrefMapper

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.legacy_catalog import ICourseCatalogLegacyEntry

from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.store import PURCHASABLE_COURSE_CHOICE_BUNDLE

from nti.store.course import create_course
from nti.store.course import PurchasableCourse
from nti.store.course import PurchasableCourseChoiceBundle

from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IPurchasableVendorInfo
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.purchasable import get_purchasable

from nti.store.store import register_purchasable

from nti.store.utils import to_list
from nti.store.utils import to_frozenset

from .utils import get_course_fee
from .utils import get_course_price
from .utils import is_course_giftable
from .utils import allow_vendor_updates
from .utils import is_course_redeemable
from .utils import get_nti_choice_bundles
from .utils import get_course_purchasable_name
from .utils import get_purchasable_cutoff_date
from .utils import get_course_purchasable_ntiid
from .utils import get_course_purchasable_title
from .utils import get_entry_purchasable_provider
from .utils import is_course_enabled_for_purchase
from .utils import get_entry_ntiid_from_purchasable
from .utils import get_purchasable_redeem_cutoff_date

from .interfaces import get_course_publishable_vendor_info

# Purchasable courses

class PurchasableCourseProxy(ProxyBase):

	AllowVendorUpdates = property(
					lambda s: s.__dict__.get('_v_allow_vendor_updates'),
					lambda s, v: s.__dict__.__setitem__('_v_allow_vendor_updates', v))

	CatalogEntryNTIID = property(
					lambda s: s.__dict__.get('_v_catalog_entry_ntiid'),
					lambda s, v: s.__dict__.__setitem__('_v_catalog_entry_ntiid', v))

	def __new__(cls, base, *args, **kwargs):
		return ProxyBase.__new__(cls, base)

	def __init__(self, base, allow=None, entry=None):
		ProxyBase.__init__(self, base)
		self.AllowVendorUpdates = allow
		self.CatalogEntryNTIID = entry

def create_proxy_course(**kwargs):
	kwargs['factory'] = PurchasableCourse
	result = create_course(**kwargs)
	result = PurchasableCourseProxy(result)
	return result

def create_purchasable_from_course(context):
	course = ICourseInstance(context)
	entry = ICourseCatalogEntry(course)
	giftable = is_course_giftable(course)
	redeemable = is_course_redeemable(course)
	public = is_course_enabled_for_purchase(course)
	provider = get_entry_purchasable_provider(entry)

	# find course price
	fee = get_course_fee(course)
	price = get_course_price(course, provider)
	if price is None:
		return None
	amount = price.Amount
	currency = price.Currency
	fee = float(fee) if fee is not None else fee
	
	ntiid = get_course_purchasable_ntiid(entry, provider)

	preview = False
	icon = thumbnail = None
	if ICourseCatalogLegacyEntry.providedBy(entry):
		preview = entry.Preview
		icon = entry.LegacyPurchasableIcon
		thumbnail = entry.LegacyPurchasableThumbnail
	items = [entry.ntiid]  # course is to be purchased

	if icon is None or thumbnail is None:
		try:
			packages = course.ContentPackageBundle.ContentPackages
		except AttributeError:
			packages = (course.legacy_content_package,)

		if icon is None and packages:
			icon = packages[0].icon
			icon = IContentUnitHrefMapper(icon).href if icon else None
		if thumbnail is None and packages:
			thumbnail = packages[0].thumbnail
			thumbnail = IContentUnitHrefMapper(thumbnail).href if thumbnail else None

	if isinstance(entry.StartDate, datetime):
		start_date = unicode(isodate.datetime_isoformat(entry.StartDate))
	elif isinstance(entry.StartDate, date):
		start_date = unicode(isodate.date_isoformat(entry.StartDate))
	else:
		start_date = unicode(entry.StartDate) if entry.StartDate else None

	purchase_cutoff_date = get_purchasable_cutoff_date(course)
	redeem_cutoff_date = get_purchasable_redeem_cutoff_date(course)
	
	name = get_course_purchasable_name(course) or entry.title
	title = get_course_purchasable_title(course) or entry.title

	vendor_info = get_course_publishable_vendor_info(course)
	result = create_proxy_course(ntiid=ntiid,
								 items=items,
								 name=name,
								 title=title,
								 provider=provider,
								 public=public,
								 fee=fee,
								 amount=amount,
								 currency=currency,
								 giftable=giftable,
								 redeemable=redeemable,
								 vendor_info=vendor_info,
								 description=entry.description,
								 purchase_cutoff_date=purchase_cutoff_date, 
								 redeem_cutoff_date=redeem_cutoff_date,
								 # deprecated/legacy
								 icon=icon,
								 preview=preview,
								 thumbnail=thumbnail,
								 startdate=start_date,
								 signature=entry.InstructorsSignature,
								 department=entry.ProviderDepartmentTitle)

	result.CatalogEntryNTIID = entry.ntiid
	result.AllowVendorUpdates = allow_vendor_updates(entry)
	return result

def adjust_purchasable_course(purchasable, entry=None):
	if entry is None:
		ntiid = getattr(purchasable, 'CatalogEntryNTIID', None)
		ntiid = ntiid or get_entry_ntiid_from_purchasable(purchasable)
		entry = find_object_with_ntiid(ntiid)
	if entry is None:  # course removed
		purchasable.Public = False
	else:
		fee = get_course_fee(entry)
		provider = get_entry_purchasable_provider(entry)
		price = get_course_price(entry, provider)
		if price is None:  # price removed
			purchasable.Public = False
			logger.warn('Could not find price for %s', purchasable.NTIID)
		else:
			purchasable.Public = True

			# Update price properties
			purchasable.Amount = price.Amount
			purchasable.Currency = price.Currency
			purchasable.Giftable = is_course_giftable(entry)
			purchasable.Redeemable = is_course_redeemable(entry)
			purchasable.Fee = float(fee) if fee is not None else fee
			purchasable.Public = is_course_enabled_for_purchase(entry)

			# set vendor info fields
			vendor_info = get_course_publishable_vendor_info(entry)
			purchasable.VendorInfo = IPurchasableVendorInfo(vendor_info, None)
			purchasable.AllowVendorUpdates = allow_vendor_updates(entry)
	return purchasable

def sync_purchasable_course(context):
	entry = ICourseCatalogEntry(context)
	ntiid = get_course_purchasable_ntiid(entry)
	purchasable = get_purchasable(ntiid)
	if purchasable is not None:
		adjust_purchasable_course(purchasable, entry)
	else:
		purchasable = create_purchasable_from_course(context)
		if purchasable is not None:
			register_purchasable(purchasable)
	return purchasable

# purchasable course choice bundles

def get_state(purchasable):
	amount = int(purchasable.Amount * 100.0)  # cents
	result = (amount, purchasable.Currency.upper(),
			  purchasable.Public, purchasable.Giftable,
			  purchasable.Redeemable, purchasable.Fee)
	return result

def items_and_ntiids(purchasables):
	items = set()
	ntiids = set()
	for p in purchasables:
		ntiids.add(p.NTIID)
		items.update(p.Items)
	ntiids = tuple(ntiids)
	items = to_frozenset(items)
	return items, ntiids

def allowed_tyes():
	result = (Number, date, datetime, timedelta, bool) + six.string_types
	return result

def get_common_vendor_info(purchasables):
	result = {}
	types = allowed_tyes()
	data = defaultdict(set)
	for p in purchasables:
		for k, v in p.VendorInfo.items():
			if isinstance(v, types):
				data[k].add(v)

	for k, s in data.items():
		if len(s) == 1:
			result[k] = s.__iter__().next()

	result = IPurchasableVendorInfo(result, None)
	return result

class PurchasableCourseChoiceBundleProxy(ProxyBase):

	AllowVendorUpdates = property(
				lambda s: s.__dict__.get('_v_allow_vendor_updates'),
				lambda s, v: s.__dict__.__setitem__('_v_allow_vendor_updates', v))

	Bundle = property(
				lambda s: s.__dict__.get('_v_bundle'),
				lambda s, v: s.__dict__.__setitem__('_v_bundle', v))

	Purchasables = property(
				lambda s: s.__dict__.get('_v_purchasables'),
				lambda s, v: s.__dict__.__setitem__('_v_purchasables', v))

	def __init__(self, base, allow=None, bundle=None, purchasables=()):
		ProxyBase.__init__(self, base)
		self.Bundle = bundle
		self.AllowVendorUpdates = allow
		self.Purchasables = purchasables

def get_course_choice_bundle_ntiid(name, purchasables):
	purchasables = to_list(purchasables)
	reference_purchasable = purchasables[0]
	specific = make_specific_safe(name)
	ntiid = make_ntiid(provider=reference_purchasable.Provider,
					   nttype=PURCHASABLE_COURSE_CHOICE_BUNDLE,
					   specific=specific)
	return ntiid

def create_course_choice_bundle(name, purchasables):
	purchasables = to_list(purchasables)
	reference_purchasable = purchasables[0]
	ntiid = get_course_choice_bundle_ntiid(name, purchasables)

	# gather items and ntiids
	items, ntiids = items_and_ntiids(purchasables)
	result = create_course(ntiid=ntiid,
						   items=items,
						   name=name,
						   title=name,
						   description=name,
						   fee=reference_purchasable.Fee,
						   public=reference_purchasable.Public,
						   amount=reference_purchasable.Amount,
						   currency=reference_purchasable.Currency,
						   provider=reference_purchasable.Provider,
						   giftable=reference_purchasable.Giftable,
						   redeemable=reference_purchasable.Redeemable,
						   vendor_info=get_common_vendor_info(purchasables),
						   factory=PurchasableCourseChoiceBundle)

	result = PurchasableCourseChoiceBundleProxy(result)
	result.Bundle = name
	result.Purchasables = ntiids
	return result

def process_choice_bundle(name, purchasables, notify=True):
	state = None
	validated = []

	for purchasable in purchasables or ():
		p_state = get_state(purchasable)
		if state is None:
			state = p_state
			validated.append(purchasable)
		elif state == p_state:
			validated.append(purchasable)
		elif notify:
			logger.warn("Purchasable %s(%s) will not be included in bundle %s",
						purchasable.NTIID, p_state, name)

	# there is something to process
	if validated:
		result = create_course_choice_bundle(name, validated)
	elif notify:
		result = None
		logger.warn("Bundle %s will not be created. Not enough purchasables", name)
	return result

def get_choice_bundle_map(registry=component):
	choice_bundle_map = defaultdict(list)
	catalog = registry.getUtility(ICourseCatalog)
	for entry in catalog.iterCatalogEntries():
		purchasable = IPurchasableCourse(entry, None)
		if purchasable is not None:
			for name in get_nti_choice_bundles(entry):
				choice_bundle_map[name].append(purchasable)
	return choice_bundle_map

def get_site_choice_bundles(registry=component):
	site_manager = registry.getSiteManager()
	if site_manager == component.getGlobalSiteManager():
		result = ()
	else:
		result = []
		for _, obj in list(registry.getUtilitiesFor(IPurchasableCourseChoiceBundle)):
			if obj.__parent__ == site_manager:
				result.append(obj)
	return result

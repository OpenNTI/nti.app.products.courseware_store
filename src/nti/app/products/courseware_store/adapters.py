#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import isodate
from datetime import date
from datetime import datetime

from zope import component
from zope import interface

from dolmen.builtins.interfaces import IString

from nti.contentlibrary.interfaces import IContentUnitHrefMapper

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.legacy_catalog import ICourseCatalogLegacyEntry

from nti.ntiids.ntiids import get_parts
from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.store.course import create_course
from nti.store.interfaces import IPurchasableCourse

from nti.utils.property import CachedProperty

from .interfaces import ICoursePrice
from .interfaces import get_course_publishable_vendor_info

from .utils import get_course_price
from .utils import is_course_giftable
from .utils import is_course_redeemable
from .utils import get_nti_course_price
from .utils import allow_vendor_updates
from .utils import get_course_purchasable_name
from .utils import get_course_purchasable_ntiid
from .utils import get_course_purchasable_title
from .utils import is_course_enabled_for_purchase
from .utils import get_entry_purchasable_provider

@interface.implementer(ICoursePrice)
def _nti_course_price_finder(context):
	result = get_nti_course_price(context)
	return result
	
@component.adapter(ICourseCatalogEntry)
@interface.implementer(IPurchasableCourse)
def _entry_to_purchasable(entry):
	course_instance = ICourseInstance(entry, None)
	result = IPurchasableCourse(course_instance, None)
	return result
	
@component.adapter(ICourseCatalogEntry)
@interface.implementer(IString)
def _entry_to_purchasable_ntiid(entry):
	parts = get_parts(entry.ntiid)
	specific = make_specific_safe(entry.ProviderUniqueID)
	ntiid = make_ntiid(date=parts.date, provider=parts.provider,
					   nttype="purchasable_course", specific=specific)
	return ntiid

@component.adapter(ICourseInstance)
@interface.implementer(IString)
def _course_to_purchasable_ntiid(course):
	entry = ICourseCatalogEntry(course, None)
	result = _entry_to_purchasable_ntiid(entry) if entry else None
	return result
		
@component.adapter(ICourseInstance)
@interface.implementer(IPurchasableCourse)
def _course_to_purchasable(course):
	entry = ICourseCatalogEntry(course)
	giftable = is_course_giftable(course)
	redeemable = is_course_redeemable(course)
	public = is_course_enabled_for_purchase(course)
	provider = get_entry_purchasable_provider(entry)
	
	price = get_course_price(course, provider)	
	if price is None:
		return None
	amount = price.Amount
	currency = price.Currency
	
	ntiid = get_course_purchasable_ntiid(entry, provider)
	assert ntiid, 'No purchasable NTIID was derived for course'
	
	preview = False
	icon = thumbnail = None
	if ICourseCatalogLegacyEntry.providedBy(entry):
		preview = entry.Preview
		icon = entry.LegacyPurchasableIcon
		thumbnail = entry.LegacyPurchasableThumbnail
	items = [entry.ntiid] # course is to be purchased
	
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

	name = get_course_purchasable_name(course) or entry.title
	title = get_course_purchasable_title(course) or entry.title
	
	vendor_info = get_course_publishable_vendor_info(course)
	result = create_course(ntiid=ntiid,
						   items=items,
						   name=name, 
						   title=title,
						   provider=provider, 
						   public=public,
						   amount=amount,
						   currency=currency,
						   giftable=giftable,
						   redeemable=redeemable,
						   vendor_info=vendor_info,
						   description=entry.description,
						   # deprecated/legacy
						   icon=icon,
						   preview=preview,
						   thumbnail=thumbnail,
						   startdate=start_date,
						   signature=entry.InstructorsSignature,
						   department=entry.ProviderDepartmentTitle,
						   factory=PurchasableProxy)
	
	result.CatalogEntryNTIID = entry.ntiid
	return result

from zope.traversing.interfaces import IEtcNamespace

from nti.store.course import PurchasableCourse

def _setter(name):
	def func(self, value):
		self.__dict__[name] = value
	return func

def _getter(name):
	def func(self):
		self._sync
		return self.__dict__.get(name, None)
	return func

def _alias(prop_name):
	prop_name = str(prop_name) # native string
	return property( _getter(prop_name), _setter(prop_name))
	
class PurchasableProxy(PurchasableCourse):
	
	__external_class_name__ = 'PurchasableCourse'
	
	CatalogEntryNTIID = None
	AllowVendorUpdates = False

	@property
	def lastSynchronized(self):
		hostsites = component.queryUtility(IEtcNamespace, name='hostsites')
		result = getattr(hostsites, 'lastSynchronized', 0)
		return result
		
	Amount = _alias('Amount')
	Currency = _alias('Currency')
	
	Public = _alias('Public')
	Giftable = _alias('Giftable')
	Redeemable = _alias('Redeemable')
	
	@CachedProperty('lastSynchronized')
	def _sync(self):
		if not self.CatalogEntryNTIID:
			return
		try:
			entry = find_object_with_ntiid(self.CatalogEntryNTIID)
			if entry is None:
				self.Public = False
			else:
				# reset flags
				self.Giftable = is_course_giftable(entry)
				self.Redeemable = is_course_redeemable(entry)
				self.Public = is_course_enabled_for_purchase(entry)
				self.AllowVendorUpdates = allow_vendor_updates(entry)
				# reset price
				provider = get_entry_purchasable_provider(entry)
				price = get_course_price(entry, provider)
				self.Amount = price.Amount
				self.Currency = price.Currency
		except (StandardError, Exception):
			## running outside a transaction?
			self.Public = False

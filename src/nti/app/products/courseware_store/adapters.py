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

from nti.contentlibrary.interfaces import IContentUnitHrefMapper

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.legacy_catalog import ICourseCatalogLegacyEntry

from nti.store.interfaces import IPurchasableCourse

from .interfaces import ICoursePrice
from .interfaces import get_course_publishable_vendor_info

from .purchasable import create_proxy_course

from .utils import get_course_price
from .utils import find_catalog_entry
from .utils import is_course_giftable
from .utils import is_course_redeemable
from .utils import get_nti_course_price
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

@component.adapter(ICourseInstance)
@interface.implementer(IPurchasableCourse)
def _course_to_purchasable(course):
	entry = ICourseCatalogEntry(course)
	giftable = is_course_giftable(course)
	redeemable = is_course_redeemable(course)
	public = is_course_enabled_for_purchase(course)
	provider = get_entry_purchasable_provider(entry)
	
	# find course price
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
	result = create_proxy_course(ntiid=ntiid,
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
								 department=entry.ProviderDepartmentTitle)
	
	result.CatalogEntryNTIID = entry.ntiid
	return result

@component.adapter(IPurchasableCourse)
@interface.implementer(ICourseCatalogEntry)
def _purchasable_to_catalog_entry(purchasable):
	ntiid = getattr(purchasable, 'CatalogEntryNTIID', None) or u''
	result = find_catalog_entry(ntiid) if ntiid else None
	return result

@component.adapter(IPurchasableCourse)
@interface.implementer(ICourseInstance)
def _purchasable_to_course_instance(purchasable):
	entry = ICourseCatalogEntry(purchasable, None)
	result = ICourseInstance(entry, None)
	return result

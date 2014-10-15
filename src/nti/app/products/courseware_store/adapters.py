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

from nti.store.course import create_course
from nti.store.interfaces import IPurchasableCourse

from ..interfaces import get_course_publishable_vendor_info

from .utils import get_course_price
from .utils import is_course_giftable
from .utils import is_course_enabled_for_purchase
from .utils import get_course_purchasable_provider
	
from zope import component
from zope import interface
from zope.traversing.api import traverse

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.utils.maps import CaseInsensitiveDict

from .model import CoursePrice

from .interfaces import ICoursePrice

TIMEOUT = 30

def get_vendor_info(course):
	return ICourseInstanceVendorInfo(course, {})

@interface.implementer(ICoursePrice)
@component.adapter(ICourseInstance)
def _nti_course_price_finder(course):
	vendor_info = get_vendor_info(course)
	amount = traverse(vendor_info, 'NTI/Purchasable/Price', default=None)
	currency = traverse(vendor_info, 'NTI/Purchasable/Currency', default='USD')
	if amount:
		result = CoursePrice(Amount=float(amount), Currency=currency)
		return result
	return None

@interface.implementer(ICoursePrice)
@component.adapter(ICourseCatalogEntry)
def _nti_catalog_entry_price_finder(entry):
	return _nti_course_price_finder(ICourseInstance(entry))

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
	public = is_course_enabled_for_purchase(course)
	price = get_course_price(course)
	if price is None:
		return
	
	giftable = is_course_giftable(course)
	entry = ICourseCatalogEntry(course)
	amount = price.Amount
	currency = price.Currency
	
	ntiid = component.queryAdapter(entry, IString, name="purchasable_course_ntiid")
	if ntiid is None:
		ntiid = _entry_to_purchasable_ntiid(entry)
	
	parts = get_parts(entry.ntiid)
	provider = get_course_purchasable_provider(course) or parts.provider
	
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

	vendor_info = get_course_publishable_vendor_info(course)
	result = create_course(ntiid=ntiid,
						   items=items,
						   name=entry.title, 
						   title=entry.title,
						   provider=provider, 
						   public=public,
						   amount=amount,
						   currency=currency,
						   giftable=giftable,
						   vendor_info=vendor_info,
						   description=entry.description,
						   # deprecated/legacy
						   icon=icon,
						   preview=preview,
						   thumbnail=thumbnail,
						   startdate=start_date,
						   signature=entry.InstructorsSignature,
						   department=entry.ProviderDepartmentTitle)
	
	return result
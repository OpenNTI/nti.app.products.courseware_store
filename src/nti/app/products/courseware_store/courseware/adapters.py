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
from zope.traversing.api import traverse

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.utils.maps import CaseInsensitiveDict

from ..fiveminuteaep import get_course_details
from ..fiveminuteaep import get_fmaep_crn_and_term

from .model import CoursePrice

from .interfaces import ICoursePrice

TIMEOUT = 30

def get_vendor_info(course):
	return ICourseInstanceVendorInfo(course, {})

@interface.implementer(ICoursePrice)
@component.adapter(ICourseInstance)
def _fmaep_course_price_finder(course):
	data = get_fmaep_crn_and_term(course)
	if not data:
		return None

	crn, term = data
	try:
		details = get_course_details(crn, term, timeout=TIMEOUT)
	except Exception as e:
		details = None
		logger.error("Cannot get course details for %s,%s. %s", crn, term, e)
	
	details = CaseInsensitiveDict(details) if details else {}
	currency = details.get('Currency') or 'USD'
	amount = details.get('Price') or details.get('Amount')
	if amount:
		result = CoursePrice(Amount=float(amount), Currency=currency)
		return result
	return None
	
@interface.implementer(ICoursePrice)
@component.adapter(ICourseCatalogEntry)
def _fmaep_catalog_entry_price_finder(entry):
	return _fmaep_course_price_finder(ICourseInstance(entry))

@interface.implementer(ICoursePrice)
@component.adapter(ICourseInstance)
def _ou_course_price_finder(course):
	vendor_info = get_vendor_info(course)
	amount = traverse(vendor_info, 'OU/Price', default=None)
	currency = traverse(vendor_info, 'OU/Currency', default='USD')
	if amount:
		result = CoursePrice(Amount=float(amount), Currency=currency)
		return result
	return None

@interface.implementer(ICoursePrice)
@component.adapter(ICourseCatalogEntry)
def _ou_catalog_entry_price_finder(entry):
	return _ou_course_price_finder(ICourseInstance(entry))

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

@interface.implementer(ICoursePrice)
@component.adapter(ICourseInstance)
def _course_price_finder(course):
	result = None
	if not result:
		result = _ou_course_price_finder(course)
	if not result:
		result = _nti_course_price_finder(course)
	return result
	
@interface.implementer(ICoursePrice)
@component.adapter(ICourseCatalogEntry)
def _catalog_entry_price_finder(entry):
	return _course_price_finder(ICourseInstance(entry))

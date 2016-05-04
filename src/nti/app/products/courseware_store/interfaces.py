#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid.interfaces import IRequest

from nti.app.products.courseware.interfaces import IEnrollmentOption
from nti.app.products.courseware.interfaces import ICoursePublishableVendorInfo
from nti.app.products.courseware.interfaces import get_course_publishable_vendor_info

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.store.interfaces import IPurchasableCourse

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine

# Re-Export
ICoursePublishableVendorInfo = ICoursePublishableVendorInfo
get_course_publishable_vendor_info = get_course_publishable_vendor_info

class ICoursePrice(interface.Interface):
	Amount = Number(title="The price amount", required=True)
	Currency = ValidTextLine(title="The currency", required=False, default='USD')

class ICoursePriceFinder(interface.Interface):
	"""
	marker interface for a course price finder
	"""

class IStoreEnrollmentOption(IEnrollmentOption):
	IsEnabled = Bool(title="Is enabled flag", required=False, default=True)

	Purchasables = ListOrTuple(Object(IPurchasableCourse),
							   title="Purchasable course",
							   required=True,
							   min_length=1)
	AllowVendorUpdates = Bool(title="Allow vendor updates",
							  required=False,
							  default=False)

class IStoreEnrollmentEvent(interface.Interface):
	request = Object(IRequest, title="the request", required=False)

	purchasable = Object(IPurchasableCourse, title="purchasable course",
						 required=False)

	record = Object(ICourseInstanceEnrollmentRecord, title="enrollemnt record",
					required=True)

@interface.implementer(IStoreEnrollmentEvent)
class StoreEnrollmentEvent(object):

	def __init__(self, record, purchasable=None, request=None):
		self.record = record
		self.request = request
		self.purchasable = purchasable

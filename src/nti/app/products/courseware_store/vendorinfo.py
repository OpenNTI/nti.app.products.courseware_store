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

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from .interfaces import ICoursePublishableVendorInfo

from .utils import allow_vendor_updates

@component.adapter(ICourseInstance)
@interface.implementer(ICoursePublishableVendorInfo)
class _DefaultCoursePublishableVendorInfo(object):

	def __init__(self, course):
		self.course = course

	def info(self):
		return None

@component.adapter(ICourseInstance)
@interface.implementer(ICoursePublishableVendorInfo)
class _CourseCatalogPublishableVendorInfo(object):
	"""
	A bit of a hack to expose course catalog information to unauthenticated users
	on the landing page.
	"""

	def __init__(self, course):
		self.course = course

	def info(self):
		catalog_entry = ICourseCatalogEntry( self.course, None )
		if not catalog_entry:
			return None

		does_allow_vendor_updates = allow_vendor_updates( self.course )

		result = {'StartDate': catalog_entry.StartDate,
				  'EndDate': catalog_entry.EndDate,
				  'Duration': catalog_entry.Duration,
				  'AllowVendorUpdates' : does_allow_vendor_updates }

		credit_info = getattr( catalog_entry, 'Credit', None )
		if credit_info:
			# Just grabbing the first entry
			credit_info = credit_info[0]
			hours = credit_info.Hours
			result.update( { 'Hours': hours } )
		return result

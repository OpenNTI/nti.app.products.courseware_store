#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.app.products.courseware.interfaces import ICoursePublishableVendorInfo

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from .utils import allow_vendor_updates

@interface.implementer(ICoursePublishableVendorInfo)
class _CourseCatalogPublishableVendorInfo(object):

	def __init__(self, context):
		self.context = context

	def info(self):
		catalog_entry = ICourseCatalogEntry(self.context, None)
		if not catalog_entry:
			return None

		does_allow_vendor_updates = allow_vendor_updates(self.context)

		result = {
			'Title': catalog_entry.title,
			'StartDate': catalog_entry.StartDate,
			'EndDate': catalog_entry.EndDate,
			'Duration': catalog_entry.Duration,
			'AllowVendorUpdates': does_allow_vendor_updates
		}

		credit_info = getattr(catalog_entry, 'Credit', None)
		if credit_info:
			# Just get the first entry
			credit_info = credit_info[0]
			hours = credit_info.Hours
			result.update({ 'Hours': hours })
		return result

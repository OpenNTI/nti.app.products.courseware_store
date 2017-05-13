#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.app.products.courseware.interfaces import ICoursePublishableVendorInfo

from nti.app.products.courseware_store.utils import allow_vendor_updates

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry


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
            'EndDate': catalog_entry.EndDate,
            'Duration': catalog_entry.Duration,
            'StartDate': catalog_entry.StartDate,
            'AllowVendorUpdates': does_allow_vendor_updates
        }
        credit_info = getattr(catalog_entry, 'Credit', None)
        if credit_info:
            credit_info = credit_info[0] # get the first entry
            result.update({'Hours': credit_info.Hours})
        return result

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

from .utils import allow_vendor_updates

from .interfaces import ICoursePublishableVendorInfo

@component.adapter(ICourseInstance)
@interface.implementer(ICoursePublishableVendorInfo)
class _DefaultCoursePublishableVendorInfo(object):

    def __init__(self, course):
        self.course = course

    def info(self):
        result = {'AllowVendorUpdates': allow_vendor_updates(self.course)}
        return result

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
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from ..courseware.interfaces import ICoursePublishableVendorInfo

@component.adapter(ICourseInstance)
@interface.implementer(ICoursePublishableVendorInfo)
class _OUCoursePublishableVendorInfo(object):

    def __init__(self, course):
        self.course = course

    def info(self):
        vendor_info = ICourseInstanceVendorInfo(self.course, {})
        sourcedid = traverse(vendor_info, 'OU/IMS/sourcedid', default=None)
        return {'OU_IMS':sourcedid} if sourcedid else None
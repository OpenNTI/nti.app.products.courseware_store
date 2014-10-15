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

from ..courseware.interfaces import ICoursePublishableVendorInfo

from .utils import get_fmaep_crn_and_term

@component.adapter(ICourseInstance)
@interface.implementer(ICoursePublishableVendorInfo)
class _FMAEPCoursePublishableVendorInfo(object):

    def __init__(self, course):
        self.course = course

    def info(self):
        result = None
        record = get_fmaep_crn_and_term(self.course)
        if record:
            result = {'NTI_CRN':record[0], 'NTI_Term':record[1]}
        return result
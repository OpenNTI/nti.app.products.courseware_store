#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import isodate
from datetime import datetime

from zope import interface
from zope.traversing.api import traverse

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.externalization.interfaces import IExternalMappingDecorator

@interface.implementer(IExternalMappingDecorator)
class BaseOUCourseEntryDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, result):
        return self._is_authenticated
    
    def linked_allowed(self, start=None, cutoff=None, utcnow=None):
        utcnow = utcnow or datetime.utcnow()
        start = utcnow if start is None else start
        cutoff = utcnow if cutoff is None else cutoff
        result = utcnow.replace(tzinfo=None) >= start.replace(tzinfo=None) and \
                 utcnow.replace(tzinfo=None) <= cutoff.replace(tzinfo=None)
        return result
    
    def get_and_set_date(self, vendor_info, in_key, out_key, result, default=None):
        value = traverse(vendor_info, in_key, default=default)
        if value:
            result[out_key] = value
            try:
                return isodate.parse_datetime(value)
            except StandardError:
                pass
        return None

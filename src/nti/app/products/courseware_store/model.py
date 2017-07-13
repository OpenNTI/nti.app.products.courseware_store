#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.app.products.courseware_store.interfaces import ICoursePrice

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.store.model import Price


@interface.implementer(ICoursePrice)
class CoursePrice(Price):
    createDirectFieldProperties(ICoursePrice)

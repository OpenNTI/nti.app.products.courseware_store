#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import interface

from nti.common.property import alias
from nti.common.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ICoursePrice

@WithRepr
@total_ordering
@EqHash('Amount', 'Currency')
@interface.implementer(ICoursePrice)
class CoursePrice(SchemaConfigured):
    createDirectFieldProperties(ICoursePrice)

    amount = alias('Amount')
    currency = alias('Currency')
    
    def __lt__(self, other):
        try:
            return (self.Amount, self.Currency) < (self.Amount, self.Currency)
        except AttributeError:  # pragma: no cover
            return NotImplemented
    
    def __gt__(self, other):
        try:
            return (self.Amount, self.Currency) > (self.Amount, self.Currency)
        except AttributeError:  # pragma: no cover
            return NotImplemented

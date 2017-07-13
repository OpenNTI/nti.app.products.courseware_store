#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.cachedescriptors.property import readproperty

from nti.app.products.courseware_store.interfaces import ICoursePrice
from nti.app.products.courseware_store.interfaces import IPurchasableCourse2
from nti.app.products.courseware_store.interfaces import IPurchasableCourseChoiceBundle

from nti.externalization.representation import WithRepr

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import AdaptingFieldProperty
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.store.purchasable import Purchasable

from nti.store.model import Price


@interface.implementer(ICoursePrice)
class CoursePrice(Price):
    createDirectFieldProperties(ICoursePrice)


@WithRepr
@EqHash('NTIID',)
@interface.implementer(IPurchasableCourse2)
class PurchasableCourse(Purchasable):
    createDirectFieldProperties(IPurchasableCourse2)

    Description = AdaptingFieldProperty(IPurchasableCourse2['Description'])

    @readproperty
    def Label(self):
        return self.Name


@interface.implementer(IPurchasableCourseChoiceBundle)
class PurchasableCourseChoiceBundle(PurchasableCourse):
    __external_class_name__ = 'PurchasableCourseChoiceBundle'
    IsPurchasable = False

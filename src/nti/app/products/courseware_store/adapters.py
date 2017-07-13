#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.products.courseware_store.interfaces import ICoursePrice
from nti.app.products.courseware_store.interfaces import IPurchasableCourse

from nti.app.products.courseware_store.utils import find_catalog_entry
from nti.app.products.courseware_store.utils import get_nti_course_price
from nti.app.products.courseware_store.utils import get_course_purchasable_ntiid
from nti.app.products.courseware_store.utils import get_entry_ntiid_from_purchasable

from nti.contenttypes.courses.utils import get_any_enrollment

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.store.interfaces import IPurchaseAttempt
from nti.store.interfaces import IObjectTransformer
from nti.store.interfaces import IPurchasableChoiceBundle

from nti.store.store import get_purchasable
from nti.store.store import get_purchase_purchasables


@interface.implementer(ICoursePrice)
def _nti_course_price_finder(context):
    return get_nti_course_price(context)


@component.adapter(ICourseCatalogEntry)
@interface.implementer(IPurchasableCourse)
def _entry_to_purchasable(entry):
    ntiid = get_course_purchasable_ntiid(entry)
    return get_purchasable(ntiid) if ntiid else None


@component.adapter(ICourseInstance)
@interface.implementer(IPurchasableCourse)
def _course_to_purchasable(course):
    entry = ICourseCatalogEntry(course, None)
    return IPurchasableCourse(entry, None)


@component.adapter(IPurchasableCourse)
@interface.implementer(ICourseCatalogEntry)
def _purchasable_to_catalog_entry(purchasable):
    try:
        ntiid = purchasable.CatalogEntryNTIID
    except AttributeError:
        ntiid = get_entry_ntiid_from_purchasable(purchasable)
    return find_catalog_entry(ntiid) if ntiid else None


@component.adapter(IPurchasableCourse)
@interface.implementer(ICourseInstance)
def _purchasable_to_course_instance(purchasable):
    entry = ICourseCatalogEntry(purchasable, None)
    return ICourseInstance(entry, None)


def _purchase_attempt_transformer(purchase, user=None):
    result = purchase
    purchasables = get_purchase_purchasables(purchase)
    if (    len(purchasables) == 1
        and IPurchasableCourse.providedBy(purchasables[0])
        and not IPurchasableChoiceBundle.providedBy(purchasables[0])):
        course = ICourseInstance(purchasables[0], None)
        if user is not None and course is not None:
            record = get_any_enrollment(course, user)
            result = record if record is not None else purchase
    return result


@component.adapter(IPurchaseAttempt)
@interface.implementer(IObjectTransformer)
def _purchase_object_transformer(obj):
    return _purchase_attempt_transformer

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.products.courseware_store.interfaces import IPurchasableCourse
from nti.app.products.courseware_store.interfaces import IStoreEnrollmentOption
from nti.app.products.courseware_store.interfaces import IPurchasableCourseChoiceBundle

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.store.externalization import PurchasableSummaryExternalizer

CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE

logger = __import__('logging').getLogger(__name__)


@component.adapter(IPurchasableCourse)
class _PurchasableCourseSummaryExternalizer(PurchasableSummaryExternalizer):

    fields_to_remove = PurchasableSummaryExternalizer.fields_to_remove + \
                        ('Featured', 'Preview', 'StartDate', 'Department',
                         'Signature', 'Communities', 'Duration', 'EndDate')

    interface = IPurchasableCourse


@component.adapter(IPurchasableCourseChoiceBundle)
@interface.implementer(IInternalObjectExternalizer)
class _PurchasableCourseChoiceBundleSummaryExternalizer(PurchasableSummaryExternalizer):
    interface = IPurchasableCourseChoiceBundle
    

@component.adapter(IStoreEnrollmentOption)
@interface.implementer(IInternalObjectExternalizer)
class _StoreEnrollmentOptionExternalizer(object):

    def __init__(self, obj):
        self.obj = obj

    def toExternalObject(self, *unused_args, **unused_kwargs):
        result = LocatedExternalDict()
        result[MIMETYPE] = self.obj.mimeType
        result[CLASS] =  getattr(self.obj, '__external_class_name__', None) \
                      or self.obj.__class__.__name__
        result['RequiresAdmission'] = False
        result['IsEnabled'] = self.obj.IsEnabled
        result['AllowVendorUpdates'] = self.obj.AllowVendorUpdates
        # purchasables
        items = []
        defaultGifting = None
        defaultPurchase = None
        length = len(self.obj.Purchasables)
        result['Purchasables'] = {ITEMS: items}
        for idx in range(length):
            purchasable = self.obj.Purchasables[idx]
            if not defaultPurchase:
                defaultPurchase = purchasable.NTIID
            ext_obj = to_external_object(purchasable, name='summary')
            items.append(ext_obj)
            purchasable = self.obj.Purchasables[length - idx - 1]
            if not defaultGifting:
                defaultGifting = purchasable.NTIID
        result['Purchasables']['DefaultGiftingNTIID'] = defaultGifting
        result['Purchasables']['DefaultPurchaseNTIID'] = defaultPurchase
        return result

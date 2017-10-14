#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import datetime
from collections import Mapping

from zope import interface

from zope.cachedescriptors.property import readproperty

from nti.app.products.courseware_store.interfaces import ICoursePrice
from nti.app.products.courseware_store.interfaces import IPurchasableCourse
from nti.app.products.courseware_store.interfaces import IPurchasableCourseChoiceBundle

from nti.externalization.representation import WithRepr

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import AdaptingFieldProperty
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.store.purchasable import Purchasable
from nti.store.purchasable import DefaultPurchasableVendorInfo

from nti.store.model import Price

from nti.store.utils import to_frozenset

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICoursePrice)
class CoursePrice(Price):
    createDirectFieldProperties(ICoursePrice)


@WithRepr
@EqHash('NTIID',)
@interface.implementer(IPurchasableCourse)
class PurchasableCourse(Purchasable):
    createDirectFieldProperties(IPurchasableCourse)

    Description = AdaptingFieldProperty(IPurchasableCourse['Description'])

    @readproperty
    def Label(self):
        return self.Name


@interface.implementer(IPurchasableCourseChoiceBundle)
class PurchasableCourseChoiceBundle(PurchasableCourse):
    __external_class_name__ = 'PurchasableCourseChoiceBundle'
    IsPurchasable = False


def create_course(ntiid, name=None, provider=None, amount=None, currency=u'USD',
                  items=(), fee=None, title=None, license_=None, author=None,
                  description=None, icon=None, thumbnail=None, discountable=False,
                  bulk_purchase=False, public=True, giftable=False, redeemable=False,
                  vendor_info=None, factory=PurchasableCourse,
                  purchase_cutoff_date=None, redeem_cutoff_date=None,
                  # deprecated / legacy
                  communities=None, featured=False, preview=False,
                  department=None, signature=None, startdate=None):

    if amount is not None and not provider:
        raise AssertionError("Must specify a provider")

    if amount is not None and not currency:
        raise AssertionError("Must specify a currency")

    fee = float(fee) if fee is not None else None
    amount = float(amount) if amount is not None else amount
    items = to_frozenset(items) if items else frozenset((ntiid,))
    communities = to_frozenset(communities) if communities else None

    def _parse_time(field):
        result = field
        if isinstance(field, (datetime.datetime, datetime.date)):
            result = field.isoformat()
        return result
    startdate = _parse_time(startdate)

    if vendor_info and isinstance(vendor_info, Mapping):
        vendor = DefaultPurchasableVendorInfo(vendor_info)
    else:
        vendor = None

    result = factory()

    # basic info
    result.Name = name
    result.NTIID = ntiid
    result.Title = title
    result.Items = items
    result.Author = author
    result.Provider = provider
    result.Description = description

    # cost
    result.Fee = fee
    result.Amount = amount
    result.Currency = currency

    # flags
    result.Public = public
    result.Giftable = giftable
    result.Redeemable = redeemable
    result.Discountable = discountable
    result.BulkPurchase = bulk_purchase

    # extras
    result.Icon = icon
    result.VendorInfo = vendor
    result.Thumbnail = thumbnail
    result.RedeemCutOffDate = redeem_cutoff_date
    result.PurchaseCutOffDate = purchase_cutoff_date

    # deprecated / legacy
    result.Preview = preview
    result.License = license_
    result.Featured = featured
    result.StartDate = startdate
    result.Signature = signature
    result.Department = department
    result.Communities = communities
    return result

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from datetime import date
from datetime import datetime
from datetime import timedelta
from collections import defaultdict

from numbers import Number

import isodate

from zope import component
from zope import lifecycleevent

from zope.cachedescriptors.property import readproperty

from nti.app.products.courseware_store.interfaces import get_course_publishable_vendor_info

from nti.app.products.courseware_store.utils import get_course_fee
from nti.app.products.courseware_store.utils import get_course_price
from nti.app.products.courseware_store.utils import is_course_giftable
from nti.app.products.courseware_store.utils import allow_vendor_updates
from nti.app.products.courseware_store.utils import is_course_redeemable
from nti.app.products.courseware_store.utils import get_nti_choice_bundles
from nti.app.products.courseware_store.utils import get_course_purchasable_name
from nti.app.products.courseware_store.utils import get_purchasable_cutoff_date
from nti.app.products.courseware_store.utils import get_course_purchasable_ntiid
from nti.app.products.courseware_store.utils import get_course_purchasable_title
from nti.app.products.courseware_store.utils import get_entry_purchasable_provider
from nti.app.products.courseware_store.utils import is_course_enabled_for_purchase
from nti.app.products.courseware_store.utils import get_purchasable_redeem_cutoff_date

from nti.contentlibrary.interfaces import IContentUnitHrefMapper

from nti.contenttypes.courses.common import get_course_packages

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.legacy_catalog import ICourseCatalogLegacyEntry

from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe

from nti.store import PURCHASABLE_COURSE_CHOICE_BUNDLE

from nti.store.course import create_course
from nti.store.course import PurchasableCourse as StorePurchasableCourse
from nti.store.course import PurchasableCourseChoiceBundle as StorePurchasableCourseChoiceBundle

from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IPurchasableVendorInfo
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.store import register_purchasable

from nti.store.utils import to_list
from nti.store.utils import to_frozenset

# Purchasable courses


class PurchasableCourse(StorePurchasableCourse):
    CatalogEntryNTIID = None
    AllowVendorUpdates = None


def create_purchasable_from_course(context):
    course = ICourseInstance(context)
    entry = ICourseCatalogEntry(course)
    giftable = is_course_giftable(course)
    redeemable = is_course_redeemable(course)
    public = is_course_enabled_for_purchase(course)
    provider = get_entry_purchasable_provider(entry)

    # find course price
    fee = get_course_fee(course)
    price = get_course_price(course, provider)
    if price is None:
        return None
    amount = price.Amount
    currency = price.Currency
    fee = float(fee) if fee is not None else fee

    ntiid = get_course_purchasable_ntiid(entry, provider)

    preview = False
    icon = thumbnail = None
    if ICourseCatalogLegacyEntry.providedBy(entry):
        preview = entry.Preview
        icon = entry.LegacyPurchasableIcon
        thumbnail = entry.LegacyPurchasableThumbnail
    items = [entry.ntiid]  # course is to be purchased

    if icon is None or thumbnail is None:
        packages = get_course_packages(course)
        if icon is None and packages:
            icon = packages[0].icon
            icon = IContentUnitHrefMapper(icon).href if icon else None
        if thumbnail is None and packages:
            thumbnail = packages[0].thumbnail
            thumbnail = IContentUnitHrefMapper(thumbnail).href if thumbnail else None

    if isinstance(entry.StartDate, datetime):
        start_date = unicode(isodate.datetime_isoformat(entry.StartDate))
    elif isinstance(entry.StartDate, date):
        start_date = unicode(isodate.date_isoformat(entry.StartDate))
    else:
        start_date = unicode(entry.StartDate) if entry.StartDate else None

    purchase_cutoff_date = get_purchasable_cutoff_date(course)
    redeem_cutoff_date = get_purchasable_redeem_cutoff_date(course)

    if      purchase_cutoff_date \
        and redeem_cutoff_date \
        and purchase_cutoff_date > redeem_cutoff_date:
        raise ValueError(
            'RedeemCutOffDate cannot be before PurchaseCutOffDate')

    name = get_course_purchasable_name(course) or entry.title
    title = get_course_purchasable_title(course) or entry.title

    vendor_info = get_course_publishable_vendor_info(course)
    result = create_course(ntiid=ntiid,
                           items=items,
                           name=name,
                           title=title,
                           provider=provider,
                           public=public,
                           fee=fee,
                           amount=amount,
                           currency=currency,
                           giftable=giftable,
                           redeemable=redeemable,
                           vendor_info=vendor_info,
                           description=entry.description,
                           purchase_cutoff_date=purchase_cutoff_date,
                           redeem_cutoff_date=redeem_cutoff_date,
                           # deprecated/legacy
                           icon=icon,
                           preview=preview,
                           thumbnail=thumbnail,
                           startdate=start_date,
                           signature=entry.InstructorsSignature,
                           department=entry.ProviderDepartmentTitle,
                           # initializer
                           factory=PurchasableCourse)
    # save non-public properties
    result.CatalogEntryNTIID = entry.ntiid
    result.AllowVendorUpdates = allow_vendor_updates(entry)
    return result


def update_purchasable_course(purchasable, entry):
    fee = get_course_fee(entry)
    provider = get_entry_purchasable_provider(entry)
    price = get_course_price(entry, provider)
    if price is None:  # price removed
        purchasable.Public = False
        logger.warn('Could not find price for %s', purchasable.NTIID)
    else:
        name = get_course_purchasable_name(entry) or entry.title
        title = get_course_purchasable_title(entry) or entry.title

        purchasable.Name = name
        purchasable.Title = title
        purchasable.Public = True

        # Update price properties
        purchasable.Amount = price.Amount
        purchasable.Currency = price.Currency
        purchasable.Giftable = is_course_giftable(entry)
        purchasable.Redeemable = is_course_redeemable(entry)
        purchasable.Fee = float(fee) if fee is not None else fee
        purchasable.Public = is_course_enabled_for_purchase(entry)

        # set vendor info fields
        vendor_info = get_course_publishable_vendor_info(entry)
        purchasable.VendorInfo = IPurchasableVendorInfo(vendor_info, None)
        purchasable.AllowVendorUpdates = allow_vendor_updates(entry)
    return purchasable


def sync_purchasable_course(context):
    entry = ICourseCatalogEntry(context, None)
    purchasable = IPurchasableCourse(entry, None)
    if purchasable is not None:
        update_purchasable_course(purchasable, entry)
        lifecycleevent.modified(purchasable)
    else:
        purchasable = create_purchasable_from_course(context)
        if purchasable is not None:
            lifecycleevent.created(purchasable)
            register_purchasable(purchasable)
    return purchasable

# purchasable course choice bundles


def get_state(purchasable):
    amount = int(purchasable.Amount * 100.0)  # cents
    result = (amount, purchasable.Currency.upper(),
              purchasable.isPublic(), purchasable.Giftable,
              purchasable.Redeemable, purchasable.Fee)
    return result


def items_and_ntiids(purchasables):
    items = set()
    ntiids = set()
    for p in purchasables:
        ntiids.add(p.NTIID)
        items.update(p.Items)
    ntiids = tuple(ntiids)
    items = to_frozenset(items)
    return items, ntiids


def allowed_tyes():
    result = (Number, date, datetime, timedelta, bool) + six.string_types
    return result


def get_common_vendor_info(purchasables):
    result = {}
    types = allowed_tyes()
    data = defaultdict(set)
    for p in purchasables:
        for k, v in p.VendorInfo.items():
            if isinstance(v, types):
                data[k].add(v)

    for k, s in data.items():
        if len(s) == 1:
            result[k] = s.__iter__().next()

    result = IPurchasableVendorInfo(result, None)
    return result


class PurchasableCourseChoiceBundle(StorePurchasableCourseChoiceBundle):

    Purchasables = None

    @readproperty
    def Bundle(self):
        return self.Name


def get_course_choice_bundle_ntiid(name, purchasables):
    purchasables = to_list(purchasables)
    reference_purchasable = purchasables[0]
    specific = make_specific_safe(name)
    ntiid = make_ntiid(provider=reference_purchasable.Provider,
                       nttype=PURCHASABLE_COURSE_CHOICE_BUNDLE,
                       specific=specific)
    return ntiid


def get_reference_purchasable(purchasables):
    purchasables = to_list(purchasables)
    reference_purchasable = purchasables[0]
    return reference_purchasable


def create_course_choice_bundle(name, purchasables):
    ntiid = get_course_choice_bundle_ntiid(name, purchasables)
    reference_purchasable = get_reference_purchasable(purchasables)

    # gather items and ntiids
    items, ntiids = items_and_ntiids(purchasables)
    result = create_course(ntiid=ntiid,
                           items=items,
                           name=name,
                           title=name,
                           description=name,
                           fee=reference_purchasable.Fee,
                           amount=reference_purchasable.Amount,
                           currency=reference_purchasable.Currency,
                           provider=reference_purchasable.Provider,
                           giftable=reference_purchasable.Giftable,
                           public=reference_purchasable.isPublic(),
                           redeemable=reference_purchasable.Redeemable,
                           vendor_info=get_common_vendor_info(purchasables),
                           factory=PurchasableCourseChoiceBundle)

    # save course properties
    result.Bundle = name  # alias
    result.Purchasables = ntiids
    return result


def process_choice_bundle(name, purchasables, notify=True):
    state = None
    validated = []

    for purchasable in purchasables or ():
        p_state = get_state(purchasable)
        if state is None:
            state = p_state
            validated.append(purchasable)
        elif state == p_state:
            validated.append(purchasable)
        elif notify:
            logger.warn("Purchasable %s(%s) will not be included in bundle %s",
                        purchasable.NTIID, p_state, name)

    # there is something to process
    if validated:
        result = create_course_choice_bundle(name, validated)
    elif notify:
        result = None
        logger.warn("Bundle %s does not have enough purchasables", name)
    return result, validated


def get_choice_bundle_map(registry=component):
    choice_bundle_map = defaultdict(list)
    catalog = registry.getUtility(ICourseCatalog)
    for entry in catalog.iterCatalogEntries():
        purchasable = IPurchasableCourse(entry, None)
        if purchasable is not None:
            for name in get_nti_choice_bundles(entry):
                choice_bundle_map[name].append(purchasable)
    return choice_bundle_map


def get_registered_choice_bundles(registry=component, by_name=False):
    result = {}
    for name, obj in list(registry.getUtilitiesFor(IPurchasableCourseChoiceBundle)):
        if by_name:
            result[obj.Name] = obj
        else:
            result[name] = obj
    return result


def update_purchasable_course_choice_bundle(stored, source, validated):
    # update non-public properties
    stored.Bundle = source.Bundle  # alias
    stored.Purchasables = source.Purchasables
    # update public properties
    stored.Items = source.Items
    reference_purchasable = get_reference_purchasable(validated)
    stored.Fee = reference_purchasable.Fee
    stored.Amount = reference_purchasable.Amount
    stored.Currency = reference_purchasable.Currency
    stored.Provider = reference_purchasable.Provider
    stored.Giftable = reference_purchasable.Giftable
    stored.Public = reference_purchasable.isPublic()
    stored.Redeemable = reference_purchasable.Redeemable
    # vendor info
    data = get_common_vendor_info(validated)
    stored.VendorInfo = IPurchasableVendorInfo(data)


def sync_purchasable_course_choice_bundles(registry=component):
    bundle_map = get_choice_bundle_map(registry)
    site_bundles = get_registered_choice_bundles(registry, by_name=True)
    for name, purchasables in bundle_map.items():
        stored = site_bundles.get(name)
        if stored is not None and stored.__parent__ != registry.getSiteManager():
            continue
        processed, validated = process_choice_bundle(name, purchasables)
        if processed is None:
            if stored is not None:  # removed
                stored.Public = False
                lifecycleevent.modified(stored)
        elif stored is not None:  # update
            update_purchasable_course_choice_bundle(stored, 
                                                    processed, 
                                                    validated)
            lifecycleevent.modified(stored)
        else:  # new
            lifecycleevent.created(processed)
            register_purchasable(processed)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from itertools import chain

from requests.structures import CaseInsensitiveDict

from zope.intid.interfaces import IIntIds

from zope import component

from zope.traversing.api import traverse

from zope.security.interfaces import IPrincipal

from ZODB.POSException import POSError

from nti.app.products.courseware_store.interfaces import ICoursePrice

from nti.app.products.courseware_store.model import CoursePrice

from nti.contenttypes.courses import get_course_vendor_info

from nti.contenttypes.courses.interfaces import NTIID_ENTRY_TYPE
from nti.contenttypes.courses.interfaces import NTIID_ENTRY_PROVIDER

from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.ntiids.ntiids import get_parts
from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.store import PURCHASABLE_COURSE

from nti.store.index import IX_CREATOR
from nti.store.index import IX_MIMETYPE
from nti.store.index import get_purchase_catalog

from nti.store.interfaces import IPurchasable
from nti.store.interfaces import IPurchaseAttempt
from nti.store.interfaces import IInvitationPurchaseAttempt
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.store import get_purchasables

from nti.store.utils import PURCHASE_ATTEMPT_MIME_TYPES


def get_vendor_info(context):
    info = get_course_vendor_info(context, False)
    return info or {}


def is_course_enabled_for_purchase(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Enabled', default=False)


def is_course_giftable(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Giftable', default=False)


def is_course_redeemable(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Redeemable', default=False)


def get_course_purchasable_provider(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Provider', default=None)


def get_course_purchasable_name(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Name', default=None)


def get_purchasable_redeem_cutoff_date(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/RedeemCutOffDate', default=None)


def get_purchasable_cutoff_date(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/PurchaseCutOffDate', default=None)


def get_course_purchasable_title(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Title', default=None)


def get_course_purchasable_fee(context):
    vendor_info = get_vendor_info(context)
    return traverse(vendor_info, 'NTI/Purchasable/Fee', default=None)
get_course_fee = get_course_purchasable_fee


def get_entry_purchasable_provider(context):
    entry = ICourseCatalogEntry(context)
    course = ICourseInstance(entry)
    parts = get_parts(entry.ntiid)
    return get_course_purchasable_provider(course) or parts.provider


def get_course_price(context, *names):
    course = ICourseInstance(context, None)
    names = chain(names, ('',)) if names else ('',)
    for name in names:
        result = component.queryAdapter(course,  ICoursePrice, name=name)
        if result is not None:
            return result
    return None


def get_course_purchasable_ntiid(context, name=None):
    entry = ICourseCatalogEntry(context)
    parts = get_parts(entry.ntiid)
    ntiid = make_ntiid(date=parts.date,
                       provider=parts.provider,
                       nttype=PURCHASABLE_COURSE,
                       specific=parts.specific)
    return ntiid
get_entry_purchasable_ntiid = get_course_purchasable_ntiid


def get_entry_ntiid_from_purchasable(context, provider=NTIID_ENTRY_PROVIDER):
    purchasable = IPurchasable(context)
    parts = get_parts(purchasable.NTIID)
    ntiid = make_ntiid(date=parts.date,
                       provider=provider,
                       nttype=NTIID_ENTRY_TYPE,
                       specific=parts.specific)
    return ntiid


def get_nti_course_price(context):
    vendor_info = get_vendor_info(context)
    amount = traverse(vendor_info, 'NTI/Purchasable/Price', default=None)
    currency = traverse(vendor_info, 'NTI/Purchasable/Currency', default='USD')
    if amount:
        result = CoursePrice(Amount=float(amount), Currency=currency)
        return result
    return None


def allow_vendor_updates(context):
    vendor_info = get_vendor_info(context)
    result = traverse(vendor_info,
                      'NTI/Purchasable/AllowVendorUpdates',
                      default=False)
    return bool(result) if result is not None else False


def get_nti_choice_bundles(context):
    vendor_info = get_vendor_info(context)
    result = traverse(vendor_info, 'NTI/Purchasable/ChoiceBundles', default=())
    result = result.split() if isinstance(result, six.string_types) else result
    return set(result) if result else ()


def find_catalog_entry(context):
    if isinstance(context, six.string_types):
        result = find_object_with_ntiid(context)
    else:
        result = context
    result = ICourseCatalogEntry(result, None)
    return result
safe_find_catalog_entry = find_catalog_entry


def find_allow_vendor_updates_purchases(entry, invitation=False):
    entry = find_catalog_entry(entry)
    if entry is None:
        return ()

    catalog = get_purchase_catalog()
    intids_purchases = catalog[IX_MIMETYPE].apply({
        'any_of': PURCHASE_ATTEMPT_MIME_TYPES
    })
    if not intids_purchases:
        return ()

    usernames = []
    enrollments = ICourseEnrollments(ICourseInstance(entry))
    for enrollment in enrollments.iter_enrollments():
        principal = IPrincipal(enrollment.Principal, None)
        if principal is not None and enrollment.Scope == ES_PURCHASED:
            usernames.append(principal.id.lower())

    creator_intids = catalog[IX_CREATOR].apply({'any_of': usernames})
    intids_purchases = catalog.family.IF.intersection(intids_purchases,
                                                      creator_intids)

    provider = get_entry_purchasable_provider(entry)
    ntiid = get_entry_purchasable_ntiid(entry, provider)

    result = []
    intids = component.getUtility(IIntIds)
    for uid in intids_purchases or ():
        try:
            purchase = intids.queryObject(uid)
            # filter any invalid object
            if     purchase is None \
                or not IPurchaseAttempt.providedBy(purchase):
                continue
            # invitations may not be required
            if not invitation and IInvitationPurchaseAttempt.providedBy(purchase):
                continue
            # check the purchasable is in the purchase
            if ntiid not in purchase.Items:
                continue
            # check vendor updates
            context = CaseInsensitiveDict(purchase.Context or {})
            if not context.get('AllowVendorUpdates', False):
                continue
            result.append(purchase)
        except (TypeError, POSError):
            continue
    return result


def find_allow_vendor_updates_users(entry, invitation=False):
    purchases = find_allow_vendor_updates_purchases(entry, invitation)
    result = {getattr(x.creator, 'username', x.creator) for x in purchases}
    return result


def get_purchasable_course_bundles(entry):
    result = []
    ntiid = getattr(entry, 'ntiid', entry)
    for purchasable in get_purchasables(provided=IPurchasableCourseChoiceBundle):
        if purchasable.Public and ntiid in purchasable.Items:
            result.append(purchasable)
    return result

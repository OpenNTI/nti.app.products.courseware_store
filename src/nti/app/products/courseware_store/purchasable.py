#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import datetime
from numbers import Number
from collections import defaultdict

from zope.proxy import ProxyBase

from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe

from nti.store import PURCHASABLE_COURSE_CHOICE_BUNDLE

from nti.store.course import create_course
from nti.store.course import PurchasableCourse
from nti.store.course import PurchasableCourseChoiceBundle

from nti.store.interfaces import IPurchasableVendorInfo

from nti.store.utils import to_list
from nti.store.utils import to_frozenset

def get_state(purchasable):
	amount = int(purchasable.Amount * 100.0)  # cents
	result = (amount, purchasable.Currency.upper(),
			  purchasable.Public, purchasable.Giftable,
			  purchasable.Redeemable, purchasable.Fee)
	return result

_marker = object()

class PurchasableCourseProxy(ProxyBase):

	AllowVendorUpdates = property(
					lambda s: s.__dict__.get('_v_allow_vendor_updates'),
					lambda s, v: s.__dict__.__setitem__('_v_allow_vendor_updates', v))

	CatalogEntryNTIID = property(
					lambda s: s.__dict__.get('_v_catalog_entry_ntiid'),
					lambda s, v: s.__dict__.__setitem__('_v_catalog_entry_ntiid', v))
	
	def __new__(cls, base, *args, **kwargs):
		return ProxyBase.__new__(cls, base)

	def __init__(self, base, allow=None, entry=None):
		ProxyBase.__init__(self, base)
		self.AllowVendorUpdates = allow
		self.CatalogEntryNTIID = entry

def create_proxy_course(**kwargs):
	kwargs['factory'] = PurchasableCourse
	result = create_course(**kwargs)
	result = PurchasableCourseProxy(result)
	return result

def _items_and_ntiids(purchasables):
	items = set()
	ntiids = set()
	for p in purchasables:
		ntiids.add(p.NTIID)
		items.update(p.Items)
	ntiids = tuple(ntiids)
	items = to_frozenset(items)
	return items, ntiids

def _allowed_tyes():
	return (six.string_types, Number, datetime.date, datetime.datetime,
			datetime.timedelta, bool)

def _get_common_vendor_info(purchasables):
	result = {}
	types = _allowed_tyes()
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

class PurchasableCourseChoiceBundleProxy(ProxyBase):

	AllowVendorUpdates = property(
				lambda s: s.__dict__.get('_v_allow_vendor_updates'),
				lambda s, v: s.__dict__.__setitem__('_v_allow_vendor_updates', v))

	Bundle = property(
				lambda s: s.__dict__.get('_v_bundle'),
				lambda s, v: s.__dict__.__setitem__('_v_bundle', v))

	Purchasables = property(
				lambda s: s.__dict__.get('_v_purchasables'),
				lambda s, v: s.__dict__.__setitem__('_v_purchasables', v))
	
	def __init__(self, base, allow=None, bundle=None, purchasables=()):
		ProxyBase.__init__(self, base)
		self.Bundle = bundle
		self.AllowVendorUpdates = allow
		self.Purchasables = purchasables

def create_course_choice_bundle(name, purchasables, proxy=True):
	purchasables = to_list(purchasables)
	reference_purchasable = purchasables[0]

	specific = make_specific_safe(name)
	ntiid = make_ntiid(provider=reference_purchasable.Provider,
					   nttype=PURCHASABLE_COURSE_CHOICE_BUNDLE,
					   specific=specific)

	# gather items and ntiids
	items, ntiids = _items_and_ntiids(purchasables)
	result = create_course(ntiid=ntiid,
						   items=items,
						   name=name,
						   title=name,
						   description=name,
						   fee=reference_purchasable.Fee,
						   public=reference_purchasable.Public,
						   amount=reference_purchasable.Amount,
						   currency=reference_purchasable.Currency,
						   provider=reference_purchasable.Provider,
						   giftable=reference_purchasable.Giftable,
						   redeemable=reference_purchasable.Redeemable,
						   vendor_info=_get_common_vendor_info(purchasables),
						   factory=PurchasableCourseChoiceBundle)

	result = PurchasableCourseChoiceBundleProxy(result)
	result.Bundle = name
	result.Purchasables = ntiids
	return result

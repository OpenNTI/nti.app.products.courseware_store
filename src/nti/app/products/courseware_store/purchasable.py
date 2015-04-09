#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.traversing.interfaces import IEtcNamespace

from nti.common.property import CachedProperty

from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.store import PURCHASABLE_COURSE_CHOICE_BUNDLE

from nti.store.course import create_course
from nti.store.course import PurchasableCourse
from nti.store.course import PurchasableCourseChoiceBundle

from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IPurchasableVendorInfo
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.utils import to_list
from nti.store.utils import to_frozenset

from .interfaces import get_course_publishable_vendor_info

from .utils import get_course_price
from .utils import is_course_giftable
from .utils import is_course_redeemable
from .utils import allow_vendor_updates
from .utils import get_nti_choice_bundles
from .utils import safe_find_catalog_entry
from .utils import is_course_enabled_for_purchase
from .utils import get_entry_purchasable_provider
	
def get_state(purchasable):
	result = (purchasable.Amount, purchasable.Currency,
			  purchasable.Public, purchasable.Giftable, purchasable.Redeemable)
	return result

## CS: Make sure this getters and setters are only set
## to properties defined in the IPurchasableCourse interface

_marker = object()

def _setter(name):
	def func(self, value):
		self.__dict__[name] = value
	return func

def _getter(name):
	def func(self):
		self.check_state()
		return self.__dict__.get(name, None)
	return func

def _alias(prop_name):
	prop_name = str(prop_name) # native string
	return property( _getter(prop_name), _setter(prop_name))

class BaseProxyMixin(object):
	
	AllowVendorUpdates = False

	Amount = _alias('Amount')
	Currency = _alias('Currency')
	
	Public = _alias('Public')
	Giftable = _alias('Giftable')
	Redeemable = _alias('Redeemable')
	
	@property
	def lastSynchronized(self):
		hostsites = component.queryUtility(IEtcNamespace, name='hostsites')
		result = getattr(hostsites, 'lastSynchronized', 0)
		return result

	def check_state(self):
		pass

class PurchasableProxy(PurchasableCourse, BaseProxyMixin):
	
	__external_class_name__ = 'PurchasableCourse'
	
	CatalogEntryNTIID = None
		
	@CachedProperty('lastSynchronized')
	def __state(self):
		if not self.CatalogEntryNTIID:
			return _marker
		try:
			entry = find_object_with_ntiid(self.CatalogEntryNTIID)
			if entry is None: # course removed
				self.Public = False
			else:
				provider = get_entry_purchasable_provider(entry)
				price = get_course_price(entry, provider)
				if price is None: # price removed
					self.Public = False
				else: # Update properties after sync
					self.Amount = price.Amount
					self.Currency = price.Currency
					self.Giftable = is_course_giftable(entry)
					self.Redeemable = is_course_redeemable(entry)
					self.Public = is_course_enabled_for_purchase(entry)
					self.AllowVendorUpdates = allow_vendor_updates(entry) 
					vendor_info = get_course_publishable_vendor_info(entry)
					self.VendorInfo = IPurchasableVendorInfo(vendor_info, None)
		except Exception:
			# running outside a transaction?
			self.Public = False
		return _marker

	def check_state(self):
		return self.__state # force a check on the properties values
			
def create_proxy_course(**kwargs):
	kwargs['factory'] = PurchasableProxy
	result = create_course(**kwargs)
	result.check_state() # fix cached property
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

@interface.implementer(IPurchasableCourseChoiceBundle)
class PurchasableCourseChoiceBundleProxy(PurchasableCourseChoiceBundle, BaseProxyMixin):
	
	__external_class_name__ = 'PurchasableCourseChoiceBundle'
	mimeType = mime_type = 'application/vnd.nextthought.store.purchasablecoursechoicebundle'
	
	Bundle = None
	Purchasables = ()
	
	@CachedProperty('lastSynchronized')
	def __state(self):		
		if not self.Purchasables:
			return _marker
		
		validated = []
		ref_state = get_state(self)
		for name in self.Purchasables:
			# make sure underlying purchasable course exists
			purchasable = component.getUtility(IPurchasableCourse, name=name)
			if purchasable is None:
				logger.warn("Purchasable %s was not found", name)
				continue
			
			# make sure choice bundles have not changed
			ntiid = getattr(purchasable, 'CatalogEntryNTIID', None)
			entry = safe_find_catalog_entry(ntiid)
			choice_bundles = get_nti_choice_bundles(entry)
			if choice_bundles and not self.Bundle in choice_bundles:
				logger.warn(
					"Purchasable %s has been dropped from bundle %s for course %s",
					purchasable.NTIID, self.NTIID, ntiid)
				continue

			# make sure state has not changed
			p_state = get_state(purchasable)
			if p_state != ref_state:
				logger.warn(
					"Purchasable %s has been dropped from bundle %s because "
					"its state %s changed",	purchasable.NTIID, self.NTIID, p_state)
				continue
			validated.append(purchasable)
		
		if len(validated) > 1:
			if len(validated) != len(self.Purchasables):
				items, ntiids = _items_and_ntiids(validated)
				self.Items = items
				self.Purchasables = ntiids
				logger.warn("Purchasable bundle %s now refers to %s", self.NTIID, items)
		else:
			self.Public = False
			logger.warn("Purchasable bundle %s is no longer valid", self.NTIID)
		return _marker

	def check_state(self):
		self.__state # force a check on the properties values

def create_course_choice_bundle(name, purchasables):
	purchasables = to_list(purchasables)
	reference_purchasable = purchasables[0]
	
	title = "%s Bundle" % name
	specific = make_specific_safe(name)
	ntiid = make_ntiid(provider=reference_purchasable.Provider,
					   nttype=PURCHASABLE_COURSE_CHOICE_BUNDLE, 
					   specific=specific)

	# gather items and ntiids
	items, ntiids = _items_and_ntiids(purchasables)	
	result = create_course(	ntiid=ntiid,
							items=items,
							name=name, 
							title=title,
							description=u'',
							public=reference_purchasable.Public,
							amount=reference_purchasable.Amount,
							currency=reference_purchasable.Currency,
							provider=reference_purchasable.Provider,
							giftable=reference_purchasable.Giftable,
							redeemable=reference_purchasable.Redeemable,
							vendor_info=None,
							factory=PurchasableCourseChoiceBundleProxy)
	
	# fix cached property
	result.check_state()

	# save properties
	result.Bundle = name
	result.Purchasables = ntiids
	return result

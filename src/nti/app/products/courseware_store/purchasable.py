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

from nti.store.interfaces import IPurchasableVendorInfo
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.utils import to_list

from .interfaces import get_course_publishable_vendor_info

from .utils import get_course_price
from .utils import is_course_giftable
from .utils import is_course_redeemable
from .utils import allow_vendor_updates
from .utils import is_course_enabled_for_purchase
from .utils import get_entry_purchasable_provider
	
def state(purchasable):
	result = (purchasable.Amount, purchasable.Currency,
			  purchasable.Public, purchasable.Giftable, purchasable.Redeemable)
	return result

## CS: Make sure this getters and setters are only set
## to properties defined in the IPurchasableCourse interface

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
			return
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
		except (StandardError, Exception):
			## running outside a transaction?
			self.Public = False

	def check_state(self):
		return self.__state # force a check on the properties values
			
def create_proxy_course(**kwargs):
	kwargs['factory'] = PurchasableProxy
	return create_course(**kwargs)

@interface.implementer(IPurchasableCourseChoiceBundle)
class PurchasableCourseChoiceBundleProxy(PurchasableCourseChoiceBundle, BaseProxyMixin):
	
	@CachedProperty('lastSynchronized')
	def __state(self):
		pass
	
	def check_state(self):
		self.__state # force a check on the properties values

def create_course_choice_bundle(name, purchasables):
	purchasables = to_list(purchasables)
	reference_purchasable = purchasables[0]
	
	specific = make_specific_safe("%s_bundle" % name)
	ntiid = make_ntiid(provider=reference_purchasable.Provider,
					   nttype=PURCHASABLE_COURSE_CHOICE_BUNDLE, 
					   specific=specific)

	title = "%s Bundle" % name
	items = list({p.NTIID for p in purchasables})
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
	return result

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

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contenttypes.courses.interfaces import ES_PUBLIC
from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import get_catalog_entry
from nti.contenttypes.courses.utils import get_enrollment_record
from nti.contenttypes.courses.utils import get_vendor_thank_you_page

from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import SingletonDecorator

from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IGiftPurchaseAttempt

from nti.store.purchasable import get_purchasable

from .interfaces import IStoreEnrollmentOption

@component.adapter(IStoreEnrollmentOption)
@interface.implementer(IExternalObjectDecorator)
class _StoreEnrollmentOptionDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		return self._is_authenticated

	@classmethod
	def _get_enrollment_record(cls, context, remoteUser):
		entry = get_catalog_entry(context.CatalogEntryNTIID)
		return get_enrollment_record(entry, remoteUser)

	def _do_decorate_external(self, context, result):
		record = self._get_enrollment_record(context, self.remoteUser)
		result['IsEnrolled'] = bool(record is not None and record.Scope == ES_PURCHASED)
		isAvailable = (record is None or record.Scope == ES_PUBLIC) and context.IsEnabled
		result['Enabled'] = result['IsAvailable'] = isAvailable
		result.pop('IsEnabled', None)  # redundant

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IGiftPurchaseAttempt)
class _VendorThankYouInfoDecorator(object):
	"""
	Decorate the thank you page information for gifts.
	"""

	__metaclass__ = SingletonDecorator

	thank_you_context_key = 'Gifting'

	def _predicate(self, context, result):
		return self._is_authenticated

	def get_course( self, purchase_attempt ):
		purchaseables = purchase_attempt.Items
		catalog = component.getUtility(ICourseCatalog)
		for item in purchaseables or ():
			purchasable = get_purchasable(item)
			if not IPurchasableCourse.providedBy(purchasable):
				continue
			for catalog_ntiid in purchasable.Items:
				try:
					entry = catalog.getCatalogEntry( catalog_ntiid )
					course = ICourseInstance( entry )
					return course
				except KeyError:
					logger.error("Could not find course entry %s", catalog_ntiid)

	def decorateExternalMapping(self, context, result):
		course = self.get_course( context )
		thank_you_page = get_vendor_thank_you_page( course, self.thank_you_context_key )
		if thank_you_page:
			result['VendorThankYouPage'] = thank_you_page

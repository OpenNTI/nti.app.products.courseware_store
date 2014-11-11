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

from nti.app.products.courseware.utils import get_enrollment_record

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contenttypes.courses.interfaces import ES_PUBLIC
from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog 
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.externalization.externalization import to_external_object
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator
	
from nti.store.purchasable import get_purchasable
from nti.store.interfaces import IPurchasableCourse

from .interfaces import IStoreEnrollmentOption

@component.adapter(ICourseCatalogEntry)
@interface.implementer(IExternalMappingDecorator)
class _StoreCourseEntryLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		return self._is_authenticated
	
	def _do_decorate_external(self, context, result):
		purchasable = IPurchasableCourse(context, None)
		purchasable = get_purchasable(purchasable.NTIID) if purchasable else None
		if purchasable is not None and purchasable.Public:
			options = result.setdefault('EnrollmentOptions', {})
			store_enrollment = options.setdefault('StoreEnrollment', {})
			# set purchasable
			ext_obj = to_external_object(purchasable, name='summary')
			store_enrollment['Purchasable'] = ext_obj
			store_enrollment['RequiresAdmission'] = False
			store_enrollment['Price'] = ext_obj.get('Amount', None)
			store_enrollment['Currency'] = ext_obj.get('Currency', None)
			store_enrollment['IsEnrolled'] = ext_obj.get('Activated', False)

@component.adapter(IStoreEnrollmentOption)
@interface.implementer(IExternalObjectDecorator)
class _StoreEnrollmentOptionLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		return self._is_authenticated
	
	@classmethod
	def _get_course(cls, context):
		try:
			catalog = component.getUtility(ICourseCatalog)
			entry = catalog.getCatalogEntry(context.CatalogEntryNTIID)
			course = ICourseInstance(entry, None)
			return course
		except (KeyError, AttributeError):
			pass
		return None
	
	@classmethod
	def _get_enrollment_record(cls, context, remoteUser):
		course = cls._get_course(context)
		if course is not None:
			return get_enrollment_record(course, remoteUser)
		return None
	
	def _do_decorate_external(self, context, result):
		record = self._get_enrollment_record(context, self.remoteUser)
		isAvailable = bool(record is None or record.Scope == ES_PUBLIC)
		result['IsAvailable'] = isAvailable
		IsEnrolled = record is not None and record.Scope == ES_PURCHASED
		result['IsEnrolled'] = IsEnrolled

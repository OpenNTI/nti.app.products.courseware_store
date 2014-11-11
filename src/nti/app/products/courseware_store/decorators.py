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

from nti.externalization.interfaces import IExternalObjectDecorator

from .interfaces import IStoreEnrollmentOption

@component.adapter(IStoreEnrollmentOption)
@interface.implementer(IExternalObjectDecorator)
class _StoreEnrollmentOptionDecorator(AbstractAuthenticatedRequestAwareDecorator):

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
		result['Enabled'] = result['IsAvailable'] = isAvailable
		IsEnrolled = bool(record is not None and record.Scope == ES_PURCHASED)
		result['IsEnrolled'] = IsEnrolled

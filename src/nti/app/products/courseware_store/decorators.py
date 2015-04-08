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

from nti.app.products.courseware.utils import get_catalog_entry
from nti.app.products.courseware.utils import get_enrollment_record

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contenttypes.courses.interfaces import ES_PUBLIC
from nti.contenttypes.courses.interfaces import ES_PURCHASED

from nti.externalization.interfaces import IExternalObjectDecorator

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
		IsEnrolled = bool(record is not None and record.Scope == ES_PURCHASED)
		isAvailable = (record is None or record.Scope == ES_PUBLIC) and context.IsEnabled
		result['Enabled'] = result['IsAvailable'] = isAvailable
		result['IsEnrolled'] = IsEnrolled
		result.pop('IsEnabled', None) # redundant

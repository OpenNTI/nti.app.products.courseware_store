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

from dolmen.builtins.interfaces import IString

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.externalization.externalization import to_external_object
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.store.purchasable import get_purchasable
	
@component.adapter(ICourseCatalogEntry)
@interface.implementer(IExternalMappingDecorator)
class _StoreCourseEntryLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		return self._is_authenticated
	
	def _do_decorate_external(self, context, result):
		ntiid = component.queryAdapter(context, IString, name="purchasable_course_ntiid")
		purchasable = get_purchasable(ntiid) if ntiid else None
		if purchasable is not None and not purchasable.Public:
			options = result.setdefault('EnrollmentOptions', {})
			store_enrollment = options.setdefault('StoreEnrollment', {})
			# set purchasable
			ext_obj = to_external_object(purchasable, name='summary')
			store_enrollment['Purchasable'] = ext_obj
			store_enrollment['RequiresAdmission'] = False
			store_enrollment['Price'] = ext_obj.get('Amount', None)
			store_enrollment['Currency'] = ext_obj.get('Currency', None)
			store_enrollment['IsEnrolled'] = ext_obj.get('Activated', False)

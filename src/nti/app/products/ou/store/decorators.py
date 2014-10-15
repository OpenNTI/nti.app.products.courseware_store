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

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.externalization.externalization import to_external_object
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.store.purchasable import get_purchasable

from ..courseware.decorators import BaseOUCourseEntryDecorator
	
@component.adapter(ICourseCatalogEntry)
@interface.implementer(IExternalMappingDecorator)
class _StoreCourseEntryLinkDecorator(BaseOUCourseEntryDecorator):

	def _predicate(self, context, result):
		return self._is_authenticated
	
	def get_and_set_date(self, info, result, name):
		ikey = 'OU/%s' % name
		okey = 'OU_%s' % name
		result = super(_StoreCourseEntryLinkDecorator, self).\
								get_and_set_date(info, ikey, okey, result)
		return result
			
	def _do_decorate_external(self, context, result):
		ntiid = component.queryAdapter(context, IString, name="purchasable_course_ntiid")
		purchasable = get_purchasable(ntiid) if ntiid else None
		if purchasable is None or not purchasable.Public:
			return
		options = result.setdefault('EnrollmentOptions', {})
		store_enrollment = options.setdefault('StoreEnrollment', {})
		# set purchasable
		ext_obj = to_external_object(purchasable, name='summary')
		store_enrollment['Purchasable'] = ext_obj
		store_enrollment['RequiresAdmission'] = False
		store_enrollment['Price'] = ext_obj.get('Amount', None)
		store_enrollment['Currency'] = ext_obj.get('Currency', None)
		store_enrollment['IsEnrolled'] = ext_obj.get('Activated', False)
		# set OU info
		course = ICourseInstance(context, None)
		vendor_info = ICourseInstanceVendorInfo(course, {})
		self.get_and_set_date(vendor_info, store_enrollment, 'DropCutOffDate')
		self.get_and_set_date(vendor_info, store_enrollment, 'EnrollStartDate')
		self.get_and_set_date(vendor_info, store_enrollment, 'RefundCutOffDate')

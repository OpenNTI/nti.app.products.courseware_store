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
from zope.traversing.api import traverse

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.dataserver.interfaces import IUser

from nti.utils.property import Lazy

from ..courseware.decorators import BaseOUCourseEntryDecorator

from .utils import get_course_key
from .utils import is_fmaep_capable
from .utils import get_fmaep_crn_and_term
from .utils.links import create_fmaep_link

from .interfaces import PENDING
from .interfaces import ADMITTED
from .interfaces import REJECTED
from .interfaces import SUSPENDED
from .interfaces import IPaymentStorage
from .interfaces import IUserAdmissionData

LINKS = StandardExternalFields.LINKS

create_link = create_fmaep_link

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _FMAEPUserLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		admin_data = IUserAdmissionData(context)
		links = mapping.setdefault(LINKS, [])

		# common links
		links.append(create_link(context, 'fmaep_country_names'))
		links.append(create_link(context, 'fmaep_state_names'))

		# account status
		if admin_data.PIDM:
			links.append(create_link(context, 'fmaep_account_status'))

		# state links
		state = admin_data.state
		mapping['fmaep_admission_state'] = state

		if not state or state == REJECTED:
			links.append(create_link(context, 'fmaep_admission'))
			links.append(create_link(context, 'fmaep_admission_preflight'))
		elif state in (PENDING, SUSPENDED) or admin_data.tempmatchid:
			links.append(create_link(context, 'fmaep_query_admission', method='GET'))
		elif state == ADMITTED:
			links.append(create_link(context, 'fmaep_enrolled_courses', method='GET'))

@component.adapter(ICourseCatalogEntry)
@interface.implementer(IExternalMappingDecorator)
class _FMAEPCourseEntryLinkDecorator(BaseOUCourseEntryDecorator):

	@Lazy
	def admin_data(self):
		return IUserAdmissionData(self.remoteUser, None)

	@Lazy
	def _is_admitted(self):
		return getattr(self.admin_data, 'state', None) == ADMITTED

	@classmethod
	def _is_fmaep_capable(self, context):
		course = ICourseInstance(context,)
		return is_fmaep_capable(course)
	
	def get_and_set_date(self, info, result, name):
		ikey = 'OU/%s' % name
		okey = 'OU_%s' % name
		result = super(_FMAEPCourseEntryLinkDecorator, self).get_and_set_date(info, ikey, okey, result)
		return result

	def _set_fmaep_links(self, fmaep, CRN, Term, enroll_start, enroll_cutoff):
		result = fmaep.setdefault(LINKS, [])
		
		# course details is always avaiable
		result.append(create_link(self.remoteUser, 'fmaep_course_details',
				 			 	  params={'CRN':CRN, 'Term':Term},
				 			 	  method='GET'))

		if self._is_admitted:
			course_key = get_course_key(CRN, Term)
			allow_enroll = self.linked_allowed(enroll_start, enroll_cutoff)
				
			# payment links
			payment_storage = IPaymentStorage(self.remoteUser)
			record = payment_storage.get(course_key)
			if allow_enroll and (record is None or not record.is_success()):
				result.append(create_link(self.remoteUser, 'fmaep_pay_and_enroll'))
				if record is not None:
					fmaep['PaymentInProgress'] = True
					fmaep['PaymentAttempts'] = record.attempts
			fmaep['IsEnrolled'] = bool(record is not None and record.is_success())
	
			# always show is_pay_done link
			result.append(create_link(self.remoteUser, 'fmaep_is_pay_done'))
		return result
	
	def _copy_legacy(self, result, fmaep, fmaep_links):
		links = result.setdefault(LINKS, [])
		links.extend(fmaep_links)
		for k, v in fmaep.items():
			if k not in result:
				result[k] = v
	
	def _decorate_for_course(self, context, result, course):
		record = get_fmaep_crn_and_term(course)
		if not record:
			return
			
		options = result.setdefault('EnrollmentOptions', {})	
		fmaep = options.setdefault('FiveminuteEnrollment', {})
		fmaep['RequiresAdmission'] = True
		
		# check 4 CRN/Term code
		CRN, Term = None, None
		fmaep_capable = is_fmaep_capable(course)
		if record:
			CRN, Term = record[0], record[1]
			fmaep['NTI_CRN'] = CRN
			fmaep['NTI_Term'] = Term
			fmaep['NTI_FiveminuteEnrollmentCapable'] = fmaep_capable

		# check for prince and enrollment dates
		vendor_info = ICourseInstanceVendorInfo(course, {})
		self.get_and_set_date(vendor_info, fmaep, 'RefundCutOffDate')
		drop_cutoff = self.get_and_set_date(vendor_info, fmaep, 'DropCutOffDate')
		enroll_start = self.get_and_set_date(vendor_info, fmaep, 'EnrollStartDate')
		
		# check price
		price = traverse(vendor_info, 'OU/Price', default=None)
		if price is not None:
			fmaep['OU_Price'] = price
				
		fmaep_links = ()
		if CRN and Term:
			fmaep_links = self._set_fmaep_links(fmaep, CRN, Term, 
												enroll_start, drop_cutoff)

		## CS For legacy purposes copy links and fmaep info to main mapping
		## Don't overwrite existing keys
		self._copy_legacy(result, fmaep, fmaep_links)

	def _do_decorate_external(self, context, result):	
		course_instance = ICourseInstance(context, None)
		if course_instance is not None:
			self._decorate_for_course(context, result, course_instance)

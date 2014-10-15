#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration between legacy code and future code.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Do not import, only exist for ZODB broken objects.",
	"nti.app.products.courseware.legacy_course",
	"_LegacyCommunityBasedCourseAdministrativeLevel",
	"_LegacyCommunityBasedCourseInstance"
)

try:
	from nti.app.products.courseware.legacy_course import DefaultCourseCatalogLegacyEntryInstancePolicy
except ImportError:
	DefaultCourseCatalogLegacyEntryInstancePolicy = object

class OUCourseCatalogLegacyEntryInstancePolicy(DefaultCourseCatalogLegacyEntryInstancePolicy):

	register_courses_in_components_named = 'platform.ou.edu'

	def extend_signature_for_instructor(self, inst, sig_lines):
		sig_lines.append( "University of Oklahoma" )

	def department_title_for_entry(self, entry):
		"""
		For bad content that uses just one word for school,
		use our provider-specific logic to assume it's a
		`Department of X at the University of Oklahoma`
		"""

		title = entry.ProviderDepartmentTitle
		if title and (len(title.split()) == 1
					  or ('Department' not in title
						  and 'School' not in title
						  and 'College' not in title)):
			title = "Department of %s at the University of Oklahoma" % title

		return title

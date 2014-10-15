#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

import zope.intid

from zope import component
from zope.traversing.api import traverse

from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

# misc

def get_uid(obj):
	intids = component.getUtility(zope.intid.IIntIds)
	result = intids.getId(obj)
	return result

def is_true(s):
	return s and str(s).lower() in ('1','t', 'y','yes','true')

def is_false(s):
	return s and str(s).lower() in ('0','f', 'n','no','false')

def safe_compare(s, *args):
	s = str(s) if not isinstance(s, six.string_types) else s
	if not s or not args:
		return False
	if len(args) == 1:
		return isinstance(args[0], six.string_types) and s.lower() == args[0].lower()
	return s.lower() in [x.lower() for x in args if isinstance(x, six.string_types)]

# course

def get_crn_term_from_course_key(course_key):
	result = course_key.split('.')
	return result[0], result[1]
crn_term_from_course_key = get_crn_term_from_course_key

def get_course_key(crn, term_code):
	result = "%s.%s" % (crn, term_code)
	return result.upper()

def is_fmaep_capable(course_instance):
	course_vendor_info = ICourseInstanceVendorInfo(course_instance, {})
	result = traverse(course_vendor_info, 'NTI/5MAEP/EnrollmentCapable', default=None)
	return is_true(result) if result else False

def get_fmaep_crn_and_term(course_instance):
	course_vendor_info = ICourseInstanceVendorInfo(course_instance, {})
	crn = traverse(course_vendor_info, 'NTI/5MAEP/CRN', default=None)
	term_code = traverse(course_vendor_info, 'NTI/5MAEP/Term', default=None)
	if crn and term_code:
		return (crn, term_code)
	return ()

def get_fmaep_key_from_course(course_instance):
	record = get_fmaep_crn_and_term(course_instance)
	if record:
		return get_course_key(record[0], record[1])
	return None


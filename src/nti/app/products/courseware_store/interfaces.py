#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from nti.schema.field import Number
from nti.schema.field import ValidTextLine

class ICoursePrice(interface.Interface):
	Amount = Number(title="The price amount", required=True)
	Currency = ValidTextLine(title="The currency", required=False, default='USD')
	
class ICoursePriceFinder(interface.Interface):
	"""
	marker interface for a course price finder
	"""

class ICoursePublishableVendorInfo(interface.Interface):
	"""
	marker interface for a vendor info that can be made public.
	this will be registered as subscribers
	"""

	def info():
		"""
		return a map with public info
		"""

def get_course_publishable_vendor_info(course):
	result = {}
	subscribers = component.subscribers((course,), ICoursePublishableVendorInfo)
	for s in list(subscribers):
		info = s.info()
		result.update(info or {})
	return result

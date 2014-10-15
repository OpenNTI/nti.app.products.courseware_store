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

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import IDenyOpenEnrollment

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from .interfaces import IOUUser
from .interfaces import IOUUserProfile

@component.adapter(IOUUser)
@interface.implementer(IExternalMappingDecorator)
class OUUserDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		profile = IOUUserProfile(context, None) or context
		mapping['OU4x4'] = getattr(profile, 'OU4x4', None) or context.username
		mapping['OUID'] = getattr(profile, 'soonerID', None) or profile.username


@component.adapter(ICourseCatalogEntry)
@interface.implementer(IExternalMappingDecorator)
class OpenEnrollmentCourseEntryDecorator(AbstractAuthenticatedRequestAwareDecorator):
	
	def _predicate(self, context, result):
		return self._is_authenticated
	
	def _do_decorate_external(self, context, result):
		options = result.setdefault('EnrollmentOptions', {})	
		open_en = options.setdefault('OpenEnrollment', {})
		open_en['Enabled'] = not IDenyOpenEnrollment.providedBy(context)

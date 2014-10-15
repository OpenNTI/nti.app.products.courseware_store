#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
import simplejson

from zope import component
from zope.traversing.api import traverse

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict

from nti.utils.maps import CaseInsensitiveDict

from ..views import JanuxPathAdapter

from . import is_true
from . import workflow

def _get_source(values, keys, name):
	# check map
	source = None
	for key in keys:
		source = values.get(key)
		if source is not None:
			break
	# validate
	if isinstance(source, six.string_types):
		source = os.path.expanduser(source)
		if not os.path.exists(source):
			raise hexc.HTTPUnprocessableEntity(detail='%s file not found' % name)
	elif source is not None:
		source = source.file
		source.seek(0)
	else:
		raise hexc.HTTPUnprocessableEntity(detail='No %s source provided' % name)
	return source

@view_config(route_name='objects.generic.traversal',
			 name='ou_nti_enrollment',
			 renderer='rest',
			 permission=nauth.ACT_MODERATE,
			 context=JanuxPathAdapter)
def ou_nti_enrollment(request):
	if request.POST:
		values = CaseInsensitiveDict(request.POST)
	else:
		values = simplejson.loads(unicode(request.body, request.charset))
		values = CaseInsensitiveDict(values)
	ims_file = _get_source(values, ('ims_file', 'ims'), 'IMS')
	create_persons = is_true(values.get('create_users', values.get('create_persons')))

	# Make sure we don't send enrollment email, etc, during this process
	# by not having any interaction.
	# This is somewhat difficult to test the side-effects of, sadly.
	endInteraction()
	try:
		result = workflow.process(ims_file, create_persons)
	finally:
		restoreInteraction()
	return result

@view_config(route_name='objects.generic.traversal',
			 name='ou_nti_create_users',
			 renderer='rest',
			 permission=nauth.ACT_MODERATE,
			 context=JanuxPathAdapter)
def ou_nti_create_users(request):
	if request.POST:
		values = CaseInsensitiveDict(request.POST)
	else:
		values = simplejson.loads(unicode(request.body, request.charset))
		values = CaseInsensitiveDict(values)
	ims_file = _get_source(values, ('ims_file', 'ims'), 'IMS')
	result = workflow.create_users(ims_file)
	return LocatedExternalDict(Created=result)

@view_config(route_name='objects.generic.traversal',
			 name='ou_nti_courses',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE,
			 context=JanuxPathAdapter)
def ou_nti_courses(request):

	request = request
	params = CaseInsensitiveDict(request.params)
	all_courses= params.get('all') or params.get('allCourses') or params.get('all_courses')
	all_courses = is_true(all_courses)

	result = LocatedExternalDict()
	entries = result['Items'] = {}

	catalog = component.getUtility(ICourseCatalog)
	for catalog_entry in catalog.iterCatalogEntries():
		course_instance = ICourseInstance(catalog_entry)
		course_vendor_info = ICourseInstanceVendorInfo(course_instance, {})

		if not all_courses:
			sourcedid = traverse(course_vendor_info, 'OU/IMS/sourcedid', default=None)
			if not sourcedid:
				continue

		entry = entries[catalog_entry.ProviderUniqueID] = {'VendorInfo': course_vendor_info}
		bundle = getattr(course_instance, 'ContentPackageBundle', None)
		entry['ContentPackageBundle'] = getattr(bundle, 'ntiid', None)
		entry['CatalogEntryNTIID'] = getattr(catalog_entry, 'ntiid', None)

	result['Total'] = len(entries)
	return result

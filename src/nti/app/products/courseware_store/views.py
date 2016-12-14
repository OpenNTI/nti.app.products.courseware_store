#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import csv
from io import BytesIO

from zope.component.hooks import site as current_site

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware.views import CourseAdminPathAdapter

from nti.app.products.courseware_store import MessageFactory as _

from nti.app.products.courseware_store.purchasable import get_registered_choice_bundles
from nti.app.products.courseware_store.purchasable import sync_purchasable_course_choice_bundles

from nti.app.products.courseware_store.utils import find_catalog_entry
from nti.app.products.courseware_store.utils import find_allow_vendor_updates_purchases

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.hostpolicy import get_host_site

from nti.site.site import get_component_hierarchy_names

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

def _tx_string(s):
	if s and isinstance(s, unicode):
		s = s.encode('utf-8')
	return s

def _parse_course(params):
	ntiid = params.get('ntiid') or params.get('course')
	entry = find_catalog_entry(ntiid) if ntiid else None
	return entry

@view_config(context=IDataserverFolder)
@view_config(context=CourseAdminPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
				renderer='rest',
			 	permission=nauth.ACT_NTI_ADMIN,
			 	name='VendorUpdatesPurchasedCourse')
class VendorUpdatesPurchasedCourseView(AbstractAuthenticatedView):

	def __call__(self):
		params = CaseInsensitiveDict(self.request.params)
		entry = _parse_course(params)
		if entry is None:
			raise hexc.HTTPUnprocessableEntity(detail=_('Course not found or specified.'))

		bio = BytesIO()
		csv_writer = csv.writer(bio)

		# header
		header = ['username', 'name', 'email']
		csv_writer.writerow(header)

		purchases = find_allow_vendor_updates_purchases(entry)
		for purchase in purchases:
			creator = purchase.creator
			username = getattr(creator, 'username', creator)
			profile = purchase.Profile
			email = getattr(profile, 'email', None)
			name = getattr(profile, 'realname', None) or username
			# write data
			row_data = [username, name, email]
			csv_writer.writerow([_tx_string(x) for x in row_data])

		response = self.request.response
		response.body = bio.getvalue()
		response.content_disposition = b'attachment; filename="updates.csv"'
		return response

@view_config(context=IDataserverFolder)
@view_config(context=CourseAdminPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
				renderer='rest',
			 	permission=nauth.ACT_NTI_ADMIN,
			 	name='SyncPurchasableCourseChoiceBundles')
class SyncPurchasableCourseChoiceBundlesView(AbstractAuthenticatedView):

	def __call__(self):
		# sync in all hierarchy sites
		for name in get_component_hierarchy_names():
			site = get_host_site(name)
			with current_site(site):
				sync_purchasable_course_choice_bundles()

		result = LocatedExternalDict()
		bundles = get_registered_choice_bundles()
		items = result[ITEMS] = list(bundles.values())
		result[TOTAL] = result[ITEM_COUNT] = len(items)
		return result

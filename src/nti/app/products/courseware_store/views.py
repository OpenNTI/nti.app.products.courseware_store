#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import csv
from io import BytesIO

from zope import component

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.common.maps import CaseInsensitiveDict

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver import authorization as nauth

from nti.ntiids.ntiids import find_object_with_ntiid

from .utils import find_allow_vendor_updates_purchases

def _tx_string(s):
	if s and isinstance(s, unicode):
		s = s.encode('utf-8')
	return s

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IDataserverFolder,
			 permission=nauth.ACT_NTI_ADMIN,
			 name='VendorUpdatesPurchasedCourse')
class VendorUpdatesPurchasedCourseView(AbstractAuthenticatedView):

	def __call__(self):
		params = CaseInsensitiveDict(self.request.params)

		ntiid = params.get('ntiid') or \
				params.get('entry') or \
				params.get('course')
		if not ntiid:
			raise hexc.HTTPUnprocessableEntity(detail=_('No course entry identifier'))

		context = find_object_with_ntiid(ntiid)
		entry = ICourseCatalogEntry(context, None)
		if entry is None:
			try:
				catalog = component.getUtility(ICourseCatalog)
				entry = catalog.getCatalogEntry(ntiid)
			except LookupError:
				raise hexc.HTTPUnprocessableEntity(detail=_('Catalog not found'))
			except KeyError:
				raise hexc.HTTPUnprocessableEntity(detail=_('Course not found'))

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

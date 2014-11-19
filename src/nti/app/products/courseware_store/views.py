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

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver import authorization as nauth

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile

from nti.utils.maps import CaseInsensitiveDict

from .utils import find_allow_vendor_updates_users

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE,
			 name='VendorUpdatesPurchasedCourse')
class VendorUpdatesPurchasedCourseView(AbstractAuthenticatedView):
	
	def __call__(self):
		params = CaseInsensitiveDict(self.request.params)
		
		ntiid = params.get('ntiid') or \
				params.get('entry') or \
				params.get('course') or \
				params.get('ProviderUniqueID')
		if not ntiid:
			raise hexc.HTTPUnprocessableEntity(detail=_('No course entry identifier'))

		try:
			catalog = component.getUtility(ICourseCatalog)
			entry = catalog.getCatalogEntry(ntiid)
		except LookupError:
			raise hexc.HTTPNotFound(detail=_('Catalog not found'))
		except KeyError:
			raise hexc.HTTPNotFound(detail=_('Course not found'))

		bio = BytesIO()
		csv_writer = csv.writer(bio)
		
		# header
		header = ['Username', 'Name', 'Email'] 
		csv_writer.writerow(header)
		
		usernames = find_allow_vendor_updates_users(entry)
		for username in usernames:
			user = User.get_user(username)
			if not user or not IUser.providedBy(user):
				continue

			profile = IUserProfile( user, None )
			email = getattr(profile, 'email', None)
			name = getattr(profile, 'realname', None) or username
						
			row_data = [username, name, email]
			csv_writer.writerow(row_data)

		response = self.request.response
		response.body = bio.getvalue()
		response.content_disposition = b'attachment; filename="updates.csv"'
		return response

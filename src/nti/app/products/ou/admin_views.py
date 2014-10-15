#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import csv
import six
from io import BytesIO
from datetime import datetime
from datetime import timedelta

from zope import component

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.authorization import ACT_MODERATE
from nti.dataserver.users.interfaces import IUserProfile

from nti.externalization.interfaces import LocatedExternalDict

from nti.utils.maps import CaseInsensitiveDict

from .logon import get_ldap_attr
from .logon import save_attributes
from .logon import is_valid_ou_user

from .views import JanuxPathAdapter

from .interfaces import IOUUser
from .interfaces import IUserResearchStatus

def _make_min_max_btree_range(search_term):
	min_inclusive = search_term	 # start here
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive

def username_search(search_term):
	min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout(dataserver).users_folder
	usernames = list(_users.iterkeys(min_inclusive, max_exclusive, excludemax=True))
	return usernames

@view_config(route_name='objects.generic.traversal',
			 name='ou_set_user_attributes',
			 renderer='rest',
			 request_method='POST',
			 permission=ACT_MODERATE,
			 context=JanuxPathAdapter)
class OUSetUserAttributesView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):
	
	def readInput(self):
		result = CaseInsensitiveDict()
		if self.request.body:
			data = super(OUSetUserAttributesView, self).readInput()
			result.update(data)
		return result
	
	def _do_call( self ):
		values = CaseInsensitiveDict(self.readInput())
		usernames = values.get('username') or values.get('usernames')
		term = values.get('term', values.get('search', None))
		if term:
			usernames = username_search(term)
		elif usernames and isinstance(usernames, six.string_types):
			usernames = usernames.split(',')
		else:
			dataserver = component.getUtility(IDataserver)
			usernames = IShardLayout(dataserver).users_folder.keys()
	
		result = LocatedExternalDict()
		items = result['Items'] = {}
		errors = result['Errors'] = []
	
		for username in usernames:
			user = User.get_user(username)
			if user is None or not IUser.providedBy(user):
				continue
	
			if	IOUUser.providedBy(user) and getattr(user, 'soonerID', None) and \
				getattr(user, 'OU4x4', None):
				continue
	
			try:
				ldap_data = is_valid_ou_user(user.username)
				ldap_data = ldap_data[0] if ldap_data else ()
				ldap_data = ldap_data[1] if len(ldap_data) >= 2 else None
				if ldap_data:
					OU4x4 = user.username
					soonerID = get_ldap_attr(ldap_data, 'employeeNumber')
					if save_attributes(user, soonerID, OU4x4):
						items[user.username] = (username, soonerID)
				else:
					logger.warn("Data for %s could not be found in LDAP" % user)
			except Exception as e:
				msg = "Error getting LDAP data for user %s.%s" % (user, e)
				errors.append(msg)
	
		return result

@view_config(route_name='objects.generic.traversal',
			 name='UsersInterestedInCredit.csv',
			 renderer='rest',
			 request_method='GET',
			 permission=ACT_MODERATE,
			 context=JanuxPathAdapter)
class ExportUsersInterestedIncreditView(AbstractAuthenticatedView):
	
	def __call__( self ):
		dataserver = component.getUtility(IDataserver)
		users_folder = IShardLayout(dataserver).users_folder
	
		buf = BytesIO()
		writer = csv.writer(buf)
		writer.writerow(['Username', 'Email', 'Alias', 'Real Name'])
	
		for user in users_folder.values():
			if not IUser.providedBy(user):
				continue
	
			profile = IUserProfile(user,None)
			interested = getattr(profile, 'interested_in_credit', False)
			email = getattr(profile, 'email', None)
	
			if interested and email:
				writer.writerow([user.username, email,
								 (profile.alias or '').encode('utf-8'),
								 (profile.realname or '').encode('utf-8')])
	
		response = self.request.response
		response.body = buf.getvalue()
		response.content_disposition = b'attachment; filename="UsersInterestedInCredit.csv"'
		return response

@view_config(route_name='objects.generic.traversal',
			 name='ou_user_research_stats',
			 renderer='rest',
			 request_method='GET',
			 permission=ACT_MODERATE,
			 context=JanuxPathAdapter)
class UserResearchStatsView(AbstractAuthenticatedView):
	
	def __call__( self ):
		result = LocatedExternalDict()
	
		dataserver = component.getUtility(IDataserver)
		users_folder = IShardLayout(dataserver).users_folder
	
		allow_count = deny_count = neither_count = 0
	
		now = datetime.utcnow()
		year_ago = now - timedelta( days=365 )
	
		# This is pretty slow. Perhaps we should index this field?
		for user in users_folder.values():
			if not IUser.providedBy(user):
				continue
			
			research_status = IUserResearchStatus( user )
			last_mod = research_status.lastModified
			if last_mod is not None:
				# First, find the year+ older entries; they are promptable.
				if datetime.utcfromtimestamp( last_mod ) < year_ago:
					neither_count +=1
					continue
	
			if research_status.allow_research:
				allow_count += 1
			else:
				deny_count += 1
	
		result['DenyResearchCount'] = deny_count
		result['AllowResearchCount'] = allow_count
		result['ToBePromptedCount'] = neither_count
		return result

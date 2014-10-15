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

from zope import component

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver.users import User
from nti.dataserver import authorization as nauth
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.externalization.interfaces import LocatedExternalDict

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout

from nti.utils.maps import CaseInsensitiveDict

from ..views import JanuxPathAdapter

from .utils import is_true
from .utils import safe_compare

from . import get_url_map
from . import ACCOUNT_STATUS_URL

from .interfaces import ADMISSION_STATES
from .interfaces import IUserAdmissionData

from .process import account_status
from .process import set_user_state
from .process import find_ou_courses
from .process import query_admission

def _make_min_max_btree_range(search_term):
	min_inclusive = search_term  # start here
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive

def username_search(search_term):
	min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout(dataserver).users_folder
	usernames = list(_users.iterkeys(min_inclusive, max_exclusive, excludemax=True))
	return usernames

def _all_user_names():
	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout(dataserver).users_folder
	return _users.keys()

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_users_status',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE,
			 context=JanuxPathAdapter)
class UsersStatusView(AbstractAuthenticatedView):

	def __call__(self):
		stream = BytesIO()
		writer = csv.writer( stream )
		response = self.request.response
		response.content_encoding = str('identity' )
		response.content_type = str('text/csv; charset=UTF-8')
		response.content_disposition = str( 'attachment; filename="fmaep_users_status.csv"' )

		values = CaseInsensitiveDict(**self.request.params)
		term = values.get('term', values.get('search', None))
		usernames = values.get('usernames', values.get('username', None))
		if term:
			usernames = username_search(term)
		elif usernames:
			usernames = usernames.split(",")
		else:
			usernames = _all_user_names()

		writer.writerow( ['Username', 'Display Name', 'Email', 'Enrollment State', 'PIDM', 'Temp Match ID'] )

		for username in usernames:
			user = User.get_user(username)
			if not user or not IUser.providedBy(user):
				continue
			admin_data = IUserAdmissionData(user, None)
			if admin_data is None or not admin_data.state:
				continue

			user_admission = IUserAdmissionData(user)
			profile = IUserProfile( user )
			email = getattr(profile, 'email', None)

			user = IFriendlyNamed( user )
			display_name = user.alias or user.realname or user.username

			writer.writerow( [ 	username, display_name, email,
								user_admission.state, user_admission.PIDM,
								user_admission.tempmatchid ] )

		stream.flush()
		stream.seek(0)
		response.body_file = stream
		return response

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_courses',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter,
			 permission=nauth.ACT_MODERATE)
class CourseEntriesView(AbstractAuthenticatedView):

	def __call__(self):
		result = LocatedExternalDict()
		ou_courses = find_ou_courses()
		items = result['Items'] = []
		for course_instance in ou_courses.values():
			entry = ICourseCatalogEntry(course_instance)
			items.append(entry)
		result['Total'] = len(items)
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_urls',
			 renderer='rest',
			 request_method='GET',
			 context=JanuxPathAdapter,
			 permission=nauth.ACT_MODERATE)
class URLMapView(AbstractAuthenticatedView):

	def __call__(self):
		result = LocatedExternalDict(get_url_map())
		return result
	
@view_config(route_name='objects.generic.traversal',
			 name='fmaep_check_accounts',
			 renderer='rest',
			 request_method='POST',
			 context=JanuxPathAdapter,
			 permission=nauth.ACT_MODERATE)
class CheckAccountsView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		notify = values.get('notify', True)
		usernames = values.get('usernames')
		term = values.get('term', values.get('search', None))
		notify = is_true(notify)
		if term:
			usernames = username_search(term)
		elif usernames and isinstance(usernames, six.string_types):
			usernames = usernames.split(',')
		else:
			usernames = _all_user_names()

		fm_users = []
		for username in usernames:
			user = User.get_user(username)
			if not user or not IUser.providedBy(user):
				continue
			admin_data = IUserAdmissionData(user, None)
			if admin_data is None or not admin_data.state or not admin_data.PIDM:
				continue
			fm_users.append(user)

		result = LocatedExternalDict()
		account_status_url = get_url_map()[ACCOUNT_STATUS_URL]
		items = result['Items'] = {}
		for user in fm_users:
			logger.debug("Checking account status for %s", user)
			result = account_status(user, account_status_url=account_status_url)
			items[user.username] = result
		result['Total'] = len(items)
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_set_state',
			 renderer='rest',
			 request_method='POST',
			 context=JanuxPathAdapter,
			 permission=nauth.ACT_MODERATE)
class SetStateView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		username = values.get('username')
		new_state = values.get('state')
		notify = is_true(values.get('notify', False))

		if not safe_compare(new_state, *ADMISSION_STATES):
			raise hexc.HTTPUnprocessableEntity('Not a valid state (%s)' % new_state)

		pidm = values.get('pidm')
		tempmatchid = values.get('tempmatchid')

		user = User.get_user(username)
		if not user or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity("user not found")

		result = LocatedExternalDict()
		admin_data = IUserAdmissionData(user)
		old_state = admin_data.state
		set_user_state( user, new_state, PIDM=pidm, tempmatchid=tempmatchid, event=notify )
		new_state = admin_data.state
		result[username] = 'Updated (old=%s) (new=%s)' % (old_state, new_state)
		logger.info('Setting five minute state (user=%s) (old=%s) (new=%s) (notify=%s)',
					username, old_state, new_state, notify )
		return result

@view_config(route_name='objects.generic.traversal',
			 name='fmaep_admission_inquiry',
			 renderer='rest',
			 request_method='POST',
			 context=JanuxPathAdapter,
			 permission=nauth.ACT_MODERATE)
class AdmissionInquiryView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		username = values.get('username')
		if not username:
			raise hexc.HTTPUnprocessableEntity("must specify a username")
		user = User.get_user(username)
		if not user or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity("user not found")

		admin_data = IUserAdmissionData(user)
		tempmatchid = values.get('tempmatchid') or admin_data.tempmatchid
		if not tempmatchid:
			raise hexc.HTTPUnprocessableEntity("must specify a tempmatchid")

		notify = is_true(values.get('notify', False))
		result = query_admission(user, tempmatchid, event=notify)
		return result

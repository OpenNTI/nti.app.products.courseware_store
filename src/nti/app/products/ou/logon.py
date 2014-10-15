#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and data models relating to the login process.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

logger = __import__('logging').getLogger(__name__)

import re
import functools
import nameparser
import collections

import ldap

from datetime import datetime
from datetime import timedelta

TIMEOUT = getattr(ldap, 'TIMEOUT')
VERSION3 = getattr(ldap, 'VERSION3')
SCOPE_SUBTREE = getattr(ldap, 'SCOPE_SUBTREE')
INSUFFICIENT_ACCESS = getattr(ldap, 'INSUFFICIENT_ACCESS')
INVALID_CREDENTIALS = getattr(ldap, 'INVALID_CREDENTIALS')
OPT_PROTOCOL_VERSION = getattr(ldap, 'OPT_PROTOCOL_VERSION')

from ldappool import BackendError
from ldappool import ConnectionManager

ldap.set_option(OPT_PROTOCOL_VERSION, VERSION3)

# See also ldappool https://pypi.python.org/pypi/ldappool
# and pyramid_ldap

from zope import interface
from zope import component

from pyramid.view import view_config
from pyramid.interfaces import IRequest
from pyramid import httpexceptions as hexc

from nti.app.externalization.error import raise_json_error as _raise_error

from nti.appserver.logon import _create_failure_response
from nti.appserver.logon import _create_success_response
from nti.appserver.logon import _deal_with_external_account
from nti.appserver.logon import _SimpleExistingUserLinkProvider

from nti.appserver.interfaces import IMissingUser
from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider

from nti.dataserver.links import Link
from nti.dataserver.users import User
from nti.dataserver.users.users import _Password

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.utils import interfaces as util_interfaces

from .views import SET_RESEARCH_VIEW

from .interfaces import IOUUser
from .interfaces import IOUUserProfile
from .interfaces import IUserResearchStatus

REL_LOGIN_LDAP_OU = 'logon.ldap.ou'  # : See :func:`ou_ldap_login_view`

def _is_4x4(username):
	# Although it's called a four by four, the name portion
	# can be shorter (e.g., 'liu') and we've even seen some that
	# are longer (e.g., 'calton'). We arbitrarily require 2 to 10 letters.
	# The digit portion is always exactly
	# four, though
	return username and re.match(r'[a-zA-z]{2,10}[0-9]{4}$', username)

_ou_ldap_pool = None
def connection_pool():
	global _ou_ldap_pool
	if _ou_ldap_pool is None:
		entry = component.getUtility(util_interfaces.ILDAP, name="ou-ldap")
		pool = ConnectionManager(entry.URL, entry.Username, entry.Password, size=20,
								 retry_max=1, retry_delay=.2, use_pool=True)
		_ou_ldap_pool = pool
	return _ou_ldap_pool

def get_ldap_attr(data, name):
	result = data.get(name, None)
	if result and isinstance(result, collections.MutableSequence):
		result = result[0]
	return unicode(result) if result else None

def is_valid_ou_user(username):
	entry = component.getUtility(util_interfaces.ILDAP, name="ou-ldap")
	try:
		with connection_pool().connection(entry.Username, entry.Password) as conn:
			retrieveAttributes = None
			searchScope = SCOPE_SUBTREE
			searchFilter = "sAMAccountName=%s" % username
			__traceback_info__ = searchFilter
			result_data = conn.search_s(entry.BaseDN, searchScope, searchFilter,
										retrieveAttributes)
			return result_data
	except Exception:
		logger.exception("Failed OU check for %s" % username)
		raise

@interface.implementer(ILogonLinkProvider)
@component.adapter(IMissingUser, IRequest)
class _SimpleMissingUserOULinkProvider(object):

	rel = REL_LOGIN_LDAP_OU

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__(self):
		username = self.user.username
		if _is_4x4(username) and is_valid_ou_user(username):
			root = self.request.route_path('objects.generic.traversal', traverse=())
			if root.endswith('/'):
				# Strip a trailing slash, because Link will add one after
				# the target and before the elements, so avoid a double
				root = root[:-1]
			return Link( root,
						 elements=('@@' + self.rel,),
						 rel=self.rel)

@component.adapter(IOUUser, IRequest)
class _SimpleExistingUserOULinkProvider(_SimpleMissingUserOULinkProvider):
	"""
	The same as the superclass, but for users that exist.
	"""

class _DoNotAdvertiseSimpleLogonExistingUserLinkProvider(_SimpleExistingUserLinkProvider):
	"""
	Register this in this site to override
	the normal mechanism that detects the presence of a password on a user
	and sends them the logon rel for local password authentication (though
	it may still be possible)
	"""

	priority = 1

	def __call__(self):
		raise NotImplementedError()

# TODO: We should probably do the above for the reset/forgot passcode links too

from zope.authentication.interfaces import ILoginPassword

def save_attributes(user, soonerID, OU4x4):
	result = False
	if not IOUUser.providedBy(user):
		result = True
		interface.alsoProvides(user, IOUUser)

	if not getattr(user, 'soonerID', None) or not getattr(user, 'OU4x4', None):
		# set atts in user for legacy purposes
		setattr(user, 'OU4x4', OU4x4)
		setattr(user, 'soonerID', soonerID)

		# set values in profile
		ou_profile = IOUUserProfile(user, None)
		if ou_profile is not None:
			ou_profile.OU4x4 = OU4x4
			ou_profile.soonerID = soonerID
		result = True
	return result

@view_config(name=REL_LOGIN_LDAP_OU,
			 route_name='objects.generic.traversal',
			 request_method='GET',
			 context=IDataserverFolder)
def ldap_login_view(request):
	lpw = ILoginPassword(request)
	username = lpw.getLogin()
	password = lpw.getPassword()
	if not username:
		_raise_error(request, hexc.HTTPUnprocessableEntity,
					  {'field': 'username',
					   'message': _('Missing username'),
					   'code': 'RequiredMissing'}, None)
	if not password:
		_raise_error(request, hexc.HTTPUnprocessableEntity,
					  {'field': 'password',
					   'message': _('Missing password'),
					   'code': 'RequiredMissing'}, None)

	# TODO: Right here we were unconditionally decoding
	# username AND password to unicode strings using whatever
	# the system encoding happened to be. Why?

	try:
		result_data = _is_4x4(username) and is_valid_ou_user(username)
		if not result_data:
			raise hexc.HTTPUnauthorized()
		else:
			ldap_data = result_data[0]
			# get the CN to do a simple an ldap auth
			CN = ldap_data[0]
			# get attributes
			ldap_data = ldap_data[1] if len(ldap_data) >= 2 else {}
			with connection_pool().connection(CN, password):
				# this does a simple bind
				pass

			# make sure we always have sooner id
			soonerID = get_ldap_attr(ldap_data, 'employeeNumber')
			if soonerID is None:
				soonerID = username

			# check existing accounts
			userid = username  # initial user id
			user = User.get_entity(userid)
			if user is not None:
				stored_ouid = getattr(user, 'soonerID', soonerID)
				if stored_ouid != soonerID:
					# 4x4 has been reused. User soonerID to create new account
					user = None
					userid = soonerID
			else:
				userid = soonerID

			user = User.get_entity(userid) if user is None else user
			if user is None:
				# TODO: We probably need to be updating email addresses
				# every time, not just once on creation, as long
				# as the accounts are connected.
				email = get_ldap_attr(ldap_data, 'mail') or \
						get_ldap_attr(ldap_data, 'forwardingAddress')
				email = email or username + '@ou.edu'  # Assume ou.edu domain

				# get realname
				realname = get_ldap_attr(ldap_data, 'givenName')
				human_name = nameparser.HumanName(realname) if realname else None
				firstName = human_name.first or realname
				lastName = human_name.last or get_ldap_attr(ldap_data, 'sn')

				factory = functools.partial(User.create_user,
											meta_data={'check_4x4': False})

				user = _deal_with_external_account(	request,
													username=userid,
													fname=firstName,
													lname=lastName,
													email=email,
													idurl=None,
													iface=None,
													user_factory=factory)
				save_attributes(user, soonerID, username)

				# Our GET method, which is noramlly side-effect free,
				# had the side effect of creating the user. So make sure we
				# commit
				request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
			elif save_attributes(user, soonerID, username):
				request.environ[b'nti.request_had_transaction_side_effects'] = b'True'

			# When we get a successful ldap logon, capture the password
			# so that it can be used to derive security tokens; do this
			# each time so that if the user changes their password their
			# tokens also change. (But be smart and only do it when
			# the password actually changes, to avoid database churn.)

			# TODO: Should we capture the actual password, or permute it somehow?
			# Capturing the actual password is convenient for letting
			# testers login from the command line, and is nice if the external
			# LDAP server is down/unreachable. However, we don't want to get too far out of sync
			# and either accept or reject something we shouldn't (that's mostly a UI
			# thing though). We could use a known permutation so that testing could
			# still work, but that doesn't change anything, it's just a form of
			# security-through-obscurity...and a random permutation makes it hard
			# for us to detect when to actually change it.

			if not user.has_password() or not user.password.checkPassword(password):
				# These passwords are checked by the external authority, we
				# cannot enforce our policy on them.
				# FIXME: There's not currently a clean way
				# to completely bypass that, so we do it the nasty way :(
				user._p_changed = True
				user.__dict__['password'] = _Password( password, user.password_manager_name )
				request.environ[b'nti.request_had_transaction_side_effects'] = b'True'

			logger.debug("%s logging through LDAP", username)
			return _create_success_response(request, userid=userid, success=None)

	except INVALID_CREDENTIALS:
		logger.debug("Invalid credentials for %s", username)
		raise hexc.HTTPUnauthorized(detail="Invalid credentials for %s" % username)
	except INSUFFICIENT_ACCESS:
		logger.debug("Insufficient access for %s", username)
		raise hexc.HTTPUnauthorized(detail="Insufficient access for %s" % username)
	except TIMEOUT:
		logger.debug("LDAP request timeout for %s", username)
		raise hexc.HTTPRequestTimeout(detail="LDAP request timeout for %s" % username)
	except Exception, e:
		logger.exception("Failed OU login for %s", username)
		return _create_failure_response(request, error=str(e))

from nti.appserver.logon import REL_HANDSHAKE
from nti.appserver.excviews import EmailReportingExceptionView

@view_config(route_name=REL_HANDSHAKE, context=BackendError)
class LdapCommunicationExceptionView(EmailReportingExceptionView):
	"""
	When an LDAP exception occurs during the handshake phase,
	send an appropriate error message.
	"""

	def _do_create_response(self):
		return _create_failure_response( self.request,
										 error_factory=hexc.HTTPBadGateway,
										 error='We are unable to communicate with the OU 4x4 system.'
										 ' Please check @UofOklahoma, @OUITSolutions or @OUD2L'
										 ' for updates.')

IRB_PDF_LINK = '//d2ixlfeu83tci.cloudfront.net/images/ou_irb_agreement.pdf'
IRB_HTML_LINK = '//d2ixlfeu83tci.cloudfront.net/images/irb-agreement.html'

@interface.implementer(IAuthenticatedUserLinkProvider)
@component.adapter(IUser, IRequest)
class _UserResearchLogonLinkProvider(object):
	"""
	Add the research status links, if needed.
	"""

	def __init__(self, user, req):
		self.user = user
		self.request = req

	def _update_research_status(self):
		result = True
		research_status = IUserResearchStatus(self.user)
		last_mod = research_status.lastModified

		if last_mod is not None:
			now = datetime.utcnow()
			# This should handle leap years ok
			year_ago = now - timedelta( days=365 )
			# Do not prompt if they have updated in the past year.
			if datetime.utcfromtimestamp( last_mod ) > year_ago:
				result = False
		return result

	def get_links( self ):
		links = []
		if self._update_research_status():
			set_research_link = Link(self.user,
									 elements=(SET_RESEARCH_VIEW,),
						 			 rel=SET_RESEARCH_VIEW )

			pdf_link = Link( IRB_PDF_LINK, rel='irb_pdf' )
			html_link = Link( IRB_HTML_LINK, rel='irb_html' )

			links.append( set_research_link )
			links.append( pdf_link )
			links.append( html_link )
		return links

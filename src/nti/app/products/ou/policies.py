#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies and components that are related to OU.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.appserver import MessageFactory as _

import re

from zope import component
from zope import interface

from nti.appserver.interfaces import IUserCapabilityFilter
from nti.appserver.policies.site_policies import InvalidUsernamePattern
from nti.appserver.policies.site_policies import AdultCommunitySitePolicyEventListener

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import BlankHumanNameError

from .interfaces import IOUUser

@component.adapter(IOUUser)
@interface.implementer(IUserCapabilityFilter)
class NoChangePasswordCapabilityFilter(object):
	"""
	Removes the ability to change passwords for the ou accounts which are tied to passwords.
	"""
	def __init__(self, context=None):
		pass

	def filterCapabilities(self, capabilities):
		result = set(capabilities)
		result.discard('nti.platform.customization.can_change_password')
		return result

class OUSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``platform.ou.edu``.
	"""

	NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = 'new_user_created_ou'
	NEW_USER_CREATED_EMAIL_SUBJECT = _("Welcome to Janux")

	COM_USERNAME = 'ou.nextthought.com'
	COM_ALIAS = 'OU'
	COM_REALNAME = "The University of Oklahoma"

	def _censor_usernames(self, user):
		pass

	def user_will_create(self, user, event):
		meta_data = getattr(event, 'meta_data', None) or {}

		# check if username is a 4x4
		if 	meta_data.get('check_4x4', True) and \
			re.match('([a-zA-z]{2,4}[0-9]{4})|([0-9]{9})', user.username):
			raise InvalidUsernamePattern(
							_("The username is not allowed. Please choose another."),
							'Username', user.username, value=user.username)
		# continue w/ validation
		super(OUSitePolicyEventListener, self).user_will_create(user, event)

	def _check_realname(self, user):
		names = IFriendlyNamed(user)
		if names.realname is None or not names.realname.strip():
			raise BlankHumanNameError()
		human_name = names.realname
		names.alias = names.realname = unicode(human_name)

class JanuxSitePolicyEventListener(OUSitePolicyEventListener):
	"""
	Implements the policy for the 'janux.ou.edu'
	"""

	COM_USERNAME = 'janux.nextthought.com'
	DISPLAY_NAME = 'Janux'

class OUTestSitePolicyEventListener(OUSitePolicyEventListener):
	"""
	Implements the policy for the ou test site.
	"""
	
	COM_ALIAS = '*OU*'
	COM_USERNAME = 'ou.nextthought.com'
	COM_REALNAME = '*The University of Oklahoma*'
	DISPLAY_NAME = ''

class PerformanceSitePolicyEventListener(OUSitePolicyEventListener):
	"""
	Implements the policy for the 'performance.nextthought.com'
	"""

	COM_USERNAME = 'performance.nextthought.com'
	DISPLAY_NAME = 'Performance'

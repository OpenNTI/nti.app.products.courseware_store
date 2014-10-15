#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

from zope import interface
from zope.dublincore.interfaces import IDCTimes
from zope.interface.interfaces import IObjectEvent

from nti.dataserver.interfaces import IUser
from nti.dataserver.users.interfaces import IEmailRequiredUserProfile

from nti.schema.field import Bool
from nti.schema.field import Object
from nti.schema.field import ValidTextLine
from nti.schema.jsonschema import UI_TYPE_ONE_TIME_CHOICE
from nti.schema.jsonschema import TAG_UI_TYPE, TAG_READONLY_IN_UI

class IOUMixin(interface.Interface):
	OU4x4 = ValidTextLine(title="The OU 4x4 id", required=False)
	soonerID = ValidTextLine(title="The OU user id", required=False)

class IOUUser(IUser, IOUMixin):
	pass

class IOUUserProfile(IEmailRequiredUserProfile, IOUMixin):

	interested_in_credit = Bool(title=_("I might be interested in credit"),
								required=False,
								default=False)
	interested_in_credit.setTaggedValue(TAG_READONLY_IN_UI, True)
	interested_in_credit.setTaggedValue(TAG_UI_TYPE, UI_TYPE_ONE_TIME_CHOICE)

class IUserResearchStatus(IDCTimes):
	"""
	Holds whether the user has accepted that data that they generate may be
	used for research.
	"""
	allow_research = Bool(title="Allow research on user's activity.",
						  required=False,
						  default=False )

class IUserResearchStatusEvent(IObjectEvent):
	"""
	Sent when a user updates their research status.
	"""
	user = Object(IUser, title="The user")
	allow_research = Bool( title="User allow_research status" )

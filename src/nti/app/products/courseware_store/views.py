#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.appserver.policies.site_policy_views import make_scss_view
from nti.appserver.policies.site_policy_views import make_strings_view

StringsJsView = make_scss_view()
SiteCssView = make_strings_view()

from datetime import datetime

from zope import interface
from zope.event import notify
from zope.container.contained import Contained
from zope.interface.interfaces import ObjectEvent
from zope.traversing.interfaces import IPathAdapter

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.utils.maps import CaseInsensitiveDict

from . import JANUX

from .utils import is_true

from .interfaces import IUserResearchStatus
from .interfaces import IUserResearchStatusEvent

@interface.implementer(IPathAdapter)
class JanuxPathAdapter(Contained):

	__name__ = JANUX

	def __init__(self, context, request):
		self.context = context
		self.request = request
		self.__parent__ = context


@interface.implementer(IUserResearchStatusEvent)
class _UserResearchStatusEvent(ObjectEvent):

	def __init__(self, user, allow_research):
		super(_UserResearchStatusEvent, self).__init__(user)
		self.allow_research = allow_research

	@property
	def user(self):
		return self.object

SET_RESEARCH_VIEW = 'SetUserResearch'

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.dataserver.interfaces.IUser',
			  request_method='POST',
			  name=SET_RESEARCH_VIEW)
class UserResearchStudyView(AbstractAuthenticatedView,
							ModeledContentUploadRequestUtilsMixin ):
	"""
	Updates a user's research status.
	"""

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		allow_research = values.get('allow_research')
		allow_research = is_true(allow_research)
		user = self.request.context

		research_status = IUserResearchStatus(user)
		research_status.modified = datetime.utcnow()
		research_status.allow_research = allow_research

		logger.info('Setting research status for user (user=%s) (allow_research=%s)',
					user.username, allow_research )

		notify(_UserResearchStatusEvent(user, allow_research))
		return hexc.HTTPNoContent()

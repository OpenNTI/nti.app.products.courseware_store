#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import annotation

from nti.dataserver.users.user_profile import add_profile_fields
from nti.dataserver.users.user_profile import EmailRequiredUserProfile
from nti.dataserver.users.user_profile import COMPLETE_USER_PROFILE_KEY
from nti.dataserver.users.user_profile import EMAIL_REQUIRED_USER_PROFILE_KEY

from .interfaces import IOUUserProfile

@interface.implementer(IOUUserProfile)
class OUUserProfile(EmailRequiredUserProfile):
	soonerID = OU4x4 = None

add_profile_fields(IOUUserProfile, OUUserProfile)

# Create an annotation factory using the same key as the parent class.
# That way, if this account happens to get used in another site
# configuration, the fact that it was created with this profile
# to start with is preserved
OUUserProfileFactory = annotation.factory(OUUserProfile, 
										  EMAIL_REQUIRED_USER_PROFILE_KEY)

# Also create one for devmode using the same key that is
# used then. The email is still required, though.
# NOTE: This can have some issues if you're trying to use a production
# database in a devmode configuration; always take devmode out of your
# features file if you're using a production database.
DevmodeOUUserProfileFactory = annotation.factory(OUUserProfile, 
												 COMPLETE_USER_PROFILE_KEY)

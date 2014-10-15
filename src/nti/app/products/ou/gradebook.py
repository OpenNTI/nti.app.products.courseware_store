#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.app.products.gradebook.interfaces import IUsernameSortSubstitutionPolicy

from nti.dataserver.users import User

from .interfaces import IOUUserProfile

@interface.implementer(IUsernameSortSubstitutionPolicy)
class _OU4x4UsernameSortSubstitutionPolicy(object):
    
    def replace(self, username):
        user = User.get_entity(username)
        if user is None:
            return username
        profile  = IOUUserProfile(user, None)
        result = getattr(profile, 'OU4x4', None) or username
        return result


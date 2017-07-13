#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.ntiids.interfaces import INTIIDResolver

from nti.store.store import get_purchasable


@interface.implementer(INTIIDResolver)
class _PurchasableCourseResolver(object):

    __slots__ = ()

    def resolve(self, nttid):
        return get_purchasable(nttid)

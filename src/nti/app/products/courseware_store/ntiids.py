#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.ntiids.interfaces import INTIIDResolver

from nti.store.store import get_purchasable

logger = __import__('logging').getLogger(__name__)


@interface.implementer(INTIIDResolver)
class _PurchasableCourseResolver(object):

    __slots__ = ()

    def resolve(self, nttid):
        return get_purchasable(nttid)

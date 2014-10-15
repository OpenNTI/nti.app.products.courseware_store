#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IMS modude

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from itertools import ifilter, tee

from ..utils import get_text
from ..utils import get_fileobj

from .interfaces import STUDENT
from .interfaces import INSTRUCTOR
from .interfaces import STUDENT_ROLE
from .interfaces import INSTRUCTOR_ROLE

def isorted(iterable, comparator=None):
    """
    generator-based quicksort.

    http://code.activestate.com/recipes/280501-lazy-sorting/
    """
    iterable = iter(iterable)
    try:
        pivot = iterable.next()
    except:
        return

    comparator = comparator if comparator else lambda x, y: x < y

    a, b = tee(iterable)
    for x in isorted(ifilter(lambda x: comparator(x, pivot), a), comparator):
        yield x
    yield pivot
    for x in isorted(ifilter(lambda x: not comparator(x, pivot), b), comparator):
        yield x

def to_legacy_role(role):
    if role:
        role = role.upper()
        if role == STUDENT:
            role = STUDENT_ROLE
        elif role == INSTRUCTOR:
            role = INSTRUCTOR_ROLE
    return role
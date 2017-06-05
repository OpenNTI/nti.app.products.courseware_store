#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 4

from zope.generations.generations import SchemaManager


class _CoursewareStoreSchemaManager(SchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        super(_CoursewareStoreSchemaManager, self).__init__(
            generation=generation,
            minimum_generation=generation,
            package_name='nti.app.products.courseware_store.generations')


def evolve(context):
    pass

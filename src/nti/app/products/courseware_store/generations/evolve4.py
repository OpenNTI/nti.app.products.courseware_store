#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.app.products.courseware_store.interfaces import IPurchasableCourse
from nti.app.products.courseware_store.interfaces import IPurchasableCourseChoiceBundle

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites

generation = 4

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def _process_site(current, seen):
    with current_site(current):
        for name, purchasable in list(component.getUtilitiesFor(IPurchasableCourse)):
            if name in seen:
                continue
            seen.add(name)
            if IPurchasableCourseChoiceBundle.providedBy(purchasable):
                purchasable.__parent__ = current
            else:
                course = ICourseInstance(purchasable, None)
                if course is not None:
                    purchasable.__parent__ = course
                else:
                    purchasable.__parent__ = current


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']
    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        seen = set()
        for current in get_all_host_sites():
            _process_site(current, seen)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 4 by changing the lineage of purchasable courses
    """
    do_evolve(context)

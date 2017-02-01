#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 2

from zope import component

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.intid import IIntIds

from nti.site.hostpolicy import get_all_host_sites

from nti.store.interfaces import IPurchasable
from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IPurchasableChoiceBundle
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from nti.store.store import remove_purchasable


def iface_of_obj(node):
    for node_interface in (IPurchasableCourseChoiceBundle,
                           IPurchasableChoiceBundle,
                           IPurchasableCourse,
                           IPurchasable):  # orden matters
        if node_interface.providedBy(node):
            return node_interface
    return IPurchasable


def unregister_purchasables(intids):
    result = 0
    sites = get_all_host_sites()
    for site in sites:
        with current_site(site):
            registry = component.getSiteManager()
            for _, obj in list(component.getUtilitiesFor(IPurchasable)):
                provided = iface_of_obj(obj)
                if intids.queryId(obj) is None:
                    continue
                if remove_purchasable(registry=registry,
                                      item=obj,
                                      provided=provided):
                    result += 1
    logger.info('%s obj(s) unregistered', result)
    return result


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']
    with current_site(ds_folder):
        assert  component.getSiteManager() == ds_folder.getSiteManager(), \
                "Hooks not installed?"
        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)
        unregister_purchasables(intids)

    logger.info('nti.dataserver-courseware-store %s generation completed', 
                 generation)


def evolve(context):
    """
    Evolve to generation 2 by removing any persistent purchasable
    """
    do_evolve(context)

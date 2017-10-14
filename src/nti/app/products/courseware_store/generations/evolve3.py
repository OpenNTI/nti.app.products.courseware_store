#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict

from zope import component

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.app.products.courseware_store.purchasable import process_choice_bundle
from nti.app.products.courseware_store.purchasable import create_purchasable_from_course

from nti.app.products.courseware_store.utils import get_nti_choice_bundles

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.site.hostpolicy import get_all_host_sites

from nti.store.store import register_purchasable as store_register_purchasable

generation = 3

logger = __import__('logging').getLogger(__name__)


def register_site_purchasables(registry=None, seen=None):
    result = []
    choice_bundle_map = defaultdict(list)
    seen = set() if seen is None else seen
    catalog = component.getUtility(ICourseCatalog)
    for entry in catalog.iterCatalogEntries():
        if entry.ntiid in seen:
            continue
        seen.add(entry.ntiid)
        purchasable = create_purchasable_from_course(entry)
        if purchasable is not None:
            item = store_register_purchasable(purchasable, registry=registry)
            if item is not None:
                logger.info("Purchasable %s was registered", item.NTIID)
                result.append(item)
            # collect choice bundle data
            for name in get_nti_choice_bundles(entry):
                choice_bundle_map[name].append(purchasable)

    for name, bundle in choice_bundle_map.items():
        purchasable, _ = process_choice_bundle(name, bundle, notify=False)
        if purchasable is not None:
            item = store_register_purchasable(purchasable, registry=registry)
            if item is not None:
                result.append(item)
                logger.info("Purchasable %s was registered", item.NTIID)
    return result


def register_purchasables():
    result = []
    seen = set()
    for site in get_all_host_sites():
        with current_site(site):
            registry = site.getSiteManager()
            result.extend(register_site_purchasables(registry=registry,
                                                     seen=seen))
    return result


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"
        result = register_purchasables()
    logger.info('Generation completed, %s purchasables registered',
                generation, len(result))


def evolve(context):
    """
    Evolve to generation 3 by registering purchasables for courses
    """
    do_evolve(context)

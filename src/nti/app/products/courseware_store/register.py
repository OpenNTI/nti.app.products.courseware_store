#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import defaultdict

from zope import component
from zope import lifecycleevent

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.store.interfaces import IPurchasableCourse
from nti.store.interfaces import IPurchasableCourseChoiceBundle

from .purchasable import process_choice_bundle

from .utils import get_nti_choice_bundles

def register_choice_bundles(bundle_map, registry=component, notify=True):
	result = []
	for name, bundle in bundle_map.items():
		logger.debug("Creating purchasable bundle %s", name)
		purchasable, _ = process_choice_bundle(name, bundle, notify=notify)
		name = getattr(purchasable, 'NTIID', None)
		if name and not registry.queryUtility(IPurchasableCourseChoiceBundle, name=name):
			# TODO: Register in site manager when persistent purchasables are ready
			registry.getGlobalSiteManager().registerUtility(purchasable,
															IPurchasableCourseChoiceBundle,
															name=name)
			if notify:
				lifecycleevent.created(purchasable)
			result.append(purchasable)
			logger.debug("Purchasable choice bundle %s has been registered", name)
	return result

def register_purchasables(registry=component, notify=True):
	result = []
	choice_bundle_map = defaultdict(list)
	catalog = component.getUtility(ICourseCatalog)
	for entry in catalog.iterCatalogEntries():
		purchasable = IPurchasableCourse(entry, None)
		name = getattr(purchasable, 'NTIID', None)
		if name and registry.queryUtility(IPurchasableCourse, name=name) is None:
			# TODO: Register in site manager when persistent purchasables are ready
			registry.getGlobalSiteManager().registerUtility(purchasable, 
															IPurchasableCourse, 
															name=name)
			result.append(purchasable)
			if notify:
				lifecycleevent.created(purchasable)
			logger.debug("Purchasable %s was registered for course %s",
						 purchasable.NTIID, entry.ntiid)

			# collect choice bundle data
			for name in get_nti_choice_bundles(entry):
				choice_bundle_map[name].append(purchasable)

	choice_bundles = register_choice_bundles(choice_bundle_map, registry, notify=notify)
	result.extend(choice_bundles)
	return result

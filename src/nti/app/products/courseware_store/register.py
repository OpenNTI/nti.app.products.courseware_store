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

from .purchasable import get_state
from .purchasable import create_course_choice_bundle

from .utils import get_nti_choice_bundles

def process_choice_bundle(name, bundle, proxy=True, notify=True):
	state = None
	validated = []

	for purchasable in bundle or ():
		p_state = get_state(purchasable)
		if state is None:
			state = p_state
			validated.append(purchasable)
		elif state == p_state:
			validated.append(purchasable)
		elif notify:
			logger.warn("Purchasable %s(%s) will not be included in bundle %s",
						purchasable.NTIID, p_state, name)

	# there is something to create
	if len(validated) >= 1:
		result = create_course_choice_bundle(name, validated, proxy=proxy)
	elif notify:
		result = None
		logger.warn("Bundle %s will not be created. Not enough purchasables", name)
	return result

def register_choice_bundles(bundle_map, registry=component, notify=True):
	result = []
	for name, bundle in bundle_map.items():
		logger.debug("Creating purchasable bundle %s", name)
		purchasable = process_choice_bundle(name, bundle, notify=notify)
		name = getattr(purchasable, 'NTIID', None)
		if name and not registry.queryUtility(IPurchasableCourseChoiceBundle, name=name):
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
			# register purchasable course
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

# XXX: Persistent purchasables

from nti.store.store import register_purchasable as store_register_purchasable

from .adapters import create_purchasable_from_course

def register_site_purchasables(registry=component, seen=None):
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
				result.append(item)
			# collect choice bundle data
			for name in get_nti_choice_bundles(entry):
				choice_bundle_map[name].append(purchasable)

	for name, bundle in choice_bundle_map.items():
		purchasable = process_choice_bundle(name, bundle, notify=False, proxy=False)
		if purchasable is not None:
			item = store_register_purchasable(purchasable, registry=registry)
			if item is not None:
				result.append(item)
	return result

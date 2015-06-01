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

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.traversing.interfaces import IEtcNamespace

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.site.interfaces import IHostPolicyFolder

from nti.store.store import register_purchasable

from ..adapters import create_purchasable_from_course

from ..utils import get_nti_choice_bundles

from ..register import process_choice_bundle

generation = 2

def register_purchasables(registry):
	result = []
	choice_bundle_map = defaultdict(list)
	catalog = component.getUtility(ICourseCatalog)
	for entry in catalog.iterCatalogEntries():
		purchasable = create_purchasable_from_course(entry)
		if purchasable is not None:
			item = register_purchasable(purchasable, registry=registry)
			result.append(item)
			# collect choice bundle data
			for name in get_nti_choice_bundles(entry):
				choice_bundle_map[name].append(purchasable)

	for name, bundle in choice_bundle_map.items():
		purchasable = process_choice_bundle(name, bundle, notify=False, proxy=False)
		if purchasable is not None:
			item = register_purchasable(purchasable, registry=registry)
			result.append(item)
	return result

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']
	lsm = ds_folder.getSiteManager()		
	sites_folder = lsm.getUtility(IEtcNamespace, name='hostsites')
	for _, site in sites_folder.items():
		if not IHostPolicyFolder.providedBy(site):
			continue	
		with current_site(site):
			registry = site.getSiteManager()
			register_purchasables(registry=registry)

def evolve(context):
	"""
	Evolve to generation 2 by registering purchasables for courses
	"""
	do_evolve(context)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.site.hostpolicy import get_all_host_sites

from ..register import register_site_purchasables

generation = 2

def register():
	seen = set()
	for site in get_all_host_sites():
		with current_site(site):
			registry = site.getSiteManager()
			register_site_purchasables(registry=registry, seen=seen)

def do_evolve(context, generation=generation):
	setHooks()
	conn = context.connection
	ds_folder = conn.root()['nti.dataserver']
	with current_site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"
		register()
	logger.info('nti.dataserver-courseware-store %s generation completed', generation)

def evolve(context):
	"""
	Evolve to generation 3 by registering purchasables for courses
	"""
	do_evolve(context)

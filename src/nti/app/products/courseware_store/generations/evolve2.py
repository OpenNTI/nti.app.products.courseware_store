#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.traversing.interfaces import IEtcNamespace

from nti.site.interfaces import IHostPolicyFolder

from ..register import register_site_purchasables

generation = 2

def do_evolve(context):
	setHooks()
	seen = set()
	conn = context.connection
	ds_folder = conn.root()['nti.dataserver']
	lsm = ds_folder.getSiteManager()		
	sites_folder = lsm.getUtility(IEtcNamespace, name='hostsites')
	for _, site in sites_folder.items():
		if not IHostPolicyFolder.providedBy(site):
			continue	
		with current_site(site):
			registry = site.getSiteManager()
			register_site_purchasables(registry=registry, seen=seen)

def evolve(context):
	"""
	Evolve to generation 2 by registering purchasables for courses
	"""
	do_evolve(context)

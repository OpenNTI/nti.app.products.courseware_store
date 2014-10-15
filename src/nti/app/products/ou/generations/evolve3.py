#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 3.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 3

from zope import component
from zope.component.hooks import site, setHooks

from zope.annotation.interfaces import IAnnotations

def remove_old_annotation(user):
	annotations = IAnnotations(user, {})
	name = "nti.app.products.ou.fiveminuteaep.model.DefaultEnrollmentStorage"
	annotations.pop(name, None)

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert 	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			remove_old_annotation(user)
			
	logger.info('Generation %s completed', generation)

def evolve(context):
	"""
	Evolve to generation 3 by removing old annotation
	"""
	do_evolve(context)

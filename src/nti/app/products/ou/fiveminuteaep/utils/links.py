#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.location.interfaces import ILocation

from pyramid.traversal import find_interface

from nti.externalization.interfaces import StandardExternalFields

from nti.dataserver.links import Link
from nti.dataserver.interfaces import IDataserverFolder

from ... import JANUX

LINKS = StandardExternalFields.LINKS

def create_fmaep_link(context, name, method='POST', params=None):
	ds_folder = find_interface(context, IDataserverFolder)
	link = Link(ds_folder, rel=name.replace('_', '.'), elements=(JANUX, name),
				method=method, params=params)
	link.__name__ = link.target
	link.__parent__ = ds_folder
	interface.alsoProvides(link, ILocation)
	return link

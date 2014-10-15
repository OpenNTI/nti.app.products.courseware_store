#!/usr/bin/env python
"""
zope.generations installer for nti.app.products.ou

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

generation = 3

from zope import interface

from zope.generations.interfaces import IInstallableSchemaManager
from zope.generations.generations import SchemaManager as BaseSchemaManager

@interface.implementer(IInstallableSchemaManager)
class SchemaManager(BaseSchemaManager):
	"""
	A schema manager that we can register as a utility in ZCML.
	"""
	def __init__( self ):
		super(SchemaManager, self).__init__(
			generation=generation,
			minimum_generation=generation,
			package_name='nti.app.products.ou.generations')

	def install( self, context ):
		pass

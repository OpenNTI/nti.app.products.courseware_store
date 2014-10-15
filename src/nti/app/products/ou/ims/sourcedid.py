#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Define a sourceid object.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import interface

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import get_text

from .interfaces import ISourcedID

DEFAULT_SOURCE = ISourcedID['source'].default

@total_ordering
@EqHash('source', 'id')
@WithRepr
@interface.implementer(ISourcedID)
class SourcedID(SchemaConfigured):
	id = None
	source = None

	createDirectFieldProperties(ISourcedID)

	def __lt__(self, other):
		try:
			return (self.source, self.id) < (other.source, other.id)
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.source, self.id) > (other.source, other.id)
		except AttributeError: # pragma: no cover
			return NotImplemented
		
	@classmethod
	def createFromElement(cls, element):
		source = element.find('source')
		source = get_text(source) or DEFAULT_SOURCE

		id_ = element.find('id')
		id_ = get_text(id_)

		result = SourcedID(source=source, id=id_) if source and id_ else None
		if result is None:
			logger.debug('Skipping sourceid node %r (%s, %s)', element, source, id_)
		return result

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Define a group object.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import isodate
from functools import total_ordering

from zope import interface

from nti.externalization.representation import WithRepr
from nti.externalization.datetime import datetime_from_string

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.utils.property import alias

from . import get_text

from .sourcedid import SourcedID

from .interfaces import IGroup
from .interfaces import ITimeFrame

@interface.implementer(ITimeFrame)
@EqHash('start', 'end')
@WithRepr
class TimeFrame(SchemaConfigured):
	start = None
	end = None

	createDirectFieldProperties(ITimeFrame)

	@classmethod
	def _mktime(cls, node):
		value = get_text(node)
		if value:
			try:
				datetime = datetime_from_string(value)
			except ValueError:
				datetime = isodate.parse_date(value)
			return time.mktime(datetime.timetuple())

	@classmethod
	def createFromElement(cls, element):
		start = cls._mktime(element.find('begin'))
		end = cls._mktime(element.find('end'))
		if start is not None or end is not None:
			result = TimeFrame(start=start, end=end)
			return result

		logger.debug('Skipping timeframe node %r (%s, %s)', element, start, end)
		return None

@total_ordering
@interface.implementer(IGroup)
@EqHash('sourcedid')
@WithRepr
class Group(SchemaConfigured):
	sourcedid = None
	createDirectFieldProperties(IGroup)

	id = alias('sourcedid')

	def __lt__(self, other):
		try:
			return self.sourcedid < other.sourcedid
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return self.sourcedid > other.sourcedid
		except AttributeError:  # pragma: no cover
			return NotImplemented
		
	@classmethod
	def createFromElement(cls, element):
		sid = element.find('sourcedid')
		sid = SourcedID.createFromElement(sid) if sid is not None else None

		description = element.find('description')
		if description is not None:
			long_desc = get_text(description.find('long'))
			short_desc = get_text(description.find('short'))
			description = long_desc if long_desc else short_desc

		type_= level = None
		grouptype = element.find('grouptype')
		if grouptype is not None:
			typevalue = grouptype.find('typevalue')
			type_ = get_text(typevalue)
			level = unicode(typevalue.get('level', u'')) \
					if typevalue is not None else None

		timeframe = element.find('timeframe')
		timeframe = TimeFrame.createFromElement(timeframe) \
					if timeframe is not None else None

		result = Group(sourcedid=sid, timeframe=timeframe,
					   description=description, type=type_, level=level) \
				 if sid is not None else None

		if result is None:
			logger.debug('Skipping group node %r (%s, %s)', element, sid)
		return result

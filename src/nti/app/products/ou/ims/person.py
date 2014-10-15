#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Define a person object.

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

from nti.utils.property import alias

from . import get_text
from . import to_legacy_role

from .interfaces import IPerson
from .interfaces import IPersons

from .sourcedid import SourcedID

@total_ordering
@interface.implementer(IPerson)
@EqHash('sourcedid')
@WithRepr
class Person(SchemaConfigured):
	userid = None
	userrole = None
	sourcedid = None
	
	createDirectFieldProperties(IPerson)
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

		userid = element.find('userid')
		userid = get_text(userid)

		name = element.find('name')
		if name is not None:
			fn = name.find('fn')
			if fn is not None:
				name = get_text(fn)
			else:
				n = name.find('n')
				given = get_text(n.find('given')) if n is not None else None
				family = get_text(n.find('family')) if n is not None else None
				if given and family:
					name = "%s %s" % (given.title(), family.title())
				else:
					name = u''
		if not name:
			logger.warn("No name specified for person %s", userid)
			
		email = element.find('email')
		email = get_text(email)

		userrole = None
		extension = element.find('extension')
		if extension is not None:
			userrole = get_text(extension.find('userrole'))
			userrole = to_legacy_role(userrole)
			
		result = Person(sourcedid=sid, userid=userid,
						name=name, email=email, userrole=userrole) \
				 if sid is not None and userid else None
		if result is None:
			logger.debug('Skipping person node %r (%s, %s)', element, sid, userid)
		return result

@interface.implementer(IPersons)
class Persons(dict):

	def __init__(self):
		super(Persons, self).__init__()
		self.by_userid = {}

	def add(self, person):
		if person is not None:
			self[person.sourcedid] = person
			self.by_userid[person.userid] = person

	def get_by_userid(self, userid):
		result = self.by_userid.get(userid)
		return result

	def __delitem__(self, key):
		result = dict.__delitem__(self, key)
		if result is not None:
			self.by_userid.pop(result.userid)
		return result

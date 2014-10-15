#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Define an enterprise object.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from io import BytesIO

from lxml import etree

from zope import interface

from . import get_fileobj

from .group import Group
from .person import Person
from .person import Persons
from .membership import Membership
from .interfaces import IEnterprise

@interface.implementer(IEnterprise)
class Enterprise(object):

	def __init__(self):
		self.groups = {}
		self.memberships = {}
		self.persons = Persons()

	def add_group(self, group):
		if group is not None:
			self.groups[group.sourcedid] = group

	def get_group(self, groupid):
		result = self.groups.get(groupid)
		return result

	def get_groups(self):
		return self.groups.itervalues()

	def add_membership(self, membership):
		if membership is not None:
			self.memberships[membership.sourcedid] = membership

	def get_membership(self, groupid):
		result = self.memberships.get(groupid)
		return result

	def get_all_members(self):
		for membership in self.memberships.values():
			for member in membership:
				yield member

	def get_memberships(self):
		return self.memberships.itervalues()

	def get_person(self, sourceid):
		return self.persons.get(sourceid)

	def get_persons(self):
		return self.persons.values()

	@classmethod
	def createFromElement(cls, element):
		enterprise = Enterprise()
		for node in element.iterchildren():
			if node.tag == 'group':
				g = Group.createFromElement(node)
				enterprise.add_group(g)
			elif node.tag == 'person':
				p = Person.createFromElement(node)
				enterprise.persons.add(p)
			elif node.tag == 'membership':
				m = Membership.createFromElement(node)
				enterprise.add_membership(m)
		return enterprise

	@classmethod
	def _check(cls, enterprise):
		for m in enterprise.get_all_members():
			# set userid if mssing
			if m.userid is None:
				p = enterprise.get_person(m.sourcedid)
				if p is not None:
					m.role.userid = p.userid
				else:
					logger.warn("removing invalid membership record %s", m)
					membership = m.membership
					idx = membership.index(m)
					del membership[idx]
					
		return enterprise
	
	@classmethod
	def parse(cls, source):
		if not hasattr(source, 'read'):
			source = BytesIO(source)
		tree = etree.parse(source)
		root = tree.getroot()
		result = cls.createFromElement(root)
		return cls._check(result) if result is not None else None

	@classmethod
	def parseFile(cls, source):
		fileobj = None
		try:
			fileobj = get_fileobj(source)
			result = cls.parse(fileobj)
			return result
		finally:
			if hasattr(fileobj, 'close'):
				fileobj.close()

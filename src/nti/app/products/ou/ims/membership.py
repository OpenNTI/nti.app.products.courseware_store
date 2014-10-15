#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Define membership objects.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import interface
from zope.proxy import ProxyBase
from zope.container.contained import Contained

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.utils.property import alias

from . import get_text
from . import to_legacy_role

from .sourcedid import SourcedID

from .interfaces import IRole
from .interfaces import IMember
from .interfaces import IMembership
from .interfaces import STUDENT_ROLE
from .interfaces import ACTIVE_STATUS
from .interfaces import INSTRUCTOR_ROLE

DEFAULT_ID_TYPE = IMember['idtype'].default

@total_ordering
@interface.implementer(IRole)
@WithRepr
@EqHash('status', 'roletype', 'userid')
class Role(SchemaConfigured):
	status = None
	userid = None
	roletype = None
	createDirectFieldProperties(IRole)

	@property
	def is_student(self):
		return self.roletype == STUDENT_ROLE

	@property
	def is_instructor(self):
		return self.roletype == INSTRUCTOR_ROLE
	
	def __lt__(self, other):
		try:
			return (self.userid, self.status) < (other.userid, other.status)
		except AttributeError:  # pragma: no cover
			return NotImplemented
		
	def __gt__(self, other):
		try:
			return (self.userid, self.status) > (other.userid, other.status)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	@classmethod
	def createFromElement(cls, element):
		roletype = unicode(to_legacy_role(element.get('roletype', STUDENT_ROLE)))

		userid = element.find('userid')
		userid = get_text(userid)

		status = get_text(element.find('status'))
		status = int(status) if status else ACTIVE_STATUS

		datasource = element.find('datasource')
		datasource = get_text(datasource)

		result = Role(roletype=roletype, userid=userid, status=status, 
					  datasource=datasource)
		return result

@total_ordering
@interface.implementer(IMember)
@EqHash('sourcedid', 'idtype', 'role')
@WithRepr
class Member(Contained, SchemaConfigured):
	role = None
	idtype = None
	sourcedid = None
	createDirectFieldProperties(IMember)

	id = alias('sourcedid')

	@property
	def membership(self):
		return self.__parent__
		
	@property
	def is_student(self):
		return self.role.is_student

	@property
	def is_instructor(self):
		return self.role.is_instructor
	
	@property
	def status(self):
		return self.role.status
	
	@property
	def is_active(self):
		return self.role.status == ACTIVE_STATUS
	
	@property
	def userid(self):
		return self.role.userid

	def __lt__(self, other):
		try:
			return (self.sourcedid, self.status) < (other.sourcedid, other.status)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.sourcedid, self.status) > (other.sourcedid, other.status)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	@classmethod
	def createFromElement(cls, element):
		sid = element.find('sourcedid')
		sid = SourcedID.createFromElement(sid) if sid is not None else None

		idtype = get_text(element.find('idtype'))
		idtype = int(idtype) if idtype else DEFAULT_ID_TYPE

		role = element.find('role')
		role = Role.createFromElement(role) if role is not None else None

		result = Member(sourcedid=sid, role=role, idtype=idtype) \
				 if sid is not None and role is not None else None

		if result is None:
			logger.debug('Skipping member node %r (%s, %s)', element, sid, role)
		return result

@total_ordering
class _MemberProxy(ProxyBase):

	course_id = property(
						lambda s: s.__dict__.get('_course_id'),
						lambda s, v: s.__dict__.__setitem__('_course_id', v))
		
	def __new__(cls, base, course_id):
		return ProxyBase.__new__(cls, base)

	def __init__(self, base, course_id):
		ProxyBase.__init__(self, base)
		self.course_id = course_id

	def __lt__(self, other):
		try:
			return (self.course_id, self.sourcedid, self.status) < (other.course_id, other.sourcedid, other.status)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.course_id, self.sourcedid, self.status) > (other.course_id, other.sourcedid, other.status)
		except AttributeError:  # pragma: no cover
			return NotImplemented

@interface.implementer(IMembership)
class Membership(object):

	sourcedid = None

	def __init__(self):
		self.members = []

	id = alias('sourcedid')

	def add(self, member):
		if member is not None:
			member.__parent__ = self
			self.members.append(member)

	def __iter__(self):
		for member in self.members:
			yield _MemberProxy(member, self.sourcedid)

	def __len__(self):
		return len(self.members)

	def __getitem__(self, index):
		result = self.members[index]
		return _MemberProxy(result, self.sourcedid)
	
	def __delitem__(self, index):
		del self.members[index]

	def __contains__(self, member):
		return member in self.members
	
	def index(self, member):
		return self.members.index(member)
	
	@classmethod
	def createFromElement(cls, element):
		result = Membership()
		for e in element.iterchildren():
			if e.tag =="sourcedid":
				sid = SourcedID.createFromElement(e)
				result.sourcedid = sid
			elif e.tag == "member":
				member = Member.createFromElement(e)
				result.add(member)
		return result

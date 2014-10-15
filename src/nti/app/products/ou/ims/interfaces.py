#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OU integration IMS interfaces

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.annotation.interfaces import IAnnotatable

from dolmen.builtins import IDict
from dolmen.builtins import IIterable

from nti.schema.field import Int
from nti.schema.field import Dict
from nti.schema.field import Float
from nti.schema.field import Object
from nti.schema.field import ValidTextLine

STUDENT_ROLE = "01"
INSTRUCTOR_ROLE = "02"

STUDENT = 'STUDENT'
FACULTY = INSTRUCTOR = 'FACULTY'

ACTIVE_STATUS = 1
INACTIVE_STATUS = 0

CLASSES = 'CLASSES'

class IElementCreatable(interface.Interface):

	def createFromElement(element):
		"""
		return a instance of this object from an Element object
		"""

class ISourcedID(IAnnotatable, IElementCreatable):
	id = ValidTextLine(title='Identifier', required=True)
	source = ValidTextLine(title='Source', required=False, default='SIS')
	
class ITimeFrame(IAnnotatable, IElementCreatable):
	start = Float(title='start time', required=False)
	end = Float(title='end time', required=False)

class IGroup(IAnnotatable, IElementCreatable):
	sourcedid = Object(ISourcedID, title='Source id', required=True)
	timeframe = Object(ITimeFrame, title='Time frame', required=False)
	description = ValidTextLine(title='Group description', required=False)
	type = ValidTextLine(title='Group type', required=False)
	level = ValidTextLine(title='Group level', required=False)

class IPerson(IAnnotatable, IElementCreatable):
	sourcedid = Object(ISourcedID, title='Source id', required=True)
	userid = ValidTextLine(title='user id', required=True)
	name = ValidTextLine(title='person name', required=False)
	email = ValidTextLine(title='person email', required=False)
	userrole = ValidTextLine(title='user role type', required=False)
	
class IPersons(IAnnotatable, IDict):

	def add(person):
		"""
		add a person
		"""

	def get_by_userid(userid):
		"""
		return a IPerson w/ the specified userid
		"""

class IRole(IAnnotatable, IElementCreatable):
	userid = ValidTextLine(title='User id', required=False)
	datasource = ValidTextLine(title='Data source', required=False)
	status = Int(title='Status id', required=True, default=ACTIVE_STATUS)
	roletype = ValidTextLine(title='role type', required=True, default=STUDENT_ROLE)

class IMember(IAnnotatable, IElementCreatable):
	sourcedid = Object(ISourcedID, title='source id', required=True)
	idtype = Int(title='Id type', required=False, default=1)
	role = Object(IRole, title='Source id', required=True)

class IMembership(IAnnotatable, IElementCreatable, IIterable):
	sourcedid = Object(ISourcedID, title='source id', required=True)
	members = Dict(key_type=Object(ISourcedID), value_type=Object(IMember))
	
	def add(member):
		"""
		add a member
		"""
		
	def get(sourcedid):
		"""
		return the IMemeber with the specified id
		"""

class IEnterprise(IAnnotatable, IElementCreatable):
	persons = Object(IPersons)
	groups = Dict(key_type=Object(ISourcedID), value_type=Object(IGroup))
	membership = Dict(key_type=Object(ISourcedID), value_type=Object(IMembership))

	def get_persons():
		"""
		return all IPerson objects in this object
		"""

	def add_group(group):
		"""
		add the specified group
		"""

	def get_group(sourcedid):
		"""
		return the group w/ the specifeid id
		"""

	def get_groups():
		"""
		return all groups
		"""

	def add_membership(membership):
		""""
		add the specified membership
		"""

	def get_membership(sourcedid):
		"""
		return the membership w/ the specifeid id
		"""

	def get_memberships():
		"""
		return all membership
		"""

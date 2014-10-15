#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import os
import unittest

from nti.app.products.ou.ims.sourcedid import SourcedID
from nti.app.products.ou.ims.enterprise import Enterprise

class TestEnterprise(unittest.TestCase):

	def test_sourceid(self):
		a = SourcedID(source="SIS", id="112133307")
		assert_that(a, has_property("source", "SIS"))
		assert_that(a, has_property("id", "112133307"))
		b = SourcedID(source="SIS", id="112133307")
		c = SourcedID(source="SIS", id="112133443")
		assert_that(a, is_(b))
		assert_that(a, is_not(c))
		
	def test_parse(self):
		path = os.path.join(os.path.dirname(__file__), 'ims.xml')
		enterprise = Enterprise.parseFile(path)
		assert_that(enterprise, is_not(none()))
		assert_that(enterprise, has_property("persons", has_length(1)))
		p = enterprise.persons.get_by_userid('cald3307')
		assert_that(p, is_not(none()))
		assert_that(p, has_property('name', is_('Carlos Sanchez')))
		assert_that(p, has_property('userid', is_('cald3307')))
		assert_that(p, has_property('email', is_('maletas@ou.edu')))
		assert_that(p, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(p, has_property('sourcedid', has_property('id', is_('112133307'))))

		groups = list(enterprise.get_groups())
		assert_that(groups, has_length(1))
		group = enterprise.get_group(groups[0].sourcedid)
		assert_that(group, is_not(none()))
		assert_that(group, has_property('type', is_('CLASSES')))
		assert_that(group, has_property('level', is_('0')))
		assert_that(group, has_property('description', is_('P E-2213-001 - Thermodynamics')))
		assert_that(group, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(group, has_property('sourcedid', has_property('id', is_('18161.201120'))))
		assert_that(group, has_property('timeframe', has_property('end', is_(1338181200.0))))
		assert_that(group, has_property('timeframe', has_property('start', is_(none()))))

		memberships = list(enterprise.get_memberships())
		assert_that(memberships, has_length(1))
		membership = enterprise.get_membership(memberships[0].sourcedid)
		assert_that(membership, is_not(none()))
		assert_that(membership, has_length(1))
		assert_that(membership, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(membership, has_property('sourcedid', has_property('id', is_('18161.201120'))))

		members = list(membership)
		assert_that(members, has_length(1))
		member = membership[0]
		assert_that(member, is_not(none()))
		assert_that(member, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(member, has_property('sourcedid', has_property('id', is_('112133307'))))
		assert_that(member, has_property('role', has_property('roletype', is_('01'))))
		assert_that(member, has_property('role', has_property('status', is_(1))))
		assert_that(member, has_property('role', has_property('userid', is_('cald3307'))))

	def test_export(self):
		path = os.path.join(os.path.dirname(__file__), 'export.xml.gz')
		enterprise = Enterprise.parseFile(path)
		members = list(enterprise.get_all_members())
		assert_that(members, has_length(360))
		members = sorted(members)
		assert_that(members, has_length(360))
		assert_that(members[0], has_property('userid', is_('mcgo2121')))
		assert_that(members[-1], has_property('userid', is_('mcgu1451')))
		assert_that(members[0], has_property('course_id', is_not(none())))

	def test_sort(self):
		path = os.path.join(os.path.dirname(__file__), 'sort.xml')
		enterprise = Enterprise.parseFile(path)
		members = sorted(list(enterprise.get_all_members()))
		assert_that(members, has_length(2))
		assert_that(members[0], has_property('course_id', has_property('id', is_('18161.201120'))))
		assert_that(members[0], has_property('role', has_property('status', is_(0))))
		assert_that(members[1], has_property('course_id', has_property('id', is_('18161.201121'))))
		assert_that(members[1], has_property('role', has_property('status', is_(1))))

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

from nti.app.products.ou.ims.enterprise import Enterprise

class TestOSU(unittest.TestCase):
		
	def test_parse(self):
		path = os.path.join(os.path.dirname(__file__), 'osu.xml')
		enterprise = Enterprise.parseFile(path)
		assert_that(enterprise, is_not(none()))
		assert_that(enterprise, has_property("persons", has_length(2)))
		p = enterprise.persons.get_by_userid('jobs')
		assert_that(p, is_not(none()))
		assert_that(p, has_property('userid', is_('jobs')))
		assert_that(p, has_property('userrole', is_('02')))
		assert_that(p, has_property('name', is_('Steve Jobs')))
		assert_that(p, has_property('email', is_('sjobs@okstate.edu')))
		assert_that(p, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(p, has_property('sourcedid', has_property('id', is_('XXXXXXXX'))))
		
		p = enterprise.persons.get_by_userid('griffch')
		assert_that(p, is_not(none()))
		assert_that(p, has_property('userid', is_('griffch')))
		assert_that(p, has_property('userrole', is_('01')))
		assert_that(p, has_property('name', is_('Griffin Hemphill')))
		assert_that(p, has_property('email', is_('griffch@okstate.edu')))
		assert_that(p, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(p, has_property('sourcedid', has_property('id', is_('YYYYYYYYY'))))

		groups = list(enterprise.get_groups())
		assert_that(groups, has_length(1))
		group = enterprise.get_group(groups[0].sourcedid)
		assert_that(group, is_not(none()))
		assert_that(group, has_property('type', is_(none())))
		assert_that(group, has_property('level', is_(none())))
		assert_that(group, has_property('description', is_('BIOL1311-PRIN OF BIOL LAB-WEST HTS-SEC LAB WH3')))
		assert_that(group, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(group, has_property('sourcedid', has_property('id', is_('G_BIOL1311LAB_WH3_146'))))
		assert_that(group, has_property('timeframe', has_property('end', is_(1420264800.0))))
		assert_that(group, has_property('timeframe', has_property('start', is_(1407733200.0))))

		memberships = list(enterprise.get_memberships())
		assert_that(memberships, has_length(1))
		membership = enterprise.get_membership(memberships[0].sourcedid)
		assert_that(membership, is_not(none()))
		assert_that(membership, has_length(2))
		assert_that(membership, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(membership, has_property('sourcedid', has_property('id', is_('G_BIOL1311LAB_WH3_146'))))

		members = list(membership)
		assert_that(members, has_length(2))
		member = membership[0]
		assert_that(member, is_not(none()))
		assert_that(member, has_property('membership', is_(membership)))
		assert_that(member, has_property('sourcedid', has_property('source', is_('SIS'))))
		assert_that(member, has_property('sourcedid', has_property('id', is_('XXXXXXXX'))))
		assert_that(member, has_property('role', has_property('roletype', is_('02'))))
		assert_that(member, has_property('role', has_property('status', is_(1))))
		assert_that(member, has_property('role', has_property('userid', is_('jobs'))))

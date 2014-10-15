#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from zope import component
from zope import interface

from nti.app.products.ou.courseware.interfaces import ICoursePrice

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.app.products.ou.courseware.tests import OUCoursewareApplicationLayerTest

class TestAdapters(OUCoursewareApplicationLayerTest):

	@fudge.patch('nti.app.products.ou.courseware.adapters.get_course_details',
				 'nti.app.products.ou.courseware.adapters.get_fmaep_crn_and_term')
	def test_fmaep_course_price_finder(self, mock_details, mock_crn):
		fake_course = fudge.Fake()
		interface.alsoProvides(fake_course, ICourseInstance)
		
		mock_details.is_callable().with_args().returns(
		{
			"ID": "0123456789",
			"Name": "Algebra",
			"SeatCount": 47,
			"CRN": '13004',
			'Term': '201350',
			'Price': 100,
			'Currency': 'EUR',
			"Instructor": "Ichigo",
		})	
		mock_crn.is_callable().with_args().returns(('13004', '201350'))
		
		course_price = component.queryAdapter(fake_course, ICoursePrice, name="fmaep")
		assert_that(course_price, is_not(none()))
		assert_that(course_price, has_property(u'Amount', is_(100)))
		assert_that(course_price, has_property(u'Currency', is_('EUR')))
		
	@fudge.patch('nti.app.products.ou.courseware.adapters.get_vendor_info')
	def test_ou_course_price_finder(self, mock_vi):
		fake_course = fudge.Fake()
		interface.alsoProvides(fake_course, ICourseInstance)
		
		mock_vi.is_callable().with_args().returns(
		{
			"OU": {
				"Price":200
			}
		})
		course_price = component.queryAdapter(fake_course, ICoursePrice, name="ou")
		assert_that(course_price, is_not(none()))
		assert_that(course_price, has_property(u'Amount', is_(200)))
		assert_that(course_price, has_property(u'Currency', is_('USD')))
		
	@fudge.patch('nti.app.products.ou.courseware.adapters.get_vendor_info')
	def test_nti_course_price_finder(self, mock_vi):
		fake_course = fudge.Fake()
		interface.alsoProvides(fake_course, ICourseInstance)
		
		mock_vi.is_callable().with_args().returns(
		{
			"NTI": {
				"Purchasable":{
					'Price':300,
					'Currency':'COP'
				}
			}
		})
		course_price = component.queryAdapter(fake_course, ICoursePrice, name="nti")
		assert_that(course_price, is_not(none()))
		assert_that(course_price, has_property(u'Amount', is_(300)))
		assert_that(course_price, has_property(u'Currency', is_('COP')))
		
	@fudge.patch('nti.app.products.ou.courseware.adapters.get_vendor_info')
	def test_course_price_finder(self, mock_vi):
		fake_course = fudge.Fake()
		interface.alsoProvides(fake_course, ICourseInstance)
		
		mock_vi.is_callable().with_args().returns(
		{
			"OU":{
				'CRN':34847,
				'Term':201410
			},
			"NTI": {
				"Purchasable":{
					'Price':299.80,
					'Currency':'USD'
				}
			}
		})
		course_price = component.queryAdapter(fake_course, ICoursePrice)
		assert_that(course_price, is_not(none()))
		assert_that(course_price, has_property(u'Amount', is_(299.80)))
		assert_that(course_price, has_property(u'Currency', is_('USD')))

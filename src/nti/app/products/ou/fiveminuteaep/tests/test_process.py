#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from nti.dataserver.users import User

from nti.app.products.ou.fiveminuteaep import ADMIT_URL
from nti.app.products.ou.fiveminuteaep import IS_PAY_DONE_URL
from nti.app.products.ou.fiveminuteaep import ACCOUNT_STATUS_URL
from nti.app.products.ou.fiveminuteaep import COURSE_DETAILS_URL

from nti.app.products.ou.fiveminuteaep import get_url_map

from nti.app.products.ou.fiveminuteaep.process import is_pay_done
from nti.app.products.ou.fiveminuteaep.process import account_status
from nti.app.products.ou.fiveminuteaep.process import course_details
from nti.app.products.ou.fiveminuteaep.process import query_admission
from nti.app.products.ou.fiveminuteaep.process import process_admission

from nti.app.products.ou.fiveminuteaep.utils import get_course_key

from nti.app.products.ou.fiveminuteaep.interfaces import PENDING
from nti.app.products.ou.fiveminuteaep.interfaces import ADMITTED
from nti.app.products.ou.fiveminuteaep.interfaces import REJECTED
from nti.app.products.ou.fiveminuteaep.interfaces import IFMAEPUser
from nti.app.products.ou.fiveminuteaep.interfaces import IPaymentStorage
from nti.app.products.ou.fiveminuteaep.interfaces import IUserAdmissionData

from nti.app.products.ou.fiveminuteaep.tests import FiveMinuteAEPApplicationLayerTest

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestProcess(FiveMinuteAEPApplicationLayerTest):

	admin_data = {	'first_name': 'Jason',
					'last_name': 'Madden',
					'date_of_birth': '19820131',
					'gender': 'M',
					'street_line1': '301 David L Boren Blvd STE 3050',
					'city': 'Norman',
					'postal_code': '73072',
					'nation_code': 'United States',
					'telephone_number': '+1 (405) 514-6765',
					'email': 'jason.madden@nextthought.com',
					'social_security_number': '444555666',
					'country_of_citizenship': 'United States',
					'years_of_oklahoma_residency':20,
					'high_school_graduate':'Y',
					'attended_other_institution':'N',
					'still_attending':'N',
					'good_academic_standing':'Y',
					'bachelors_or_higher':'Y'}
			
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	def test_course_details(self, mock_rs):
		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('get').is_callable().with_args().returns_fake()
		response.has_attr(status_code=200)
		response.provides('json').is_callable().returns(
		{
    		"Status": 200,
      		"Course": {
		        "ID": "0123456789",
		        "Name": "Algebra",
		        "SeatCount": 47,
		        "Instructor": "Jub",
		        "CRN": '13004',
		        'Term': '201350'
			}
		})

		url = get_url_map()[COURSE_DETAILS_URL]
		result = course_details("13004","201350", url)
		assert_that(result, has_entry(u'Status', is_(200)))
		assert_that(result, has_entry(u'Course', has_entry('CRN', '13004')))
		assert_that(result, has_entry(u'Course', has_entry('Term', '201350')))
		assert_that(result, has_entry(u'Course', has_entry('Name', 'Algebra')))
		assert_that(result, has_entry(u'Course', has_entry('SeatCount', 47)))

	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	@WithMockDSTrans
	def test_query_admission(self, mock_rs):
		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('post').is_callable().with_args().returns_fake()
		response.has_attr(status_code=201)
		response.provides('json').is_callable().returns(
		{
    		"Status": 201,
    		"Message": 'Success',
		  	'Identifier': '12345'
		})

		user = self._create_user()
		admit_url = get_url_map()[ADMIT_URL]
		result = query_admission(user, 'foomatchid', admit_url)
		assert_that(result, has_entry('Status', 201))
		assert_that(result, has_entry('Message', 'Success'))

		admin_data = IUserAdmissionData(user)
		assert_that(admin_data, has_property('PIDM', is_('12345')))
		assert_that(admin_data, has_property('state', is_(ADMITTED)))
		assert_that(IFMAEPUser.providedBy(user), is_(True))

	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	@WithMockDSTrans
	def test_account_status(self, mock_rs):
		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('get').is_callable().with_args().returns_fake()
		response.has_attr(status_code=200)
		response.provides('json').is_callable().returns(
		{
    		"Status": 200,
    		'State': 'Admitted',
    		"Message": 'Success',
		  	'Identifier': '12345'
		})

		user = self._create_user()
		status_url = get_url_map()[ACCOUNT_STATUS_URL]
		result = account_status(user, '12345', status_url)
		assert_that(result, has_entry('Status', 200))
		assert_that(result, has_entry('Message', 'Success'))

		admin_data = IUserAdmissionData(user)
		assert_that(admin_data, has_property('PIDM', is_('12345')))
		assert_that(admin_data, has_property('state', is_(ADMITTED)))
		
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	@WithMockDSTrans
	def test_process_admission_ok(self, mock_rs):	
		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('post').is_callable().with_args().returns_fake()
		response.has_attr(status_code=201)
		response.provides('json').is_callable().returns(
		{
    		"Status": 201,
    		"Message": 'Admitted',
		  	'Identifier': '123456789'
		})
		
		user = self._create_user()
		admin_url = get_url_map()[ADMIT_URL]
		result = process_admission(user, self.admin_data, admin_url)
		assert_that(result, has_entry('Status', 201))
		assert_that(result, has_entry('Message', 'Admitted'))
		
		admin_data = IUserAdmissionData(user)
		assert_that(admin_data, has_property('PIDM', is_('123456789')))
		assert_that(admin_data, has_property('state', is_(ADMITTED)))
		assert_that(IFMAEPUser.providedBy(user), is_(True))
		
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	@WithMockDSTrans
	def test_process_admission_pending(self, mock_rs):	
		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('post').is_callable().with_args().returns_fake()
		response.has_attr(status_code=202)
		response.provides('json').is_callable().returns(
		{
    		"Status": 202,
    		"Message": 'Pending',
		  	'Identifier': 'T12345'
		})
		
		user = self._create_user()
		admin_url = get_url_map()[ADMIT_URL]
		result = process_admission(user, self.admin_data, admin_url)
		assert_that(result, has_entry('Status', 202))
		assert_that(result, has_entry('Message', 'Pending'))
		
		admin_data = IUserAdmissionData(user)
		assert_that(admin_data, has_property('PIDM', is_(none())))
		assert_that(admin_data, has_property('tempmatchid', is_('T12345')))
		assert_that(admin_data, has_property('state', is_(PENDING)))
		assert_that(IFMAEPUser.providedBy(user), is_(True))
		
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	@WithMockDSTrans
	def test_process_admission_failed(self, mock_rs):	
		
		for status_code in (400, 422, 403):
			session = mock_rs.is_callable().with_args().returns_fake()
			session.has_attr(params={})
			session.has_attr(headers={})
			response = session.provides('post').is_callable().with_args().returns_fake()
			response.has_attr(status_code=status_code)
			response.provides('json').is_callable().returns(
			{
	    		"Status": status_code,
	    		"Message": 'Failure',
			  	'Identifier': ''
			})
			
			state = REJECTED if status_code == 403 else None
			user = self._create_user(username='nt%s@nti.com' % status_code)
			admin_url = get_url_map()[ADMIT_URL]
			result = process_admission(user, self.admin_data, admin_url)
			assert_that(result, has_entry('Status', status_code))
			assert_that(result, has_entry('Message', 'Failure'))
			
			admin_data = IUserAdmissionData(user)
			assert_that(admin_data, has_property('PIDM', is_(none())))
			assert_that(admin_data, has_property('tempmatchid', is_(none())))
			assert_that(admin_data, has_property('state', is_(state)))
			assert_that(IFMAEPUser.providedBy(user), is_(False))

	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	@WithMockDSTrans
	def test_is_pay_done(self, mock_rs):	
		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('get').is_callable().with_args().returns_fake()
		response.has_attr(status_code=200)
		response.provides('json').is_callable().returns(
		{
    		"Status": 200,
    		"State": True,
		  	'MESSAGE': 'Success'
		})
		
		user = self._create_user()
		is_pay_done_url = get_url_map()[IS_PAY_DONE_URL]
		result = is_pay_done(user, "12345", '13004', '201350', is_pay_done_url)
		assert_that(result, has_entry('Status', 200))
		assert_that(result, has_entry('State', is_(True)))
		
		key = get_course_key('13004', '201350')
		pay_storage = IPaymentStorage(user)
		assert_that(pay_storage, has_key(key))

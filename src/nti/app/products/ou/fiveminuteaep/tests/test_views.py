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
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import fudge
import urllib

from nti.app.products.ou.fiveminuteaep.utils import get_course_key
from nti.app.products.ou.fiveminuteaep.utils.cypher import create_token

from nti.app.products.ou.fiveminuteaep.interfaces import IUserAdmissionData

from nti.dataserver.users import User

import nti.dataserver.tests.mock_dataserver as mock_dataserver

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges

from nti.app.products.ou.fiveminuteaep.tests import FiveMinuteAEPApplicationLayerTest

class TestViews(FiveMinuteAEPApplicationLayerTest):

	valid_admin_data =  \
		{	'first_name': 'Jason',
			'last_name': 'Madden',
			'date_of_birth': '19820131',
			'gender': 'M',
			'street_line1': '301 David L Boren Blvd STE 3050',
			'city': 'Norman',
			'state': 'Oklahoma',
			'postal_code': '73072',
			'nation_code': 'United States',
			'telephone_number': '+1 (405) 514-6765',
			'email': 'jason.madden@nextthought.com',
			'social_security_number': '444555666',
			'country_of_citizenship': 'United States',
			'years_of_oklahoma_residency':'20',
			'high_school_graduate':'Y',
			'attended_other_institution':'N',
			'is_currently_attending_ou':'N',
			'good_academic_standing':'Y',
			'bachelors_or_higher':'Y',
			'is_seeking_ou_credit': 'Y'}

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_country_names(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get('/dataserver2/janux/fmaep_country_names',
						   extra_environ=environ,
						   status=200)

		body = res.json_body
		assert_that(body, has_length(293))
		assert_that(body[0], is_('United States'))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_state_names(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get('/dataserver2/janux/fmaep_state_names',
						   extra_environ=environ,
						   status=200)

		body = res.json_body
		assert_that(body, has_length(80))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_admission_preflight(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		data = self.valid_admin_data
		testapp = TestApp(self.app)
		testapp.post_json('/dataserver2/janux/fmaep_admission_preflight', data,
				  		  extra_environ=environ,
						  status=200)

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_admission_preflight_invalid_sooner_id(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		data = self.valid_admin_data
		data['sooner_id'] = '12345678910'
		testapp = TestApp(self.app)
		testapp.post_json('/dataserver2/janux/fmaep_admission_preflight', data,
				  		  extra_environ=environ,
						  status=422)
		data.pop( 'sooner_id' )

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_admission_preflight_non_entry(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		data = self.valid_admin_data
		not_answered = ('attended_other_institution',
						'still_attending',
						'good_academic_standing',
						'bachelors_or_higher' )
		for x in not_answered:
			data.pop( x, None )
		testapp = TestApp(self.app)
		res = testapp.post_json('/dataserver2/janux/fmaep_admission_preflight', data,
				  		  extra_environ=environ,
						  status=200)
		body = res.json_body
		for x in not_answered:
			assert_that(body['Input'], has_entry( x, none()))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_admission_preflight_andrew(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		data = {'first_name': 'John',
				'middle_name': "",
				'last_name': 'Doe',
				'former-first-name': "",
				'former-last-name': "",
				'former-middle-name': "",
				'date_of_birth': '19820131',
				'gender': 'M',
				'street_line1': '1 Main St',
				'city': 'Norman',
				'state': 'Oklahoma',
				'postal_code': '73072',
				'nation_code': 'United States',
				'telephone_number': '4058765309',
				'email': 'a@b.com',
				'social_security_number': '',
				'country_of_citizenship': 'United States',
				'years_of_oklahoma_residency':'12',
				'high_school_graduate':'Y',
				'attended_other_institution':'Y',
				'still_attending':'N',
				'good_academic_standing':'1',
				'bachelors_or_higher': 'Y',
				'sooner_id':'',
				'mailing_city':'',
				'mailing_postal_code':'',
				'mailing_state':'',
				'mailing_street_line_1':'ignored',
				'mailing_street_line_2':''}

		testapp = TestApp(self.app)
		res = testapp.post_json('/dataserver2/janux/fmaep_admission_preflight', data,
				  				extra_environ=environ,
						  		status=200)
		body = res.json_body
		assert_that(body, has_key('Input'))
		assert_that(body['Input'], has_entry('years_of_oklahoma_residency', is_('12')))
		assert_that(body['Input'], has_entry('still_attending', is_('N')))
		assert_that(body['Input'], has_entry('attended_other_institution', is_('Y')))
		assert_that(body['Input'], has_entry('bachelors_or_higher', is_('Y')))
		assert_that(body['Input'], has_entry('telephone_number', is_('4058765309')))
		assert_that(body['Input'], has_entry('city', is_('Norman')))
		assert_that(body['Input'], has_entry('country_of_citizenship', is_('US')))
		assert_that(body['Input'], has_entry('date_of_birth', is_('01/31/1982')))
		assert_that(body['Input'], has_entry('email', is_('a@b.com')))
		assert_that(body['Input'], has_entry('first_name', is_('John')))
		assert_that(body['Input'], has_entry('last_name', is_('Doe')))
		assert_that(body['Input'], has_entry('gender', is_('M')))
		assert_that(body['Input'], has_entry('good_academic_standing', is_('Y')))
		assert_that(body['Input'], has_entry('high_school_graduate', is_('Y')))
		assert_that(body['Input'], has_entry('is_currently_attending_highschool', is_('N')))
		assert_that(body['Input'], has_entry('is_currently_attending_ou', is_('Y')))
		assert_that(body['Input'], has_entry('is_seeking_ou_credit', is_('Y')))
		assert_that(body['Input'], has_entry('state', is_('OK')))
		assert_that(body['Input'], has_entry('nation_code', is_('US')))
		assert_that(body['Input'], has_entry('postal_code', is_('73072')))
		assert_that(body['Input'], has_entry('street_line1', is_('1 Main St')))
		assert_that(body['Input'], has_entry('mailing_state', is_('OK')))
		assert_that(body['Input'], has_entry('mailing_nation_code', is_('US')))
		assert_that(body['Input'], has_entry('mailing_postal_code', is_('73072')))
		assert_that(body['Input'], has_entry('mailing_street_line1', is_('1 Main St')))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_admission_preflight_has_mailing_address(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		data = {'first_name': 'John',
				'middle_name': "",
				'last_name': 'Doe',
				'former-first-name': "",
				'former-last-name': "",
				'former-middle-name': "",
				'date_of_birth': '19820131',
				'gender': 'M',
				'street_line1': '1 Main St',
				'city': 'Norman',
				'state': 'Oklahoma',
				'postal_code': '73072',
				'nation_code': 'United States',
				'telephone_number': '4058765309',
				'email': 'a@b.com',
				'social_security_number': '',
				'country_of_citizenship': 'United States',
				'years_of_oklahoma_residency':'12',
				'high_school_graduate':'Y',
				'attended_other_institution':'Y',
				'still_attending':'N',
				'good_academic_standing':'1',
				'bachelors_or_higher': 'Y',
				'sooner_id':'',
				'has_mailing_address': 'True',
				'mailing_city':'',
				'mailing_postal_code':'',
				'mailing_state':'',
				'mailing_street_line_1':'ignored',
				'mailing_street_line_2':''}

		testapp = TestApp(self.app)
		# We have an incomplete mailing address.
		testapp.post_json('/dataserver2/janux/fmaep_admission_preflight', data,
				  		  extra_environ=environ,
						  status=422)

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	def test_admission_403_500(self, mock_rs):

		for status_code in (403, 500):
			session = mock_rs.is_callable().with_args().returns_fake()
			session.has_attr(params={})
			session.has_attr(headers={})
			response = session.provides('post').is_callable().with_args().returns_fake()
			response.has_attr(status_code=status_code)
			response.provides('json').is_callable().returns(
			{
	    		"Status": status_code,
	    		"Message": 'Server failure'
			})

			environ = self._make_extra_environ()
			environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

			data = self.valid_admin_data
			testapp = TestApp(self.app)
			res = testapp.post_json('/dataserver2/janux/fmaep_admission', data,
					  		  extra_environ=environ,
							  status=status_code)
			body = res.json_body
			assert_that(body, has_entry(u'Status', is_(status_code)))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session')
	def test_admission_ok(self, mock_rs):
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

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		data = self.valid_admin_data
		testapp = TestApp(self.app)
		res = testapp.post_json('/dataserver2/janux/fmaep_admission', data,
								extra_environ=environ,
						  		status=201)
		result = res.json_body
		assert_that(result, has_entry(u'Status', is_(201)))
		assert_that(result, has_entry(u'State', is_('Admitted')))
		assert_that(result, has_entry(u'Identifier', is_('12345')))
		assert_that(result, has_entry(u'Links', has_length(1)))
		assert_that(result['Links'][0], has_entry(u'rel', is_('fmaep.pay.and.enroll')))
		
	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	def test_users_status(self):
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get('/dataserver2/janux/fmaep_users_status',
						   extra_environ=environ,
						   status=200)

		assert_that(res.headers, has_entry('Content-Type', 'text/csv; charset=UTF-8'))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
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

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get('/dataserver2/janux/fmaep_course_details',
						   params={"CRN":13004, 'Term':201350},
						   extra_environ=environ,
						   status=200)

		result = res.json_body
		assert_that(result, has_entry(u'Status', is_(200)))
		assert_that(result, has_entry(u'Course', has_entry('CRN', '13004')))
		assert_that(result, has_entry(u'Course', has_entry('Term', '201350')))
		assert_that(result, has_entry(u'Course', has_entry('Name', 'Algebra')))
		assert_that(result, has_entry(u'Course', has_entry('SeatCount', 47)))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session',
				 'nti.app.products.ou.fiveminuteaep.views.find_ou_courses')
	def test_pay(self, mock_rs, mock_fc):
		course_key = get_course_key('13004', '201350')
		mock_fc.is_callable().returns({course_key: fudge.Fake('course')})

		session = mock_rs.is_callable().with_args().returns_fake()
		session.has_attr(params={})
		session.has_attr(headers={})
		response = session.provides('post').is_callable().with_args().returns_fake()
		response.has_attr(status_code=202)
		response.provides('json').is_callable().returns(
		{
    		"Status": 202,
    		"Message": 'Success',
		  	"Url" : 'https://pay.ou.edu'
		})

		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(self.extra_environ_default_user)
			IUserAdmissionData(user).PIDM = '12345'

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.post_json('/dataserver2/janux/fmaep_pay_and_enroll',
				 				{	"PIDM":'12345', "CRN":13004, 'Term':201350,
									'return_url':'http://localhost/here'},
						   		extra_environ=environ,
						   		status=202)
		result = res.json_body
		assert_that(result, has_entry(u'rel', is_('redirect')))
		assert_that(result, has_entry(u'href', 'https://pay.ou.edu'))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session',
				 'nti.app.products.ou.fiveminuteaep.process.find_ou_courses')
	def test_pay_completed(self, mock_rs, mock_fc):
		course_key = get_course_key('13004', '201350')
		mock_fc.is_callable().returns({course_key: fudge.Fake('course')})

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

		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(self.extra_environ_default_user)
			IUserAdmissionData(user).PIDM = '12345'
			token = create_token(user, '12345', 13004, 201350, 'http://return_here.com')

		params = urllib.urlencode({'username': self.extra_environ_default_user,
						 		   'token': token})
		href = '/dataserver2/janux/fmaep_payment_completed?%s' % params

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.get(href,	extra_environ=environ, status=302)
		assert_that(res, has_property('location', 'http://return_here.com?State=True'))

	@WithSharedApplicationMockDSHandleChanges(users=True, testapp=True)
	@fudge.patch('nti.app.products.ou.fiveminuteaep.process.request_session',
				 'nti.app.products.ou.fiveminuteaep.process.find_ou_courses')
	def test_is_pay_done(self, mock_rs, mock_fc):
		course_key = get_course_key('13004', '201350')
		mock_fc.is_callable().returns({course_key: fudge.Fake('course')})

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

		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(self.extra_environ_default_user)
			IUserAdmissionData(user).PIDM = '12345'

		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://platform.ou.edu'

		testapp = TestApp(self.app)
		res = testapp.post_json('/dataserver2/janux/fmaep_is_pay_done',
				 				{"PIDM":'12345', "CRN":13004, 'Term':201350},
						   		extra_environ=environ,
						   		status=200)

		result = res.json_body
		assert_that(result, has_entry('Status', 200))
		assert_that(result, has_entry('State', is_(True)))

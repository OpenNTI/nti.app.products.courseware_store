#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.utils.maps import CaseInsensitiveDict

from .utils import get_course_key
from .utils import is_fmaep_capable
from .utils import get_fmaep_crn_and_term
from .utils import crn_term_from_course_key
from .utils import get_crn_term_from_course_key

from .utils.net import DEFAULT_TIMEOUT
from .utils.net import course_details as net_course_details

from .interfaces import IURLMap
from .interfaces import ICredentials

PAY_URL = u'PAY_URL'
ADMIT_URL = u'ADMIT_URL'
IS_PAY_DONE_URL = u'IS_PAY_DONE_URL'
ACCOUNT_STATUS_URL = u'ACCOUNT_STATUS_URL'
COURSE_DETAILS_URL = u'COURSE_DETAILS_URL'
PAY_AND_ENROLL_URL = u'PAY_AND_ENROLL_URL'
ENROLLED_COURSES_URL = u'ENROLLED_COURSES_URL'

def get_credentials(name=''):
	return component.getUtility(ICredentials, name=name)

def get_url_map(name=''):
	return component.getUtility(IURLMap, name=name)

@interface.implementer(IURLMap)
def prod_urls():
	result = \
	{
		PAY_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/pay',
		ADMIT_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/admit',
		IS_PAY_DONE_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/ispaydone',
		PAY_AND_ENROLL_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/payandenroll',
		COURSE_DETAILS_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/coursedetails',
		ACCOUNT_STATUS_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/accountstatuscheck',
		ENROLLED_COURSES_URL: u'https://netapps.ou.edu/webservices/fiveminuteaep/api/enrolledcourses'
	}
	return result

@interface.implementer(IURLMap)
def test_urls():
	result = \
	{
		PAY_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/pay',
		ADMIT_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/admit',
		IS_PAY_DONE_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/ispaydone',
		PAY_AND_ENROLL_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/payandenroll',
		COURSE_DETAILS_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/coursedetails',
		ENROLLED_COURSES_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/enrolledcourses',
		ACCOUNT_STATUS_URL: u'https://dotnetdev.ou.edu/webservices/fiveminuteaep/api/accountstatuscheck'
	}
	return result

def get_course_details(crn, term, timeout=DEFAULT_TIMEOUT):
	course_details_url = get_url_map()[COURSE_DETAILS_URL]
	result = net_course_details(crn=crn, 
								term_code=term,
								course_details_url=course_details_url,
								timeout=timeout)
	result = CaseInsensitiveDict(result or {})
	result = result.get('Course', {})
	return result

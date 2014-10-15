#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import copy
import json

import ssl
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from nti.externalization.interfaces import LocatedExternalDict

from ..interfaces import STATE
from ..interfaces import FAILED
from ..interfaces import STATUS
from ..interfaces import MESSAGE

DEFAULT_TIMEOUT = 180

# TLSv1 support

class TSLSv1Adapter(HTTPAdapter):

	def init_poolmanager(self, connections, maxsize, block=False):
		self.poolmanager = PoolManager(num_pools=connections,
									   maxsize=maxsize,
									   block=block,
									   ssl_version=ssl.PROTOCOL_TLSv1)

class NetSession(Session):
	
	timeout = DEFAULT_TIMEOUT
	
	def __init__(self, timeout=DEFAULT_TIMEOUT):
		super(NetSession, self).__init__()
		self.timeout = timeout

	def request(self, *args, **kwargs):
		if kwargs.get('timeout', None) is None:
			kwargs['timeout'] = self.timeout
		return super(NetSession, self).request(*args, **kwargs)
	
def request_session(url=None, tlsv1=True, credentials=None, timeout=DEFAULT_TIMEOUT):
	result = NetSession(timeout=timeout)
	if url and url.startswith('https') and tlsv1:
		result.mount('https://', TSLSv1Adapter())
	if credentials:
		result.auth = (credentials.username, credentials.password)
	return result

def to_json(data):
	to_log = result = json.dumps(data)
	ssn_name = 'social_security_number'
	if ssn_name in data:
		data = copy.copy(data)
		data[ssn_name] = re.sub('[0-9]', 'X', data[ssn_name])
		to_log = json.dumps(data)
	logger.info('Post JSON data %s', to_log)
	return result

def response_map(response):
	try:
		result = response.json()
	except Exception:
		result = {STATE:FAILED, STATUS:response.status_code}
		result[MESSAGE] = response.text or _('Unexpected reply from server')
	## some responses do not have status
	## add it to be consistent
	if STATUS not in result:
		result[STATUS] = response.status_code
	return result

def course_details(crn, term_code, course_details_url, timeout=DEFAULT_TIMEOUT):
	session = request_session(course_details_url, timeout=timeout)
	session.params['crn'] = crn
	session.params['term_code'] = term_code
	response = session.get(course_details_url)
	logger.info("course details response status code %s", response.status_code)

	result = LocatedExternalDict()
	result.update(response_map(response))

	status = result.get(STATUS, None)
	if status >= 300:
		logger.error(result.get(MESSAGE))
	return result

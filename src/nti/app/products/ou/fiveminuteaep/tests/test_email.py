#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import not_none
from hamcrest import assert_that

import isodate
import datetime

from pyramid.renderers import render

from zope.dottedname import resolve as dottedname

from nti.app.products.ou.fiveminuteaep.tests import FiveMinuteAEPApplicationLayerTest

def _write_to_file(name, output):
	pass

class TestFiveMinuteEnrollment(FiveMinuteAEPApplicationLayerTest):

	def test_render(self):
		args = {'profile': 'profile',
				'context': 'new admittance',
				'user': 'josh zuech',
				'term': 'Fall',
				'informal_username': 'Jay Z',
				'today': isodate.date_isoformat(datetime.datetime.now()) }

		package = dottedname.resolve( 'nti.app.products.ou.fiveminuteaep.templates' )
		result = render( "fivemeap_admitted_email.pt",
						 args,
						 request=self.request,
						 package=package )
		_write_to_file( 'fme_admitted.html', result )
		assert_that( result, not_none() )

		result = render( "fivemeap_rejected_email.pt",
						 args,
						 request=self.request,
						 package=package )
		_write_to_file( 'fme_rejected.html', result )
		assert_that( result, not_none() )

		result = render( "fivemeap_pending_email.pt",
						 args,
						 request=self.request,
						 package=package )
		_write_to_file( 'fme_pending.html', result )
		assert_that( result, not_none() )

		course_args = {	'course': None,
						'instructors_html_signature': 'html sig',
						'subject': 'Welcome to OU',
						'course_start_date': datetime.datetime.utcnow() }

		args.update( course_args )

		result = render( "fivemeap_enrollment_confirmation_email.pt",
						 args,
						 request=self.request,
						 package=package )
		_write_to_file( 'fme_enrollment.html', result )
		assert_that( result, not_none() )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema import vocabulary
from zope.container.constraints import contains
from zope.container.interfaces import IContainer
from zope.container.interfaces import IContained
from zope.interface.common.mapping import IReadMapping
from zope.interface.interfaces import ObjectEvent, IObjectEvent

from nti.dataserver.interfaces import IUser

from nti.schema.field import Int
from nti.schema.field import Date
from nti.schema.field import Choice
from nti.schema.field import Object
from nti.schema.field import DateTime
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine

from .schema import Bool

STATE = u'State'
FAILED = u'Failed'
STATUS = u'Status'
MESSAGE = u'Message'

class IURLMap(IReadMapping):
	"""
	marker interface for URL maps
	"""

class ICredentials(interface.Interface):
	username = ValidTextLine(title="username", required=True)
	password = ValidTextLine(title="password", required=True)

class IFMAEPUser(interface.Interface):
	"""
	marker interface for five minute enrollment users
	"""

class IFMAEPCourse(interface.Interface):
	"""
	marker interface for five minute enrollment course
	"""

GENDER = ('M', 'F')
GENDER_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in GENDER])

ADMITTED 	 = 'Admitted'
PENDING  	 = 'Pending'
REJECTED 	 = 'Rejected'
SUSPENDED	 = 'Suspended'
ADMISSION_STATES = (ADMITTED, PENDING , SUSPENDED, REJECTED)
ADMISSION_STATE_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in ADMISSION_STATES])

class IUserAdmissionProfile(interface.Interface):
	first_name = ValidTextLine(title="First name", required=True, max_length=60)
	last_name = ValidTextLine(title="Last name", required=True, max_length=60)
	middle_name = ValidTextLine(title="Middle name", required=False, max_length=60)
	former_name = ValidTextLine(title="Former name", required=False, max_length=60)
	date_of_birth = Date(
					title='birthdate YYYYMMDD',
					description='Your date of birth.',
					required=True)
	gender = Choice(vocabulary=GENDER_VOCABULARY, title='gender', required=False)
	street_line1 = ValidTextLine(title="Street line 1", required=True, max_length=75)
	street_line2 = ValidTextLine(title="Street line 2", required=False, max_length=75)
	street_line3 = ValidTextLine(title="Street line 3", required=False, max_length=75)
	street_line4 = ValidTextLine(title="Street line 4", required=False, max_length=75)
	street_line5 = ValidTextLine(title="Street line 5", required=False, max_length=75)
	city = ValidTextLine(title="City name", required=True, max_length=50)
	state = ValidTextLine(title="State name", required=False, max_length=3)
	postal_code = ValidTextLine(title="Postal code", required=False, max_length=30)
	nation_code = ValidTextLine(title="Nation code", required=True, max_length=5)

	mailing_street_line1 = ValidTextLine(title="Mailing street line 1",
										 required=False, max_length=75)
	mailing_street_line2 = ValidTextLine(title="Mailing street line 2",
										 required=False, max_length=75)
	mailing_street_line3 = ValidTextLine(title="Mailing street line 3",
										 required=False, max_length=75)
	mailing_street_line4 = ValidTextLine(title="Mailing street line 4",
										 required=False, max_length=75)
	mailing_street_line5 = ValidTextLine(title="Mailing street line 5",
										 required=False, max_length=75)

	mailing_city = ValidTextLine(title="Mailing city name", required=True, max_length=50)
	mailing_state = ValidTextLine(title="Mailing state name", required=False, max_length=3)
	mailing_postal_code = ValidTextLine(title="Mailing postal code", required=False,
										max_length=30)
	mailing_nation_code = ValidTextLine(title="Mailing nation code", required=True,
										max_length=5)

	telephone_number = ValidTextLine(title="Mailing nation code", required=False,
									 max_length=128)

	email = ValidTextLine(title="Email", required=True, max_length=128)
	social_security_number = ValidTextLine(title="Social security", required=False,
										   max_length=9, min_length=9)

	sooner_id = ValidTextLine(title="Sooner ID", required=False, max_length=9)
	country_of_citizenship = ValidTextLine(title="Country of citizenship",
										   required=True, max_length=20)

	years_of_oklahoma_residency = ValidTextLine(title="Years of Oklahoma Residency",
									  			required=True, default='0', max_length=10)

	high_school_graduate = Bool(title="High School Graduate", required=True)

	attended_other_institution = Bool(title="Attended other institution", required=False)

	still_attending = Bool(title="Still attending", required=False)

	good_academic_standing = Bool(title="Good academic standing", required=False)

	bachelors_or_higher = Bool(title="Bachelors or higher", required=False)

	is_seeking_ou_credit = Bool(title="Is seeking OU Credit", required=True)

	is_currently_attending_ou = Bool(title="Is currently attending OU", required=True)

	is_currently_attending_highschool = Bool(title="Is currently attending highschool",
						   	    	 		 required=False)

class IUserAdmissionData(interface.Interface):
	state = Choice(vocabulary=ADMISSION_STATE_VOCABULARY, title='admission state',
				   required=False, default=None)
	PIDM = ValidTextLine(title="PIDM number", required=False, default=None)
	tempmatchid = ValidTextLine(title="tempid", required=False, max_length=10)

	def is_pending():
		"""
		return if the state is pending
		"""

	def is_suspended():
		"""
		return if the state is suspende
		"""

	def is_admitted():
		"""
		return if the state is admitted
		"""

SUCCESS = 'Success'
PURCHASE_STATES = (SUCCESS, PENDING)
PURCHASE_STATE_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in PURCHASE_STATES])

class IPaymentRecord(IContained):
	state = Choice(vocabulary=PURCHASE_STATE_VOCABULARY, title='state', required=True)
	started =  DateTime(title='start date', required=True)
	completed =  DateTime(title='completed date', required=False)
	payURL = ValidTextLine(title='pay URL', required=False)
	attempts = Int(title='payment attempts', required=False, default=0)
	
	def is_pending():
		"""
		return if the state of this purchase is pending
		"""

	def is_success():
		"""
		return if the state of this purchase is success
		"""

class IPaymentStorage(IContainer, IContained):
	"""
	purchase storage
	"""
	contains(b'.IPaymentRecord')


class IEnrollmentStorage(IContainer, IContained):
	"""
	enrollment storage.

	This is to mark a user has enrolled using the OU enrollment api but
	no payment has been made. THIS IS NOT the NextThought enrollment storage
	"""

class IUserAdmisionEvent(IObjectEvent):
	user = Object(IUser, title="The admitted user")
	message = ValidText(title="admission message", required=False)

class IUserAdmittedEvent(IUserAdmisionEvent):
	pass

class IUserRejectedEvent(IUserAdmisionEvent):
	pass

class IUserAdmisionPendingEvent(IUserAdmisionEvent):
	pass

class IUserAdmisionSuspendedEvent(IUserAdmisionEvent):
	pass

@interface.implementer(IUserAdmisionEvent)
class UserAdmisionEvent(ObjectEvent):

	def __init__(self, user, message=None):
		super(UserAdmisionEvent, self).__init__(user)
		self.message = message

	@property
	def user(self):
		return self.object

@interface.implementer(IUserAdmittedEvent)
class UserAdmittedEvent(UserAdmisionEvent):
	pass

@interface.implementer(IUserRejectedEvent)
class UserRejectedEvent(UserAdmisionEvent):
	pass

@interface.implementer(IUserAdmisionPendingEvent)
class UserAdmisionPendingEvent(UserAdmisionEvent):
	pass

@interface.implementer(IUserAdmisionSuspendedEvent)
class UserAdmisionSuspendedvent(UserAdmisionEvent):
	pass
UserAdmisionRejectedEvent = UserRejectedEvent # alias

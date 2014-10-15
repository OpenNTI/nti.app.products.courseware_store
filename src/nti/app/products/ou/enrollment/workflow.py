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

from zope import lifecycleevent
from zope.traversing.api import traverse

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistory

from nti.contenttypes.courses.interfaces import ES_PUBLIC
from nti.contenttypes.courses.interfaces import ES_CREDIT_DEGREE

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseSubInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import INonPublicCourseInstance
from nti.contenttypes.courses.interfaces import ICourseInstanceVendorInfo

from nti.dataserver import users

from nti.externalization.interfaces import LocatedExternalDict

from ..ims.enterprise import Enterprise
from ..ims.interfaces import IEnterprise
from ..ims.interfaces import ACTIVE_STATUS
from ..ims.interfaces import INACTIVE_STATUS

from .. interfaces import IOUUser
from .. interfaces import IOUUserProfile

from pyramid.compat import is_nonstr_iter

def get_person_email(person, is_ou=True):
	username = person.userid
	if person.email:
		result = person.email
	else:
		result = username + ('@ou.edu' if is_ou else '@example.com')
		logger.warn('%s does not have an email. Defaulting to %s', username, result)

	result = result.lower()
	if result.endswith('@nextthought.com'):
		result = result[:-15] + ('ou.edu' if is_ou else 'example.com')
	return result

def save_attributes(user, soonerID, OU4x4):
	if not IOUUser.providedBy(user):
		interface.alsoProvides(user, IOUUser)

	if not getattr(user, 'soonerID', None) or not getattr(user, 'OU4x4', None):
		setattr(user, 'OU4x4', OU4x4)
		setattr(user, 'soonerID', soonerID)
		ou_profile = IOUUserProfile(user, None)
		if ou_profile is not None:
			ou_profile.OU4x4 = OU4x4
			ou_profile.soonerID = soonerID

def create_users(source, is_ou=True):
	result = {}
	ims = source if IEnterprise.providedBy(source) \
		  else Enterprise.parseFile(source)

	for person in ims.get_persons():
		soonerID = person.sourcedid.id
		OU4x4 = userid = username = person.userid.lower()
		if username.endswith('@nextthought.com'):
			OU4x4 = userid = username = username[:-16]

		email = get_person_email(person, is_ou)
		user = users.User.get_user(username)
		if user is not None:
			stored_ouid = getattr(user, 'soonerID', soonerID)
			if stored_ouid != soonerID:
				user = None
				userid = soonerID
		else:
			userid = soonerID

		user = users.User.get_user(userid) if user is None else user
		if user is None:
			args = {'username': userid}
			ext_value = {'email': email}
			if person.name:
				ext_value['realname'] = person.name
			args['external_value'] = ext_value
			args['meta_data'] = {'check_4x4': False}
			user = users.User.create_user(**args)
			if is_ou:
				save_attributes(user, soonerID, OU4x4)
			result[username] = soonerID
		elif is_ou:
			save_attributes(user, soonerID, OU4x4)

	return result

def find_ou_courses():
	"""
	Look through the course catalog for courses
	marked with the OU vendor info and having a
	'IMS/sourcedid' value. This value can either be a
	single string, or a list of strings.

	:return: A dictionary for all such courses
		from 'sourcedid' to instance.
	"""
	result = dict()

	catalog = component.getUtility(ICourseCatalog)
	for catalog_entry in catalog.iterCatalogEntries():
		course_instance = ICourseInstance(catalog_entry)
		course_vendor_info = ICourseInstanceVendorInfo(course_instance, {})

		sourcedid = traverse(course_vendor_info, 'OU/IMS/sourcedid', default=None)
		if not sourcedid:
			continue
		# Yay, got one!

		sourcedids = sourcedid if is_nonstr_iter(sourcedid) else [sourcedid]

		logger.info("Mapping course instance %s to ids %s",
					catalog_entry.ProviderUniqueID, sourcedids)

		for sourcedid in sourcedids:
			if sourcedid in result: # pragma: no cover
				raise KeyError("Duplicate sourcedids!", course_instance, result[sourcedid])

			result[sourcedid] = course_instance

	return result

def is_there_an_open_enrollment(course, user):
	if ICourseSubInstance.providedBy(course):
		main_course = course.__parent__.__parent__
	else:
		main_course = course

	universe = [main_course] + list(main_course.SubInstances.values())
	for instance in universe:
		enrollments = ICourseEnrollments(instance)
		record = enrollments.get_enrollment_for_principal(user)
		if record is not None and record.Scope == ES_PUBLIC:
			return True
	return False

def has_assigments_submitted(course, user):
	histories = component.queryMultiAdapter((course, user),
											IUsersCourseAssignmentHistory )
	return histories and len(histories) > 0

def drop_any_other_enrollments(course, user):
	course_entry = ICourseCatalogEntry(course)
	course_ntiid = course_entry.ntiid

	if ICourseSubInstance.providedBy(course):
		main_course = course.__parent__.__parent__
	else:
		main_course = course

	result = []
	universe = [main_course] + list(main_course.SubInstances.values())
	for instance in universe:
		instance_entry = ICourseCatalogEntry(instance)
		if course_ntiid == instance_entry.ntiid:
			continue
		enrollments = ICourseEnrollments(instance)
		record = enrollments.get_enrollment_for_principal(user)
		if record is not None:
			enrollment_manager = ICourseEnrollmentManager(instance)
			enrollment_manager.drop(user)
			logger.warn("User %s dropped from course '%s' enrollment", user,
						instance_entry.ProviderUniqueID)
			
			if has_assigments_submitted(course, user):
				logger.warn("User %s has submitted to course '%s'", user, 
							instance_entry.ProviderUniqueID)
				
			result.append(instance_entry)
	return result

def _update_member_enrollment_status(course_instance, person, role,
									 enrrollment_info=None, move_info=None, 
									 drop_info=None):
	userid = person.userid
	soonerID = person.sourcedid.id
	user = users.User.get_user(soonerID) or users.User.get_user(userid)
	if user is None:
		logger.warn("User (%s,%s) was not found", userid, soonerID)
		return

	move_info = {} if move_info is None else move_info
	drop_info = {} if drop_info is None else drop_info
	enrrollment_info = {} if enrrollment_info is None else enrrollment_info
	
	enrollments = ICourseEnrollments(course_instance)
	enrollment_manager = ICourseEnrollmentManager(course_instance)
	enrollment = enrollments.get_enrollment_for_principal(user)
	
	instance_entry = ICourseCatalogEntry(course_instance)

	if role.status == ACTIVE_STATUS:
		
		# check any other enrollment
		for entry in drop_any_other_enrollments(course_instance, user):
			drop_info.setdefault(entry.ProviderUniqueID, {})
			drop_info[entry.ProviderUniqueID][userid] = soonerID
		
		add_mod = True
		# The user should be enrolled for degree-seeking credit.
		if enrollment is None:
			# Never before been enrolled
			logger.info('User %s enrolled in %s', user, instance_entry.ProviderUniqueID)
			enrollment_manager.enroll(user, scope=ES_CREDIT_DEGREE)
		elif enrollment.Scope != ES_CREDIT_DEGREE:
			logger.info('User %s upgraded to ForCredit in %s',
						user, instance_entry.ProviderUniqueID)
			enrollment.Scope = ES_CREDIT_DEGREE
			lifecycleevent.modified(enrollment)
		else:
			add_mod = False
			
		# record enrollment
		if add_mod:
			enrrollment_info.setdefault(instance_entry.ProviderUniqueID, {})
			enrrollment_info[instance_entry.ProviderUniqueID][userid] = soonerID
	elif role.status == INACTIVE_STATUS:
		# if enrolled but the course is not public then drop it
		if enrollment is not None:

			if INonPublicCourseInstance.providedBy(course_instance):
				logger.info('User %s dropping course %s',
							user, instance_entry.ProviderUniqueID)
				enrollment_manager.drop(user)
				
				# record drop
				drop_info.setdefault(instance_entry.ProviderUniqueID, {})
				drop_info[instance_entry.ProviderUniqueID][userid] = soonerID
				
			elif enrollment.Scope != ES_PUBLIC:
				logger.info('User %s moving to PUBLIC version of %s',
							user, instance_entry.ProviderUniqueID)
				# The user should not be enrolled for degree-seeking credit,
				# but if they were already enrolled they should remain
				# as publically enrolled
				enrollment.Scope = ES_PUBLIC
				lifecycleevent.modified(enrollment)
				
				# record move
				move_info.setdefault(instance_entry.ProviderUniqueID, {})
				move_info[instance_entry.ProviderUniqueID][userid] = soonerID

		# set in an open enrollment
		if 	enrollment is not None and enrollment.Scope != ES_PUBLIC and \
			not is_there_an_open_enrollment(course_instance, user):
			open_course = course_instance
			
			# if section and non public get main course
			if 	ICourseSubInstance.providedBy(course_instance) and \
				INonPublicCourseInstance.providedBy(course_instance):
				open_course = course_instance.__parent__.__parent__
				
			# do open enrollment
			if not INonPublicCourseInstance.providedBy(open_course):
				enrollments = ICourseEnrollments(open_course)
				enrollment = enrollments.get_enrollment_for_principal(user)
				if enrollment is None:
					enrollment_manager = ICourseEnrollmentManager(open_course)
					enrollment_manager.enroll(user, scope=ES_PUBLIC)
					
					# log public enrollment
					entry = ICourseCatalogEntry(open_course)
					logger.info('User %s enolled to PUBLIC version of %s',
								user, entry.ProviderUniqueID)
					
					# record
					enrrollment_info.setdefault(entry.ProviderUniqueID, {})
					enrrollment_info[entry.ProviderUniqueID][userid] = soonerID
	else:
		raise NotImplementedError("Unknown status", role.status)

def cmp_proxy(x, y):
	result = cmp((x.course_id, x.sourcedid), (y.course_id, y.sourcedid))
	if result == 0:
		x_sort_status = 0 if x.is_active else 1
		y_sort_status = 0 if y.is_active else 1
		result = cmp(x_sort_status, y_sort_status)
	return result

def process(ims_file, create_persons=False, is_ou=True):
	# check for the old calling convention
	assert isinstance(create_persons, bool)
	ims = Enterprise.parseFile(ims_file)
	ou_courses = find_ou_courses()

	created_users = create_users(ims, is_ou) if create_persons else ()

	warns = set()
	moves = LocatedExternalDict()
	drops = LocatedExternalDict()
	errollment = LocatedExternalDict()
	# sort members (drops come first)
	members = sorted(ims.get_all_members(), cmp=cmp_proxy)
	for member in members:
		person = ims.get_person(member.id)
		if person is None:
			logger.warn("Person definition for %s was not found", member.id)
			continue

		# Instructors should be auto-created.
		if member.is_instructor:
			continue

		course_id = member.course_id.id
		course_instance = ou_courses.get(member.course_id.id)
		if course_instance is None:
			if course_id not in warns:
				warns.add(course_id)
				logger.warn("Course definition for %s was not found", course_id)
			continue

		_update_member_enrollment_status(course_instance, person, member.role,
										 errollment, moves, drops)

	result = LocatedExternalDict()
	result['Drops'] = drops
	result['Moves'] = moves
	result['Enrollment'] = errollment
	result['CreatedUsers'] = created_users
	return result

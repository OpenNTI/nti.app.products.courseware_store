#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import csv
import six

from io import BytesIO

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import site as current_site

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.courseware.views import CourseAdminPathAdapter

from nti.app.products.courseware_store import MessageFactory as _

from nti.app.products.courseware_store.interfaces import IPurchasableCourse

from nti.app.products.courseware_store.model import create_course

from nti.app.products.courseware_store.purchasable import get_registered_choice_bundles
from nti.app.products.courseware_store.purchasable import sync_purchasable_course_choice_bundles

from nti.app.products.courseware_store.utils import find_catalog_entry
from nti.app.products.courseware_store.utils import has_store_connect_keys
from nti.app.products.courseware_store.utils import can_edit_course_purchasable
from nti.app.products.courseware_store.utils import get_course_purchasable_ntiid
from nti.app.products.courseware_store.utils import find_allow_vendor_updates_purchases
from nti.app.products.courseware_store.utils import can_course_have_editable_purchasable

from nti.app.store.interfaces import IPurchasableDefaultFieldProvider

from nti.app.store.license_utils import can_create_purchasable

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.hostpolicy import get_host_site

from nti.site.site import get_component_hierarchy_names

from nti.store.store import register_purchasable

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


def _tx_string(s):
    if s and isinstance(s, six.text_type):
        s = s.encode('utf-8')
    return s


def _parse_course(params):
    ntiid = params.get('ntiid') or params.get('course')
    entry = find_catalog_entry(ntiid) if ntiid else None
    return entry


@view_config(context=CourseAdminPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               name='VendorUpdatesPurchasedCourse')
class VendorUpdatesPurchasedCourseView(AbstractAuthenticatedView):

    def __call__(self):
        params = CaseInsensitiveDict(self.request.params)
        entry = _parse_course(params)
        if entry is None:
            msg = _(u'Course not found or specified.')
            raise hexc.HTTPUnprocessableEntity(msg)

        bio = BytesIO()
        csv_writer = csv.writer(bio)

        # header
        header = ['username', 'name', 'email']
        csv_writer.writerow(header)

        purchases = find_allow_vendor_updates_purchases(entry)
        for purchase in purchases or ():
            profile = purchase.Profile
            creator = purchase.creator
            username = getattr(creator, 'username', creator)
            email = getattr(profile, 'email', None)
            name = getattr(profile, 'realname', None) or username
            # write data
            row_data = [username, name, email]
            csv_writer.writerow([_tx_string(x) for x in row_data])

        response = self.request.response
        response.body = bio.getvalue()
        response.content_disposition = 'attachment; filename="updates.csv"'
        return response


@view_config(context=CourseAdminPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               name='SyncPurchasableCourseChoiceBundles')
class SyncPurchasableCourseChoiceBundlesView(AbstractAuthenticatedView):

    def __call__(self):
        # sync in all hierarchy sites
        for name in get_component_hierarchy_names():
            site = get_host_site(name)
            with current_site(site):
                sync_purchasable_course_choice_bundles()
        result = LocatedExternalDict()
        bundles = get_registered_choice_bundles()
        items = result[ITEMS] = list(bundles.values())
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(context=ICourseInstance)
@view_config(context=ICourseCatalogEntry)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name='CreateCoursePurchasable')
class CreateCoursePurchasableView(AbstractAuthenticatedView,
                                  ModeledContentUploadRequestUtilsMixin):
    """
    Creates a course purchasable
    """

    VALID_FIELDS = ('Currency', 'Provider', 'Amount')

    @Lazy
    def _course(self):
        return ICourseInstance(self.context)

    @Lazy
    def _catalog_entry(self):
        return ICourseCatalogEntry(self.context)

    def readInput(self, value=None):
        result = super(CreateCoursePurchasableView, self).readInput(value)
        result = CaseInsensitiveDict(result)
        # Sanitize; no fee edits unless NT admin
        valid_fields = self.VALID_FIELDS
        if is_admin(self.remoteUser):
            valid_fields = valid_fields + ('Fee',)
        for key in tuple(result):
            if key not in valid_fields:
                result.pop(key, None)
        return result

    def create_purchasable(self):
        entry = self._catalog_entry
        ntiid = get_course_purchasable_ntiid(entry)
        # Use the default fields; will be overridden by user input later.
        default_fields = component.getUtility(IPurchasableDefaultFieldProvider)
        result = create_course(ntiid=ntiid,
                               items=(entry.ntiid,),
                               name=entry.title,
                               title=entry.title,
                               provider=default_fields.get_default_provider(),
                               fee=default_fields.get_default_fee(),
                               currency=default_fields.get_default_currency(),
                               description=entry.description)
        return result

    def validate(self):
        purchasable = IPurchasableCourse(self._catalog_entry, None)
        if purchasable is not None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"This course is already purchasable"),
                                'field': 'CourseAlreadyPurchasableError'
                             },
                             None)
        if not has_store_connect_keys():
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Cannot make purchasable without connect key.'),
                             },
                             None)
        if not can_edit_course_purchasable(self._course, self.remoteUser):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'message': _(u'Not an admin or instructor.'),
                             },
                             None)
        if not can_course_have_editable_purchasable(self._course):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"This course is already purchasable"),
                                'field': 'CourseAlreadyPurchasableError'
                             },
                             None)

        if not can_create_purchasable():
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u"This site can create purchasables."),
                                'field': 'SiteLicenseRestrictionError'
                             },
                             None)

    def __call__(self):
        self.validate()
        externalValue = self.readInput()
        result = self.create_purchasable()
        self.updateContentObject(result, externalValue)
        lifecycleevent.created(result)
        register_purchasable(result)
        result.__parent__ = self._course
        return result


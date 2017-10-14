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

from zope.component.hooks import site as current_site

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware.views import CourseAdminPathAdapter

from nti.app.products.courseware_store import MessageFactory as _

from nti.app.products.courseware_store.purchasable import get_registered_choice_bundles
from nti.app.products.courseware_store.purchasable import sync_purchasable_course_choice_bundles

from nti.app.products.courseware_store.utils import find_catalog_entry
from nti.app.products.courseware_store.utils import find_allow_vendor_updates_purchases

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.hostpolicy import get_host_site

from nti.site.site import get_component_hierarchy_names

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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from pyramid.interfaces import IRequest

from nti.app.products.courseware.interfaces import IEnrollmentOption

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.store.interfaces import IPurchasableCourse

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine


class ICoursePrice(interface.Interface):

    Amount = Number(title=u"The price amount", required=True)

    Currency = ValidTextLine(title=u"The currency",
                             required=False,
                             default=u'USD')


class ICoursePriceFinder(interface.Interface):
    """
    marker interface for a course price finder
    """


class IStoreEnrollmentOption(IEnrollmentOption):

    IsEnabled = Bool(title=u"Is enabled flag",
                     required=False,
                     default=True)

    Purchasables = ListOrTuple(Object(IPurchasableCourse),
                               title=u"Purchasable course",
                               required=True,
                               min_length=1)

    AllowVendorUpdates = Bool(title=u"Allow vendor updates",
                              required=False,
                              default=False)


class IStoreEnrollmentEvent(IObjectEvent):

    request = Object(IRequest, title=u"the request", required=False)

    purchasable = Object(IPurchasableCourse,
                         title=u"purchasable course",
                         required=False)

    record = Object(ICourseInstanceEnrollmentRecord,
                    title=u"enrollemnt record",
                    required=True)


@interface.implementer(IStoreEnrollmentEvent)
class StoreEnrollmentEvent(ObjectEvent):

    def __init__(self, record, purchasable=None, request=None):
        ObjectEvent.__init__(self, record)
        self.request = request
        self.purchasable = purchasable
    
    @property
    def record(self):
        return self.object


import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecated(
    "Import from nti.app.products.courseware.interfaces instead",
    ICoursePublishableVendorInfo='nti.app.products.courseware.interfaces:ICoursePublishableVendorInfo',
    get_course_publishable_vendor_info='nti.app.products.courseware.interfaces:get_course_publishable_vendor_info')

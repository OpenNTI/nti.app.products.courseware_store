#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface
from zope import deferredimport

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from pyramid.interfaces import IRequest

from nti.app.products.courseware.interfaces import IEnrollmentOption

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.store.interfaces import IPrice
from nti.store.interfaces import IPurchasable
from nti.store.interfaces import IPurchasableVendorInfo
from nti.store.interfaces import IPurchasableChoiceBundle

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Datetime
from nti.schema.field import Timedelta
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable


class ICoursePrice(IPrice):
    pass


class ICoursePriceFinder(interface.Interface):
    """
    marker interface for a course price finder
    """


class IPurchasableCourse(IPurchasable):

    Name = ValidTextLine(title=u'Course Name', 
                         required=False)

    # overrides
    Amount = Number(title=u"Cost amount",
                    required=False,
                    min=0.0,
                    default=0.0)

    Provider = ValidTextLine(title=u'Course provider',
                             required=False)

    # Deprecated/Legacy fields
    Featured = Bool(title=u'Featured flag',
                    required=False,
                    default=False)

    Preview = Bool(title=u'Course preview flag',
                   required=False)

    StartDate = ValidTextLine(title=u"Course start date",
                              required=False)

    Department = ValidTextLine(title=u'Course Department',
                               required=False)

    Signature = ValidText(title=u'Course/Professor Signature',
                          required=False)

    Communities = UniqueIterable(value_type=ValidTextLine(title=u'The community identifier'),
                                 title=u"Communities", 
                                 required=False)

    Duration = Timedelta(title=u"The length of the course",
                         description=u"Currently optional, may be None",
                         required=False)

    EndDate = Datetime(title=u"The date on which the course ends",
                       required=False)

    # For purchaseables, we want to share this.
    VendorInfo = Object(IPurchasableVendorInfo,
                        title=u"vendor info", 
                        required=False)
    VendorInfo.setTaggedValue('_ext_excluded_out', False)
ICourse = IPurchasableCourse  # alias BWC


class IPurchasableCourseChoiceBundle(IPurchasableChoiceBundle,
                                     IPurchasableCourse):
    pass


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



deferredimport.initialize()
deferredimport.deprecated(
    "Import from nti.app.products.courseware.interfaces instead",
    ICoursePublishableVendorInfo='nti.app.products.courseware.interfaces:ICoursePublishableVendorInfo',
    get_course_publishable_vendor_info='nti.app.products.courseware.interfaces:get_course_publishable_vendor_info')

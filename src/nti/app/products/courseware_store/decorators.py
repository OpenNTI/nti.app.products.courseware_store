#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.location.interfaces import ILocation

from nti.app.authentication import get_remote_user

from nti.app.products.courseware.utils import get_vendor_thank_you_page

from nti.app.products.courseware_store.interfaces import IPurchasableCourse
from nti.app.products.courseware_store.interfaces import IStoreEnrollmentOption

from nti.app.products.courseware_store.utils import has_default_store_key
from nti.app.products.courseware_store.utils import can_edit_course_purchasable
from nti.app.products.courseware_store.utils import can_course_have_editable_purchasable

from nti.app.renderers.decorators import AbstractRequestAwareDecorator
from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.app.store.license_utils import can_create_purchasable

from nti.appserver.pyramid_renderers_edit_link_decorator import EditLinkRemoverDecorator

from nti.contenttypes.courses.interfaces import ES_PUBLIC
from nti.contenttypes.courses.interfaces import ES_PURCHASED
from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import get_catalog_entry
from nti.contenttypes.courses.utils import get_enrollment_record

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import Singleton

from nti.links.links import Link

from nti.store.interfaces import IGiftPurchaseAttempt

from nti.store.purchasable import get_purchasable

logger = __import__('logging').getLogger(__name__)

LINKS = StandardExternalFields.LINKS


@component.adapter(IStoreEnrollmentOption)
@interface.implementer(IExternalObjectDecorator)
class _StoreEnrollmentOptionDecorator(AbstractRequestAwareDecorator):

    @classmethod
    def _get_enrollment_record(cls, context):
        remote_user = get_remote_user()
        if remote_user is not None:
            entry = get_catalog_entry(context.CatalogEntryNTIID)
            return get_enrollment_record(entry, remote_user)
        return None

    def _do_decorate_external(self, context, result):
        record = self._get_enrollment_record(context)
        result['IsEnrolled'] = bool(    record is not None
                                    and record.Scope == ES_PURCHASED)
        isAvailable = bool((    record is None or record.Scope == ES_PUBLIC) \
                            and context.IsEnabled)
        result['Enabled'] = result['IsAvailable'] = isAvailable  # alias property
        result.pop('IsEnabled', None)  # redundant


@component.adapter(IGiftPurchaseAttempt)
@interface.implementer(IExternalMappingDecorator)
class _VendorThankYouInfoDecorator(Singleton):
    """
    Decorate the thank you page information for gifts.
    """

    thank_you_context_key = 'Gifting'

    def _predicate(self, unused_context, unused_result):
        return self._is_authenticated

    def get_course(self, purchase_attempt):
        purchaseables = purchase_attempt.Items
        catalog = component.getUtility(ICourseCatalog)
        for item in purchaseables or ():
            purchasable = get_purchasable(item)
            if not IPurchasableCourse.providedBy(purchasable):
                continue
            for catalog_ntiid in purchasable.Items:
                try:
                    entry = catalog.getCatalogEntry(catalog_ntiid)
                    return ICourseInstance(entry)
                except (KeyError, LookupError):
                    logger.error("Could not find course entry %s",
                                 catalog_ntiid)

    def decorateExternalMapping(self, context, result):
        course = self.get_course(context)
        key = self.thank_you_context_key # vendor info key
        thank_you_page = get_vendor_thank_you_page(course, key)
        if thank_you_page:
            result['VendorThankYouPage'] = thank_you_page


@component.adapter(IPurchasableCourse)
@interface.implementer(IExternalObjectDecorator)
class PurchasableCourseDecorator(Singleton):

    def decorateExternalObject(self, unused_original, external):
        # remove deprecated / legacy if no value is specified
        for name in ('Featured', 'Preview', 'StartDate', 'Department',
                     'Signature', 'Communities', 'Duration', 'EndDate'):
            value = external.get(name)
            if not value:
                external.pop(name, None)


@component.adapter(IPurchasableCourse)
@interface.implementer(IExternalObjectDecorator)
class _PurchasableCourseDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorate the purchasable course for deletion, where appropriate.
    """

    def _predicate(self, context, unused_result):
        return  self._is_authenticated \
            and can_edit_course_purchasable(context, self.remoteUser)

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel='delete')
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context


@component.adapter(IPurchasableCourse)
@interface.implementer(IExternalObjectDecorator)
class _PurchasableCourseEditLinkRemoverDecorator(EditLinkRemoverDecorator):
    """
    Ensure only our specified users can edit purchasable course objects.
    """

    def _predicate(self, context, unused_result):
        return  self._is_authenticated \
            and not can_edit_course_purchasable(context, self.remoteUser)


@interface.implementer(IExternalObjectDecorator)
class _CoursePurchasableDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Only decorate the course as being able to have a course
    purchasable if it does not already have one, it has connect
    key(s), it does not have a vendor info purchasable, it
    does not already have a purchasable, and license permitted.
    """

    def _predicate(self, context, unused_result):
        return  self._is_authenticated \
            and not IPurchasableCourse(context, None) \
            and has_default_store_key() \
            and can_create_purchasable() \
            and can_course_have_editable_purchasable(context) \
            and can_edit_course_purchasable(context, self.remoteUser)

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel='CreateCoursePurchasable',
                    elements=('@@CreateCoursePurchasable',))
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)

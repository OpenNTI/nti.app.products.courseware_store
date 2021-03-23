#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
from datetime import datetime

import isodate

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

import pytz

import six
from six.moves import urllib_parse

from zc.intid.interfaces import IBeforeIdRemovedEvent

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.component.hooks import getSite

from zope.dottedname import resolve as dottedname

from zope.event import notify

from zope.i18n import translate

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.security.interfaces import IPrincipal

from nti.app.authentication import get_remote_user

from nti.app.products.courseware.interfaces import ICoursesWorkspace
from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_store import MessageFactory as _

from nti.app.products.courseware_store.interfaces import IPurchasableCourse
from nti.app.products.courseware_store.interfaces import IStoreEnrollmentEvent

from nti.app.products.courseware_store.interfaces import StoreEnrollmentEvent

from nti.app.products.courseware_store.purchasable import sync_purchasable_course
from nti.app.products.courseware_store.purchasable import sync_purchasable_course_choice_bundles

from nti.app.store.subscribers import safe_send_purchase_confirmation
from nti.app.store.subscribers import store_purchase_attempt_successful

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.brand.utils import get_site_brand_name

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.workspaces.interfaces import IUserService

from nti.contenttypes.courses.interfaces import ES_PURCHASED

from nti.contenttypes.courses.interfaces import AlreadyEnrolledException

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import ICourseCatalogDidSyncEvent
from nti.contenttypes.courses.interfaces import ICourseVendorInfoSynchronized
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.contenttypes.courses.utils import get_enrollment_record
from nti.contenttypes.courses.utils import drop_any_other_enrollments

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ILinkExternalHrefOnly

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IEmailAddressable

from nti.dataserver.users.users import User

from nti.externalization.externalization import to_external_object

from nti.invitations.interfaces import IInvitationAcceptedEvent

from nti.links.externalization import render_link

from nti.links.links import Link

from nti.mailer.interfaces import ITemplatedMailer

from nti.ntiids.ntiids import make_specific_safe
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.store import RedemptionException

from nti.store.interfaces import IPurchaseAttempt
from nti.store.interfaces import IGiftPurchaseAttempt
from nti.store.interfaces import IPurchaseAttemptRefunded
from nti.store.interfaces import IRedeemedPurchaseAttempt
from nti.store.interfaces import IStorePurchaseInvitation
from nti.store.interfaces import IInvitationPurchaseAttempt
from nti.store.interfaces import IPurchaseAttemptSuccessful
from nti.store.interfaces import IGiftPurchaseAttemptRedeemed

from nti.store.store import get_gift_code

from nti.store.purchasable import get_purchasable

from nti.store.purchase_attempt import get_purchasables

#: The package to find enrollment templates.
DEFAULT_ENROLL_PACKAGE = 'nti.app.products.courseware'

logger = __import__('logging').getLogger(__name__)


def _get_redeem_cutoff_date(purchase):
    result = None
    now = datetime.utcnow()
    purchaseables = get_purchasables(purchase)
    for purchasable in purchaseables or ():
        if purchasable.RedeemCutOffDate is not None:
            redeem_date = isodate.parse_datetime(purchasable.RedeemCutOffDate)
            redeem_date = redeem_date.replace(tzinfo=None)
            if result is None:
                result = redeem_date
            else:
                result = max(result, redeem_date)
    if result and now > result:
        raise RedemptionException(_(u"Gift cannot be redeemed at this time."))
    if result:
        result = result.strftime('%B %d, %Y')
    return result


def _get_policy_package():
    """
    Get the policy defined package for this site, useful for
    looking up site/context specific templates.
    """
    policy = component.getUtility(ISitePolicyUserEventListener)
    return getattr(policy, 'PACKAGE', None)


def _get_entry_id(entry):
    return entry.ProviderUniqueID.replace(' ', '').lower()


def get_template(catalog_entry, base_template, default_package=None):
    """
    Look for a specific context defined template for this catalog
    entry.  Returns the package where this template should be found.
    """
    package = _get_policy_package()
    if not package:
        return base_template, default_package

    package = dottedname.resolve(package)
    provider_unique_id = _get_entry_id(catalog_entry)
    # Safe ascii path
    provider_unique_id = make_specific_safe(provider_unique_id)
    full_provider_id = provider_unique_id.replace('-', '')
    template = full_provider_id + "_" + base_template

    path = os.path.join(os.path.dirname(package.__file__), 'templates')
    if not os.path.exists(os.path.join(path, template + ".pt")):
        # Full path doesn't exist; Drop our specific id part and try that
        provider_unique_prefix = provider_unique_id.split('-')[0]
        provider_unique_prefix = provider_unique_prefix.split('/')[0]
        template = provider_unique_prefix + "_" + base_template
        if not os.path.exists(os.path.join(path, template + ".pt")):
            template = base_template
    if template == base_template:
        # Use our default package if no context specific template
        # is found in our site.
        if not os.path.exists(os.path.join(path, template + ".pt")):
            package = default_package
    return template, package


def get_user(user):
    if user and not IUser.providedBy(user):
        user = User.get_user(str(user))
    return user


def _parent_course_instance_enrollemnt(course, user):
    enrollment = component.queryMultiAdapter((course, user),
                                             ICourseInstanceEnrollment)
    if enrollment is not None:
        service = IUserService(user, None)
        workspace = ICoursesWorkspace(service, None)
        parent = workspace['EnrolledCourses'] if workspace is not None else None
        if parent is not None and not enrollment.__parent__:
            enrollment.__parent__ = parent


def _enroll(course, user, purchasable=None, request=None, check_enrollment=False):
    enrollment = get_enrollment_record(course, user)
    if enrollment is not None and enrollment.Scope == ES_PURCHASED and check_enrollment:
        msg = _(u"You are already enrolled in this course.")
        raise AlreadyEnrolledException(msg)

    send_event = True
    if enrollment is None or enrollment.Scope != ES_PURCHASED:
        drop_any_other_enrollments(course, user)
        if enrollment is None:  # Never before been enrolled
            enrollment_manager = ICourseEnrollmentManager(course)
            # pylint: disable=redundant-keyword-arg
            enrollment = enrollment_manager.enroll(user, scope=ES_PURCHASED,
                                                   context=purchasable)
            _parent_course_instance_enrollemnt(course, user)

        elif enrollment.Scope != ES_PURCHASED:
            logger.info("User %s now paying for course (old_scope %s)",
                        user, enrollment.Scope)
            # change scope and mark record
            enrollment.Scope = ES_PURCHASED
            # notify to reflect changes
            lifecycleevent.modified(enrollment)
    else:
        send_event = False

    if send_event and enrollment is not None:
        # notify store based enrollment
        request = request or get_current_request()
        notify(StoreEnrollmentEvent(enrollment, purchasable, request))
    return send_event


def _unenroll(course, user, unused_purchasable=None):
    # pylint: disable=too-many-function-args
    enrollments = ICourseEnrollments(course)
    enrollment = enrollments.get_enrollment_for_principal(user)
    if enrollment is not None:
        enrollment_manager = ICourseEnrollmentManager(course)
        enrollment_manager.drop(user)
        return True
    return False


def _get_courses_from_purchasables(purchasables=()):
    for item in purchasables or ():
        purchasable = get_purchasable(item)
        if not IPurchasableCourse.providedBy(purchasable):
            continue
        for name in purchasable.Items:
            entry = find_object_with_ntiid(name)
            course = ICourseInstance(entry, None)
            if course is not None:
                yield course, purchasable


def _to_sequence(items=(), unique=True):
    result = items.split() if isinstance(items, six.string_types) else items
    return set(result or ()) if unique else result


def _process_successful_purchase(purchasables, user=None, request=None, check=False):
    result = False
    user = get_user(user)
    if user is not None:
        purchasables = _to_sequence(purchasables)
        for course, purchasable in _get_courses_from_purchasables(purchasables):
            _enroll(course,
                    user,
                    purchasable,
                    request=request,
                    check_enrollment=check)
            result = True
    return result


@component.adapter(IPurchaseAttempt, IPurchaseAttemptSuccessful)
def _purchase_attempt_successful(purchase, event):
    # CS: use Items property of the purchase object in case it has been proxied
    if      not IGiftPurchaseAttempt.providedBy(purchase) \
        and _process_successful_purchase(purchase.Items,
                                         user=purchase.creator,
                                         request=event.request):
        logger.info("Course purchase %s was successful", purchase.id)


@component.adapter(IInvitationAcceptedEvent)
def _purchase_invitation_accepted(event):
    invitation = event.object
    if      IStorePurchaseInvitation.providedBy(invitation) \
        and IInvitationPurchaseAttempt.providedBy(invitation.purchase):
        original = invitation.purchase
        # CS: use Items property of the purchase object in case it has been
        # proxied
        _process_successful_purchase(original.Items, user=event.user)
        logger.info("Course invitation %s was accepted", invitation.code)


def _process_refunded_purchase(purchase, user=None):
    result = False
    user = get_user(user if user is not None else purchase.creator)
    if user is not None:
        for course, purchasable in _get_courses_from_purchasables(purchase.Items):
            _unenroll(course, user, purchasable)
            result = True
    return result


@component.adapter(IPurchaseAttempt, IPurchaseAttemptRefunded)
def _purchase_attempt_refunded(purchase, unused_event):
    if      not IGiftPurchaseAttempt.providedBy(purchase) \
        and _process_refunded_purchase(purchase):
        logger.info("Course purchase %s was refunded", purchase.id)


@component.adapter(IRedeemedPurchaseAttempt, IPurchaseAttemptRefunded)
def _redeemed_purchase_attempt_refunded(purchase, unused_event):
    _process_refunded_purchase(purchase)


@component.adapter(IGiftPurchaseAttempt, IGiftPurchaseAttemptRedeemed)
def _gift_purchase_attempt_redeemed(purchase, event):
    user = event.user
    request = event.request
    # CS: use Items property of the purchase object  in case it has been
    # proxied
    if _process_successful_purchase(purchase.Items, user, request=request, check=True):
        code = event.code or get_gift_code(purchase)
        logger.info("Course gift %s has been redeemed", code)


@component.adapter(ICourseInstanceEnrollmentRecord, IBeforeIdRemovedEvent)
def _enrollment_record_dropped(record, unused_event):
    user = IUser(record, None)
    remote_user = get_remote_user()
    # Users cannot drop purchased courses, but admins can on their behalf.
    if record.Scope == ES_PURCHASED and remote_user == user:
        raise hexc.HTTPForbidden('Cannot drop a purchased course.')


# course subscribers


@component.adapter(ICourseInstance, ICourseVendorInfoSynchronized)
def on_course_vendor_info_synced(course, unused_event):
    if component.getSiteManager() != component.getGlobalSiteManager():
        sync_purchasable_course(course)


@component.adapter(ICourseInstance, ICourseCatalogDidSyncEvent)
def on_course_catalog_did_sync(unused_course, unused_event):
    if component.getSiteManager() != component.getGlobalSiteManager():
        sync_purchasable_course_choice_bundles()


@component.adapter(ICourseInstance, IBeforeIdRemovedEvent)
def on_course_instance_removed(course, unused_event):
    if component.getSiteManager() != component.getGlobalSiteManager():
        purchasable = IPurchasableCourse(course, None)
        if purchasable is not None:
            purchasable.Public = False
            purchasable.__parent__ = getSite()
            lifecycleevent.modified(purchasable)


def _build_base_args(event, user, profile):
    policy = component.getUtility(ISitePolicyUserEventListener)

    if IUser.providedBy(user):
        user_ext = to_external_object(user)
        informal_username = user_ext.get('NonI18NFirstName', profile.realname) \
                         or user.username
    else:
        informal_username = profile.realname or str(user)

    site_alias = getattr(policy, 'COM_ALIAS', '')
    for_credit_url = getattr(policy, 'FOR_CREDIT_URL', '')
    brand = get_site_brand_name()

    args = {'profile': profile,
            'context': event,
            'user': user,
            'for_credit_url': for_credit_url,
            'site_alias': site_alias,
            'support_email': policy.SUPPORT_EMAIL,
            'brand': brand,
            'informal_username': informal_username,
            'today': isodate.date_isoformat(datetime.now())}
    return args


def _queue_email(request, username, profile, args, template, subject,
                 package, text_template_extension='.txt'):
    try:
        mailer = component.getUtility(ITemplatedMailer)
        mailer.queue_simple_html_text_email(
            template,
            subject=subject,
            recipients=[profile],
            template_args=args,
            request=request,
            package=package,
            text_template_extension=text_template_extension)
        return True
    except Exception:  # pylint: disable=broad-except
        logger.exception('Error while sending store enrollment email to %s',
                         username)
        return False


def _send_email(event, user, profile, email, args, template, subject, package):

    request = getattr(event, 'request', get_current_request())
    if not request or not email:
        logger.warning("Not sending an enrollment email because of no email or request "
                       "(user=%s) (email=%s) (request=%s)", user, email, request is None)
        return

    username = user.username
    assert getattr(IPrincipal(profile, None), 'id', None) == username
    assert getattr(IEmailAddressable(profile, None), 'email', None) == email

    _queue_email(request=request,
                 username=username,
                 profile=profile,
                 args=args,
                 template=template,
                 subject=subject,
                 package=package,
                 text_template_extension='.mak')


def _get_start_date(entry, request):
    course_start_date = ''
    if entry is not None and entry.StartDate:
        # pylint: disable=no-member
        locale = IBrowserRequest(request).locale
        dates = locale.dates
        formatter = dates.getFormatter('date', length='long')
        course_start_date = formatter.format(entry.StartDate)
    return course_start_date


def _get_course_start_date(course_ntiid, request):
    entry = find_object_with_ntiid(course_ntiid)
    return _get_start_date(entry, request)


def _get_purchase_args(attempt, unused_purchasable, unused_request):
    """
    Add gift specific args for purchase email.
    """
    purchase_item_suffix = ''
    redeem_by_clause = None

    if IGiftPurchaseAttempt.providedBy(attempt):
        purchase_item_suffix = _(u' - Gift')
        redeem_by_date = _get_redeem_cutoff_date(attempt)
        if redeem_by_date:
            redeem_by_clause = translate(_(u"Must redeem by ${redeem_by}",
                                           mapping={'redeem_by': redeem_by_date}))

    args = {
        'purchase_item_suffix': purchase_item_suffix,
        'redeem_by_clause': redeem_by_clause
    }
    return args


@component.adapter(IPurchaseAttempt, IPurchaseAttemptSuccessful)
def _purchase_attempt_email_notification(purchase, event):
    items = purchase.Items
    purchasable = get_purchasable(items[0]) if items else None
    if purchasable is None or not IPurchasableCourse.providedBy(purchasable):
        return

    request = getattr(event, 'request', get_current_request())
    if request is None:
        return

    user = purchase.creator
    profile = purchase.Profile
    add_args = _build_base_args(event, user, profile)

    purchase_args = _get_purchase_args(purchase, purchasable, request)
    add_args.update(purchase_args)

    store_purchase_attempt_successful(event, add_args=add_args)

    # Send to additional addresses
    settings = component.queryUtility(IApplicationSettings) or {}
    email_line = settings.get('purchase_additional_confirmation_addresses', '')
    for email in email_line.split():
        safe_send_purchase_confirmation(event, email, add_args=add_args)


def _web_root():
    settings = component.getUtility(IApplicationSettings)
    web_root = settings.get('web_app_root', '/NextThoughtWebApp/')
    return web_root


def _get_redeem_link(request, catalog_entry, redemption_code):
    link = Link(catalog_entry)
    interface.alsoProvides(link, ILinkExternalHrefOnly)
    entry_href = render_link(link)
    url = 'catalog/object/%s/redeem/%s' % (entry_href, redemption_code)

    app_url = request.application_url
    redemption_link = urllib_parse.urljoin(app_url, _web_root())
    redemption_link = urllib_parse.urljoin(redemption_link, url)
    return redemption_link


def _get_session_length_args(catalog_entry):
    """
    For a catalog entry, return a tuple of formatted strings displaying
    the length of the course.
    """
    course_session_date = ''
    course_session_length = ''

    duration = catalog_entry.Duration
    if duration.days:
        duration_days = duration.days // 7
        course_session_length = '%s WEEK SESSION' % duration_days

    if catalog_entry.StartDate and catalog_entry.EndDate:
        # Localize times to UTC to match catalog, then
        # view as local timezone. Currently hard-coded to Central
        # time. May want to consider adding a default timezone to
        # policies if we make this more general at some point.
        localTimeZone = pytz.timezone('US/Central')
        utc_start_date = pytz.utc.localize(catalog_entry.StartDate)
        utc_end_date = pytz.utc.localize(catalog_entry.EndDate)
        local_start_date = utc_start_date.astimezone(localTimeZone)
        local_end_date = utc_end_date.astimezone(localTimeZone)

        start_format = local_start_date.strftime("%B %d")
        end_format = local_end_date.strftime("%B %d, %Y")
        course_session_date = '%s-%s' % (start_format, end_format)

    return course_session_length, course_session_date


def _get_gift_args(entry_ntiid, redemption_code, event, request):
    entry = find_object_with_ntiid(entry_ntiid)
    course_args = _build_course_args(event, entry)
    redemption_link = _get_redeem_link(request, entry, redemption_code)
    session_length, session_date = _get_session_length_args(entry)
    course_args.update({'redemption_link': redemption_link,
                        'catalog_entry': entry,
                        'course_session_length': session_length,
                        'course_session_date': session_date})
    result = entry, course_args
    return result


def _send_entry_gift_email(purchase, purchase_ntiids, event, request):
    redemption_code = get_gift_code(purchase)
    # Get all of the purchase options for our courses
    purchase_options = [_get_gift_args(x, redemption_code, event, request)
                        for x in purchase_ntiids]

    creator_email = purchase.Creator
    receiver_email = purchase.Receiver

    base_template = 'gift_certificate_email'
    first_catalog_entry = purchase_options[0][0]

    # FIXME: default gift email
    template, package = get_template(first_catalog_entry, base_template)

    if len(purchase_options) > 1:
        gift_subject = translate(_(u"Janux Gift Certificate"))
    else:
        gift_subject = translate(_(u"Janux Gift Certificate: ${course_title}",
                                   mapping={'course_title': first_catalog_entry.title}))

    gift_subject_copy = translate(_(u"${gift_subject} (copy)",
                                    mapping={'gift_subject': gift_subject}))

    outbound_params = []
    # Find out which emails to send
    if receiver_email and creator_email != receiver_email:
        # Two different email addresses; two different emails.
        outbound_params.append((receiver_email, gift_subject, None))
        header_msg = _(u"Below is a copy of the gift certificate that was sent to ${rec_email}.",
                       mapping={'rec_email': receiver_email})

        outbound_params.append((creator_email, gift_subject_copy, header_msg))
    else:
        # We do not have a receiver or the two emails are the same; just send
        # to buyer.
        header_msg = _(u"""Please forward this gift certificate to the email address of your
                        intended recipient.  You can also print this certificate out
                        and pass it to a person of your choosing.""")
        outbound_params.append((creator_email, gift_subject, header_msg))

    policy = component.getUtility(ISitePolicyUserEventListener)
    site_alias = getattr(policy, 'COM_ALIAS', '')
    for_credit_url = getattr(policy, 'FOR_CREDIT_URL', '')

    gift_options = sorted(purchase_options, key=lambda x: x[0].StartDate)
    gift_options = [x[1] for x in gift_options]
    redeem_by_date = _get_redeem_cutoff_date(purchase)

    args = {
        'sender_name': purchase.SenderName,
        'context': event,
        'receiver_name': purchase.ReceiverName,
        'gift_message': purchase.Message,
        'for_credit_url': for_credit_url,
        'site_alias': site_alias,
        'redeem_by_date': redeem_by_date,
        'redemption_code': redemption_code,
        'support_email': policy.SUPPORT_EMAIL,
        'gift_options': gift_options
    }

    # Now start sending emails
    for _email, _subject, _header in outbound_params:
        args.update({'header': _header})
        _queue_email(request=request,
                     username=_email,
                     profile=_email,
                     args=args,
                     template=template,
                     subject=_subject,
                     package=package,
                     text_template_extension='.mak')


@component.adapter(IGiftPurchaseAttempt, IPurchaseAttemptSuccessful)
def _gift_purchase_attempt_email_notification(purchase, event):
    items = purchase.Items
    purchasable = get_purchasable(items[0]) if items else None
    if purchasable is None or not IPurchasableCourse.providedBy(purchasable):
        return

    request = getattr(event, 'request', get_current_request())
    if request is None:
        return

    _send_entry_gift_email(purchase, purchasable.Items, event, request)


def _build_course_args(event, catalog_entry):
    request = getattr(event, 'request', get_current_request())
    course_start_date = _get_start_date(catalog_entry, request)
    course_end_date = catalog_entry.EndDate
    course_archived = course_end_date and course_end_date < datetime.utcnow()
    course_preview = catalog_entry.Preview

    html_sig = catalog_entry.InstructorsSignature.replace('\n', "<br />")

    course_args = {'course': catalog_entry,
                   'today': datetime.utcnow(),
                   'instructors_html_signature': html_sig,
                   'course_preview': course_preview,
                   'course_archived': course_archived,
                   'course_start_date': course_start_date}
    return course_args


def _build_enrollment_args(event, user, profile, catalog_entry):
    args = _build_base_args(event, user, profile)
    course_args = _build_course_args(event, catalog_entry)
    args.update(course_args)

    subject = translate(_(u"Welcome to ${title}",
                          mapping={'title': catalog_entry.Title}))

    course_args = {'subject': subject}
    args.update(course_args)
    return args


@component.adapter(ICourseInstanceEnrollmentRecord, IStoreEnrollmentEvent)
def _user_enrolled(record, event):
    if record.Scope != ES_PURCHASED:
        return
    creator = record.Principal
    creator = get_user(creator)
    profile = IUserProfile(creator)
    email = getattr(profile, 'email', None)

    course = record.CourseInstance
    catalog_entry = ICourseCatalogEntry(course)

    base_template = 'enrollment_confirmation_email'
    template, package = get_template(catalog_entry,
                                     base_template,
                                     DEFAULT_ENROLL_PACKAGE)

    args = _build_enrollment_args(event, creator, profile, catalog_entry)
    subject = args.pop('subject')

    _send_email(event, creator, profile,
                email, args, template,
                subject, package)

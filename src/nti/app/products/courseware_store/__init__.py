#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.app.products.courseware import MessageFactory

#: Purchasable course NTIID type
PURCHASABLE_COURSE = u'purchasable_course'

#: Purchasable course choice bundle NTIID type
PURCHASABLE_COURSE_CHOICE_BUNDLE = u'purchasable_course_choice_bundle'

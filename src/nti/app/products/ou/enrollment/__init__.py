#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OU enrollment modude

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from ..utils import is_true
from ..utils import get_text
from ..utils import get_fileobj

from .. import MessageFactory

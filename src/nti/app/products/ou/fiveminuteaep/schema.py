#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.schema import vocabulary

from nti.schema.field import Choice

BOOLS = ('Y', 'N')
BOOLS_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in BOOLS])

class Bool(Choice):
	
	def __init__(self, *args, **kwargs):
		kwargs['vocabulary'] = BOOLS_VOCABULARY
		Choice.__init__(self, *args, **kwargs)

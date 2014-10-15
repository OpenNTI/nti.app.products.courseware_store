#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import codecs
from collections import OrderedDict

def _build_codes(filename, factory=dict):
	result = factory()
	path = os.path.join(os.path.dirname(__file__), filename)
	with codecs.open(path, "r", encoding="UTF-8") as fp:
		for line in fp.readlines():
			if not line:
				continue
			code, name = line.split('\t')
			result[name.strip()] = code.strip()
	return result

COUNTRIES = None
def get_countries():
	global COUNTRIES
	if not COUNTRIES:
		COUNTRIES = _build_codes("data/countries.txt")
	return COUNTRIES

STATES = None
def get_states():
	global STATES
	if not STATES:
		# Keep US states first in the list, followed by the rest.
		us_states = _build_codes("data/us_states.txt")
		STATES = OrderedDict( sorted( us_states.items() ) )

		non_us_states = _build_codes("data/non_us_states.txt")
		non_us_states = OrderedDict( sorted( non_us_states.items() ) )
		for k,v in non_us_states.items():
			STATES[k] = v
	return STATES

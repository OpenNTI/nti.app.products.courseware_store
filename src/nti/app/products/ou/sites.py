#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from z3c.baseregistry.baseregistry import BaseComponents

from nti.appserver.policies.sites import BASEADULT

OU = BaseComponents(BASEADULT, name='platform.ou.edu', bases=(BASEADULT,))
JANUX = BaseComponents(OU, name='janux.ou.edu', bases=(OU,))

# Two separate test sites, one for client eval (outest), and
# one internally (oualpha). They have different configs so they
# only extend the base OU.
OUTEST = BaseComponents(OU, name='ou-test.nextthought.com', bases=(OU,))
OUALPHA = BaseComponents(OU, name='ou-alpha.nextthought.com', bases=(OU,))

PERFORMANCE = BaseComponents(OU, name='performance.nextthought.com', bases=(OU,))
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope.configuration import xmlconfig

import nti.app.products.courseware_store

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

class CourseStoreApplicationTestLayer(InstructedCourseApplicationTestLayer):

    @classmethod
    def setUp(cls):
        xmlconfig.file('configure.zcml', package=nti.app.products.courseware_store)

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls, test=None):
        pass

    @classmethod
    def testTearDown(cls):
        pass

class OUCoursewareApplicationLayerTest(ApplicationLayerTest):
    layer = CourseStoreApplicationTestLayer


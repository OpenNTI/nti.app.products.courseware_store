#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope.configuration import xmlconfig

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer


class CourseStoreApplicationTestLayer(InstructedCourseApplicationTestLayer):

    @classmethod
    def setUp(cls):
        xmlconfig.file('configure.zcml',
                       package="nti.app.products.courseware_store")

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls, test=None):
        pass

    @classmethod
    def testTearDown(cls):
        pass


from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

import zope.testing.cleanup


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.dataserver',
                       'nti.app.client_preferences',
                       'nti.app.products.courseware_store')

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass

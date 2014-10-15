#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

import os
import sys
import argparse

import zope.browserpage

from zope import component
from zope.component import hooks
from zope.container.contained import Contained
from zope.configuration import xmlconfig, config
from zope.dottedname import resolve as dottedname

from z3c.autoinclude.zcml import includePluginsDirective

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.utils import run_with_dataserver

from nti.site.site import get_site_for_site_names

from . import workflow

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

def _create_context(env_dir=None):
	etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
	etc = os.path.expanduser(etc)

	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)

	slugs = os.path.join(etc, 'package-includes')
	if os.path.exists(slugs) and os.path.isdir(slugs):
		package = dottedname.resolve('nti.dataserver')
		context = xmlconfig.file('configure.zcml', package=package, context=context)
		xmlconfig.include(context, files=os.path.join(slugs, '*.zcml'),
						  package='nti.appserver')

	library_zcml = os.path.join(etc, 'library.zcml')
	if not os.path.exists(library_zcml):
		raise Exception("could not locate library zcml file %s", library_zcml)
	xmlconfig.include(context, file=library_zcml, package='nti.appserver')
	
	# Include zope.browserpage.meta.zcm for tales:expressiontype
	# before including the products
	xmlconfig.include(context, file="meta.zcml", package=zope.browserpage)

	# include plugins
	includePluginsDirective(context, PP_APP)
	includePluginsDirective(context, PP_APP_SITES)
	includePluginsDirective(context, PP_APP_PRODUCTS)
	
	return context

def _process_args(ims_file, create_persons, is_ou=False, site=None):
	if site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (site,), site=cur_site )
		if new_site is cur_site:
			raise ValueError("Unknown site name", site)
		hooks.setSite(new_site)

	# load library
	library = component.queryUtility(IContentPackageLibrary)
	getattr(library, 'contentPackages')
	
	workflow.process(ims_file, create_persons, is_ou=is_ou)

def main():
	arg_parser = argparse.ArgumentParser(description="Course enrollment")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							 dest='verbose')

	arg_parser.add_argument('--create', help="Create users", action='store_true',
							dest='create_persons', default=False)

	arg_parser.add_argument('--ou', help="Create OU users", action='store_true',
							dest='is_ou', default=False)

	arg_parser.add_argument('-i', '--ims', help="IMS file location", dest='ims_file')
	arg_parser.add_argument('-s', '--site', dest='site', help="Request site (janux.ou.edu)")

	args = arg_parser.parse_args()

	ims_file = args.ims_file
	ims_file = os.path.expanduser(ims_file) if ims_file else None
	if not ims_file or not os.path.exists(ims_file):
		print('IMS file cannot be found', ims_file, file=sys.stderr)
		sys.exit(2)

	if not args.site:
		print('WARN: NO site specified')
		
	create_persons = args.create_persons
	if create_persons and not args.site:
		print('WARN: Creating users with no site specified')
		
	env_dir = os.getenv('DATASERVER_DIR')
	context = _create_context(env_dir)
	conf_packages = ('nti.appserver',)
	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						context=context,
						minimal_ds=False,
						function=lambda: _process_args(ims_file, create_persons,
													   args.is_ou, args.site))

if __name__ == '__main__':
	main()

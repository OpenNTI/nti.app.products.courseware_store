from setuptools import setup, find_packages
import codecs

VERSION = '0.0.0'

entry_points = {
    'console_scripts': [
        "nti_ou_enrollment = nti.app.products.ou.enrollment.enroll:main",
    ],
    "z3c.autoinclude.plugin": [
		'target = nti.app.products',
	],
}

setup(
    name = 'nti.app.products.ou',
    version = VERSION,
    author = 'Carlos Sanchez',
    author_email = 'carlos@nextthought.com',
    description = "Support for University of Oklahoma integration",
    long_description = codecs.open('README.rst', encoding='utf-8').read(),
    license = 'Proprietary',
    keywords = 'ou ldap',
    #url = 'https://github.com/NextThought/nti.nose_traceback_info',
    classifiers = [
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
		'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.3',
		'Framework :: Pyramid',
        ],
	packages=find_packages('src'),
	package_dir={'': 'src'},
	namespace_packages=['nti', 'nti.app', 'nti.app.products'],
	install_requires=[
		'setuptools',
		'python-ldap',
		'pyScss',
		'ldappool',
	],
	entry_points=entry_points
)

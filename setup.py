import codecs
from setuptools import setup, find_packages

entry_points = {
    'console_scripts': [
    ],
    "z3c.autoinclude.plugin": [
        'target = nti.app.products',
    ],
}

TESTS_REQUIRE = [
    'nti.app.testing',
    'nti.testing',
    'zope.testrunner',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.app.products.courseware_store',
    version=_read('version.txt').strip(),
    author='Jason Madden',
    author_email='jason@nextthought.com',
    description="NTI Course-Store Integration",
    long_description=(_read('README.rst') + '\n\n' + _read("CHANGES.rst")),
    license='Apache',
    keywords='course store integration',
    classifiers=[
        'Framework :: Zope',
        'Framework :: Pyramid',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/NextThought/nti.app.products.courseware_store",
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti', 'nti.app', 'nti.app.products'],
    install_requires=[
        'setuptools',
        'isodate',
        'nti.app.products.courseware',
        'nti.app.store',
        'nti.base',
        'nti.contentlibrary',
        'nti.contenttypes.courses',
        'nti.externalization',
        'nti.ntiids',
        'nti.schema',
        'nti.site',
        'nti.store',
        'pyramid',
        'pytz',
        'requests',
        'six',
        'zc.intid',
        'zope.cachedescriptors',
        'zope.component',
        'zope.configuration',
        'zope.deferredimport',
        'zope.dottedname',
        'zope.event',
        'zope.generations',
        'zope.i18n',
        'zope.interface',
        'zope.intid',
        'zope.lifecycleevent',
        'zope.publisher',
        'zope.schema',
        'zope.security',
        'zope.traversing',
    ],
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinx_rtd_theme',
        ],
    },
    entry_points=entry_points
)

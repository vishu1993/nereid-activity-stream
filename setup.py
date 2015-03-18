# -*- coding: utf-8 -*-
"""
    Nereid Activity Stream

    :copyright: (c) 2013-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
import sys
import re
import os
import ConfigParser
import unittest
from setuptools import setup, Command


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


class SQLiteTest(Command):
    """
    Run the tests on SQLite
    """
    description = "Run tests on SQLite"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):

        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)

        os.environ['TRYTOND_DATABASE_URI'] = 'sqlite://'
        os.environ['DB_NAME'] = ':memory:'

        from tests import suite
        test_result = unittest.TextTestRunner(verbosity=3).run(suite())

        if test_result.wasSuccessful():
            sys.exit(0)
        sys.exit(-1)


config = ConfigParser.ConfigParser()
config.readfp(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
major_version, minor_version, _ = info.get('version', '0.0.1').split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

requires = []

for dep in info.get('depends', []):
    if not re.match(r'(ir|res|webdav)(\W|$)', dep):
        requires.append(
            'trytond_%s >= %s.%s, < %s.%s' %
            (dep, major_version, minor_version, major_version,
                minor_version + 1)
        )
requires.append(
    'trytond >= %s.%s, < %s.%s' %
    (major_version, minor_version, major_version, minor_version + 1)
)

setup(
    name='trytond_nereid_activity_stream',
    version=info.get('version', '0.0.1'),
    description='Activity Stream (a.k.a news feed) for Tryton nereid',
    long_description=open('README.rst').read(),
    author='Openlabs Technologies & consulting (P) Limited',
    author_email='info@openlabs.co.in',
    url='https://github.com/openlabs/nereid-activity-stream',
    package_dir={'trytond.modules.nereid_activity_stream': '.'},
    packages=[
        'trytond.modules.nereid_activity_stream',
        'trytond.modules.nereid_activity_stream.tests',
    ],
    package_data={
        'trytond.modules.nereid_activity_stream': info.get('xml', []) +
        info.get('translation', []) + ['tryton.cfg'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Tryton',
        'Topic :: Office/Business',
    ],
    license='GPLv3',
    install_requires=requires,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    nereid_blog = trytond.modules.nereid_activity_stream
    """,
    test_suite='tests.suite',
    test_loader='trytond.test_loader:Loader',
    cmdclass={
        'test': SQLiteTest,
    },
)

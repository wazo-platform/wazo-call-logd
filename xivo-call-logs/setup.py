#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fnmatch
import os

from distutils.core import setup


def is_package(path):
    is_svn_dir = fnmatch.fnmatch(path, '*/.svn/*')
    is_test_module = fnmatch.fnmatch(path, '*tests')
    return not (is_svn_dir or is_test_module)

packages = [p for p, _, _ in os.walk('xivo_ami') if is_package(p)]


setup(
    name='xivo-call-logs',
    version='1.2',
    description='XiVO Call Logs Generation',
    author='Avencall',
    author_email='dev@avencall.com',
    url='https://github.com/xivo-pbx/xivo-call-logs',
    license='GPLv3',
    packages=packages,
    scripts=['bin/xivo-call-logs', 'bin/xivo-call-logd'],
)

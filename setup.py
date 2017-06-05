#!/usr/bin/env python3
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from setuptools import setup
from setuptools import find_packages


setup(
    name='xivo-call-logs',
    version='1.2',
    description='XiVO Call Logs Generation',
    author='Wazo Authors',
    author_email='dev.wazo@gmail.com',
    url='http://wazo.community',
    license='GPLv3',
    packages=find_packages(),
    package_data={
        'xivo_call_logs.plugins': ['*/api.yml'],
    },
    scripts=['bin/xivo-call-logs', 'bin/xivo-call-logd'],
    entry_points={
        'xivo_call_logs.plugins': [
            'api = xivo_call_logs.plugins.api.plugin:Plugin',
            'cdr = xivo_call_logs.plugins.cdr.plugin:Plugin',
        ]
    }
)

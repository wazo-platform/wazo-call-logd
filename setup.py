#!/usr/bin/env python3
# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from setuptools import setup
from setuptools import find_packages


setup(
    name='wazo-call-logd',
    version='1.2',
    description='Wazo Call Logs Generation',
    author='Wazo Authors',
    author_email='dev@wazo.community',
    url='http://wazo.community',
    license='GPLv3',
    packages=find_packages(),
    package_data={
        'wazo_call_logd.plugins': ['*/api.yml'],
    },
    scripts=['bin/wazo-call-logs', 'bin/wazo-call-logd'],
    entry_points={
        'wazo_call_logd.plugins': [
            'api = wazo_call_logd.plugins.api.plugin:Plugin',
            'cdr = wazo_call_logd.plugins.cdr.plugin:Plugin',
            'status = wazo_call_logd.plugins.status.plugin:Plugin',
        ]
    }
)

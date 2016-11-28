#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages


setup(
    name='xivo-call-logs',
    version='1.2',
    description='XiVO Call Logs Generation',
    author='Avencall',
    author_email='dev@avencall.com',
    url='https://github.com/wazo-pbx/xivo-call-logs',
    license='GPLv3',
    packages=find_packages(),
    scripts=['bin/xivo-call-logs', 'bin/xivo-call-logd'],
)

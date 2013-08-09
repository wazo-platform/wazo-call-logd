#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name='xivo-call-logs',
    version='1.2',
    description='XiVO Call Logs Generation',
    author='Avencall',
    author_email='xivo-dev@lists.proformatique.com',
    url='http://wiki.xivo.fr/',
    packages=['xivo_call_logs'],
    scripts=['bin/xivo-call-logs'],
)

#!/usr/bin/env python3
# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

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
    package_data={'wazo_call_logd.plugins': ['*/api.yml']},
    entry_points={
        'console_scripts': [
            'wazo-call-logd=wazo_call_logd.main:main',
            'wazo-call-logd-init-db=wazo_call_logd.init_db:main',
            'wazo-call-logd-upgrade-db=wazo_call_logd.main:upgrade_db',
            'wazo-call-logd-migrate-db=wazo_call_logd.main_migrate_db:main',
            'wazo-call-logs=wazo_call_logd.main_sweep:main',
        ],
        'wazo_call_logd.celery_tasks': [
            'recording_export = wazo_call_logd.plugins.cdr.celery_tasks:Plugin',
        ],
        'wazo_call_logd.plugins': [
            'api = wazo_call_logd.plugins.api.plugin:Plugin',
            'cdr = wazo_call_logd.plugins.cdr.plugin:Plugin',
            'config = wazo_call_logd.plugins.config.plugin:Plugin',
            'export = wazo_call_logd.plugins.export.plugin:Plugin',
            'retention = wazo_call_logd.plugins.retention.plugin:Plugin',
            'status = wazo_call_logd.plugins.status.plugin:Plugin',
            'support_center = wazo_call_logd.plugins.support_center.plugin:Plugin',
        ],
        'wazo_purge_db.purgers': [
            'call-logs = wazo_call_logd.purger:CallLogsPurger',
            'exports = wazo_call_logd.purger:ExportsPurger',
            'recordings = wazo_call_logd.purger:RecordingsPurger',
        ],
    },
)

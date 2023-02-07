# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    datetime as dt,
    timedelta as td,
)
from hamcrest import assert_that, has_length, equal_to

from wazo_call_logd.database.models import CallLog, Export, Recording

from .helpers.base import DBIntegrationTest
from .helpers.constants import MASTER_TENANT, OTHER_TENANT
from .helpers.database import call_log, export, recording, retention
from .helpers.filesystem import FileSystemClient, file_


class _BasePurger(DBIntegrationTest):
    asset = 'purge'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.filesystem = FileSystemClient(
            execute=cls.docker_exec, service_name='purge-db', root=True
        )
        cls.config_file = '/etc/wazo-purge-db/conf.d/10-enable-plugin.yml'

    def setUp(self):
        super().setUp()
        self.filesystem.remove_file('/tmp/1')
        self.filesystem.remove_file('/tmp/2')
        self.filesystem.remove_file('/tmp/3')
        self._reset_default_config()

    def _reset_default_config(self):
        config = self.dao.config.find_or_create()
        config.retention_cdr_days = 365
        config.retention_export_days = 2
        config.retention_recording_days = 365
        self.dao.config.update(config)

    def _purge(self, days_to_keep):
        command = [
            '/bin/bash',
            '-c',
            f'wazo-purge-db -d {days_to_keep} &> /proc/1/fd/1',
        ]
        rc = self.docker_exec(
            command, service_name='purge-db', return_attr='returncode'
        )
        assert_that(rc, equal_to(0))


class TestCallLogPurger(_BasePurger):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.filesystem.create_file(
            cls.config_file,
            content='enabled_plugins: {purgers:{call-logs: true}}',
        )

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1))
    @call_log(**{'id': 2}, date=dt.utcnow() - td(days=2))
    @call_log(**{'id': 3}, date=dt.utcnow() - td(days=3))
    @recording(call_log_id=1, path='/tmp/1')
    @recording(call_log_id=2, path='/tmp/2')
    @recording(call_log_id=3, path='/tmp/3')
    @file_('/tmp/1', service_name='purge-db')
    @file_('/tmp/2', service_name='purge-db')
    @file_('/tmp/3', service_name='purge-db')
    def test_purger(self, *_):
        self._assert_len_call_logs(3)

        days_to_keep = 42
        self._purge(days_to_keep)
        self._assert_len_call_logs(3)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(self.filesystem.path_exists('/tmp/2'))
        assert_that(self.filesystem.path_exists('/tmp/3'))

        days_to_keep = 2
        self._purge(days_to_keep)
        self._assert_len_call_logs(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

        days_to_keep = 0
        self._purge(days_to_keep)
        self._assert_len_call_logs(0)
        assert_that(not self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

    def _assert_len_call_logs(self, number):
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(number))
        result = self.session.query(Recording).all()
        assert_that(result, has_length(number))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=2), tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 2}, date=dt.utcnow() - td(days=4), tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 3}, date=dt.utcnow() - td(days=2), tenant_uuid=OTHER_TENANT)
    @retention(tenant_uuid=MASTER_TENANT, cdr_days=3)
    def test_purger_by_retention(self, *_):
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(3))

        # When retention < default
        days_to_keep = 365
        self._purge(days_to_keep)
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(2))

        # When retention > default
        days_to_keep = 1
        self._purge(days_to_keep)
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(1))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1), tenant_uuid=MASTER_TENANT)
    @retention(tenant_uuid=MASTER_TENANT, cdr_days=0)
    def test_purger_when_retention_is_zero(self, *_):
        days_to_keep = 365
        self._purge(days_to_keep)
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(0))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1), tenant_uuid=MASTER_TENANT)
    def test_purger_when_default_days_is_customized(self, *_):
        config = self.dao.config.find_or_create()
        config.retention_cdr_days = 42
        self.dao.config.update(config)
        days_to_keep = 0

        self._purge(days_to_keep)

        result = self.session.query(CallLog).all()
        assert_that(result, has_length(1))


class TestExportPurger(_BasePurger):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.filesystem.create_file(
            cls.config_file,
            content='enabled_plugins: {purgers: {exports: true}}',
        )

    @export(requested_at=dt.utcnow() - td(days=1), path='/tmp/1')
    @export(requested_at=dt.utcnow() - td(days=2), path='/tmp/2')
    @export(requested_at=dt.utcnow() - td(days=3), path='/tmp/3')
    @file_('/tmp/1', service_name='purge-db')
    @file_('/tmp/2', service_name='purge-db')
    @file_('/tmp/3', service_name='purge-db')
    def test_purger(self, *_):
        self._assert_len_export(3)

        days_to_keep = 42
        self._purge(days_to_keep)
        self._assert_len_export(3)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(self.filesystem.path_exists('/tmp/2'))
        assert_that(self.filesystem.path_exists('/tmp/3'))

        days_to_keep = 2
        self._purge(days_to_keep)
        self._assert_len_export(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

        days_to_keep = 0
        self._purge(days_to_keep)
        self._assert_len_export(0)
        assert_that(not self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

    @export(
        requested_at=dt.utcnow() - td(days=1), path='/tmp/1', tenant_uuid=MASTER_TENANT
    )
    @export(
        requested_at=dt.utcnow() - td(days=3), path='/tmp/2', tenant_uuid=MASTER_TENANT
    )
    @export(
        requested_at=dt.utcnow() - td(days=1), path='/tmp/3', tenant_uuid=OTHER_TENANT
    )
    @retention(tenant_uuid=MASTER_TENANT, export_days=3)
    @file_('/tmp/1', service_name='purge-db')
    @file_('/tmp/2', service_name='purge-db')
    @file_('/tmp/3', service_name='purge-db')
    def test_purger_by_retention(self, *_):
        self._assert_len_export(3)

        # When retention < default
        days_to_keep = 365
        self._purge(days_to_keep)
        self._assert_len_export(2)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(self.filesystem.path_exists('/tmp/3'))

        # When retention > default
        days_to_keep = 1
        self._purge(days_to_keep)
        self._assert_len_export(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

    @export(
        requested_at=dt.utcnow() - td(days=2), path='/tmp/1', tenant_uuid=MASTER_TENANT
    )
    @retention(tenant_uuid=MASTER_TENANT, export_days=0)
    @file_('/tmp/1', service_name='purge-db')
    def test_purger_when_retention_is_zero(self, *_):
        days_to_keep = 365
        self._purge(days_to_keep)
        self._assert_len_export(0)
        assert_that(not self.filesystem.path_exists('/tmp/1'))

    @export(requested_at=dt.utcnow() - td(days=2), path='/tmp/42')
    def test_purger_when_file_not_on_filesystem(self, *_):
        assert_that(not self.filesystem.path_exists('/tmp/42'))
        days_to_keep = 0
        self._purge(days_to_keep)
        self._assert_len_export(0)
        assert_that(not self.filesystem.path_exists('/tmp/42'))

    @export(requested_at=dt.utcnow() - td(days=2), path=None)
    def test_purger_when_path_not_set(self, *_):
        days_to_keep = 0
        self._purge(days_to_keep)
        self._assert_len_export(0)

    @export(
        requested_at=dt.utcnow() - td(days=2), path='/tmp/1', tenant_uuid=MASTER_TENANT
    )
    @file_('/tmp/1', service_name='purge-db')
    def test_purger_when_default_days_is_customized(self, *_):
        config = self.dao.config.find_or_create()
        config.retention_export_days = 42
        self.dao.config.update(config)
        days_to_keep = 0

        self._purge(days_to_keep)

        self._assert_len_export(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))

    def _assert_len_export(self, number):
        result = self.session.query(Export).all()
        assert_that(result, has_length(number))


class TestRecordingPurger(_BasePurger):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.filesystem.create_file(
            cls.config_file,
            content='enabled_plugins: {purgers:{recordings: true}}',
        )

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1))
    @call_log(**{'id': 2}, date=dt.utcnow() - td(days=2))
    @call_log(**{'id': 3}, date=dt.utcnow() - td(days=3))
    @recording(call_log_id=1, path='/tmp/1')
    @recording(call_log_id=2, path='/tmp/2')
    @recording(call_log_id=3, path='/tmp/3')
    @file_('/tmp/1', service_name='purge-db')
    @file_('/tmp/2', service_name='purge-db')
    @file_('/tmp/3', service_name='purge-db')
    def test_purger(self, *_):
        self._assert_len_recording_path(3)

        days_to_keep = 42
        self._purge(days_to_keep)
        self._assert_len_recording_path(3)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(self.filesystem.path_exists('/tmp/2'))
        assert_that(self.filesystem.path_exists('/tmp/3'))

        days_to_keep = 2
        self._purge(days_to_keep)
        self._assert_len_recording_path(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

        days_to_keep = 0
        self._purge(days_to_keep)
        self._assert_len_recording_path(0)
        assert_that(not self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=2), tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 2}, date=dt.utcnow() - td(days=4), tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 3}, date=dt.utcnow() - td(days=2), tenant_uuid=OTHER_TENANT)
    @recording(call_log_id=1, path='/tmp/1')
    @recording(call_log_id=2, path='/tmp/2')
    @recording(call_log_id=3, path='/tmp/3')
    @retention(tenant_uuid=MASTER_TENANT, recording_days=3)
    @file_('/tmp/1', service_name='purge-db')
    @file_('/tmp/2', service_name='purge-db')
    @file_('/tmp/3', service_name='purge-db')
    def test_purger_by_retention(self, *_):
        self._assert_len_recording_path(3)

        # When retention < default
        days_to_keep = 365
        self._purge(days_to_keep)
        self._assert_len_recording_path(2)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(self.filesystem.path_exists('/tmp/3'))

        # When retention > default
        days_to_keep = 1
        self._purge(days_to_keep)
        self._assert_len_recording_path(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))
        assert_that(not self.filesystem.path_exists('/tmp/2'))
        assert_that(not self.filesystem.path_exists('/tmp/3'))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1), tenant_uuid=MASTER_TENANT)
    @recording(call_log_id=1, path='/tmp/1')
    @retention(tenant_uuid=MASTER_TENANT, recording_days=0)
    @file_('/tmp/1', service_name='purge-db')
    def test_purger_when_retention_is_zero(self, *_):
        days_to_keep = 365
        self._purge(days_to_keep)
        self._assert_len_recording_path(0)
        assert_that(not self.filesystem.path_exists('/tmp/1'))

    @call_log(**{'id': 1})
    @recording(call_log_id=1, path='/tmp/1')
    def test_purger_when_file_not_on_filesystem(self, *_):
        assert_that(not self.filesystem.path_exists('/tmp/1'))
        days_to_keep = 0
        self._purge(days_to_keep)
        self._assert_len_recording_path(0)
        assert_that(not self.filesystem.path_exists('/tmp/1'))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1), tenant_uuid=MASTER_TENANT)
    @recording(call_log_id=1, path='/tmp/1')
    @file_('/tmp/1', service_name='purge-db')
    def test_purger_when_default_days_is_customizedd(self, *_):
        config = self.dao.config.find_or_create()
        config.retention_recording_days = 42
        self.dao.config.update(config)
        days_to_keep = 0

        self._purge(days_to_keep)

        self._assert_len_recording_path(1)
        assert_that(self.filesystem.path_exists('/tmp/1'))

    def _assert_len_recording_path(self, number):
        result = self.session.query(Recording).filter(Recording.path.isnot(None)).all()
        assert_that(result, has_length(number))

# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid
from hamcrest import assert_that, equal_to
from wazo_test_helpers import until

from .helpers.base import RawCelIntegrationTest
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy
from .helpers.constants import MASTER_TENANT, USER_1_UUID as USER_UUID


class TestMigration(RawCelIntegrationTest):
    asset = 'migration'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def setUp(self):
        super().setUp()
        self._reset_cel_database()

    def _reset_cel_database(self):
        self.restart_service('cel-postgres', signal='SIGINT')
        self.reset_clients()
        until.true(
            self.cel_database.is_up,
            timeout=5,
            message='cel-postgres did not come back up',
        )

    def test_migration_workflow(self):
        nb_call_logs = 10
        with self.cel_database.queries() as queries:
            for _ in range(nb_call_logs):
                call_log_id = self._insert_old_call_log(queries)
                self._insert_old_call_log_participant(queries, call_log_id)
            old_id_seq = self._get_old_call_log_id_seq(queries)

            assert_that(self._old_call_log_table_exists(queries))
            assert_that(self._old_call_log_participant_table_exists(queries))
            assert_that(self._old_call_log_participant_role_type_exists(queries))

        with self.no_call_logs():
            code = self._exec(['wazo-call-logd-migrate-db', '-i'])
            assert_that(code, equal_to(0))
            with self.database.queries() as queries:
                new_id_seq = self._get_call_log_id_seq(queries)
                assert_that(new_id_seq, equal_to(old_id_seq))

            code = self._exec(['wazo-call-logd-migrate-db'])
            assert_that(code, equal_to(0))
            with self.database.queries() as queries:
                count = self._count_call_log(queries)
                assert_that(count, equal_to(nb_call_logs))
                count = self._count_call_log_participant(queries)
                assert_that(count, equal_to(nb_call_logs))

            with self.cel_database.queries() as q:
                assert_that(not self._old_call_log_table_exists(q))
                assert_that(not self._old_call_log_participant_table_exists(q))
                assert_that(not self._old_call_log_participant_role_type_exists(q))

    def test_migration_already_done(self):
        code = self._exec(['wazo-call-logd-migrate-db', '-i'])
        assert_that(code, equal_to(0))

        code = self._exec(['wazo-call-logd-migrate-db'])
        assert_that(code, equal_to(0))

        code = self._exec(['wazo-call-logd-migrate-db', '-i'])
        assert_that(code, equal_to(2))

        code = self._exec(['wazo-call-logd-migrate-db'])
        assert_that(code, equal_to(2))

    def test_exceeds_max_entries(self):
        nb_call_logs = 2
        with self.cel_database.queries() as queries:
            for _ in range(nb_call_logs):
                self._insert_old_call_log(queries)

        code = self._exec(['wazo-call-logd-migrate-db', '-m', '1'])
        assert_that(code, equal_to(3))

    def test_migrate_index_overwrite_previous_value(self):
        nb_call_logs = 2
        with self.cel_database.queries() as queries:
            for _ in range(nb_call_logs):
                self._insert_old_call_log(queries)
            old_id_seq = self._get_old_call_log_id_seq(queries)

        code = self._exec(['wazo-call-logd-migrate-db', '-i'])
        assert_that(code, equal_to(0))
        with self.database.queries() as queries:
            new_id_seq = self._get_call_log_id_seq(queries)
            assert_that(new_id_seq, equal_to(old_id_seq))

            queries.insert_call_log()
            new_id_seq = self._get_call_log_id_seq(queries)
            assert_that(new_id_seq, equal_to(old_id_seq + 1))

        code = self._exec(['wazo-call-logd-migrate-db', '-i'])
        assert_that(code, equal_to(0))
        with self.database.queries() as queries:
            new_id_seq = self._get_call_log_id_seq(queries)
            assert_that(new_id_seq, equal_to(old_id_seq))

    def _exec(self, command):
        return self.docker_exec(command, return_attr='returncode')

    def _insert_old_call_log(self, queries):
        session = queries.Session()
        query = f'''
        INSERT INTO call_log
        (date, tenant_uuid)
        VALUES
        ('2021-01-01','{MASTER_TENANT}')
        RETURNING id
        '''
        result = session.execute(query)
        call_log_id = result.fetchone()[0]
        session.commit()
        return call_log_id

    def _insert_old_call_log_participant(self, queries, call_log_id):
        session = queries.Session()
        uuid_ = uuid.uuid4()
        query = f'''
        INSERT INTO call_log_participant
        (uuid, call_log_id, user_uuid, role)
        VALUES
        ('{uuid_}', {call_log_id}, '{USER_UUID}', 'source');
        '''
        session.execute(query)
        session.commit()

    def _get_old_call_log_id_seq(self, queries):
        session = queries.Session()
        query = 'SELECT last_value FROM call_log_id_seq;'
        id_seq = session.execute(query).fetchone()[0]
        session.commit()
        return id_seq

    def _get_call_log_id_seq(self, queries):
        session = queries.Session()
        query = 'SELECT last_value FROM call_logd_call_log_id_seq;'
        id_seq = session.execute(query).fetchone()[0]
        session.commit()
        return id_seq

    def _count_call_log(self, queries):
        session = queries.Session()
        query = 'SELECT count(*) FROM call_logd_call_log;'
        count = session.execute(query).fetchone()[0]
        session.commit()
        return count

    def _count_call_log_participant(self, queries):
        session = queries.Session()
        query = 'SELECT count(*) FROM call_logd_call_log_participant;'
        count = session.execute(query).fetchone()[0]
        session.commit()
        return count

    def _old_call_log_table_exists(self, queries):
        session = queries.Session()
        query = "SELECT to_regclass('call_log');"
        result = session.execute(query).fetchone()[0]
        session.commit()
        return result

    def _old_call_log_participant_table_exists(self, queries):
        session = queries.Session()
        query = "SELECT to_regclass('call_log_participant');"
        result = session.execute(query).fetchone()[0]
        session.commit()
        return result

    def _old_call_log_participant_role_type_exists(self, queries):
        session = queries.Session()
        query = "SELECT to_regtype('call_log_participant_role');"
        result = session.execute(query).fetchone()[0]
        session.commit()
        return result

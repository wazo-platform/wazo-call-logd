# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime as dt
from hamcrest import (
    assert_that,
    contains_inanyorder,
    has_properties,
)
from xivo_test_helpers import until

from .helpers.base import raw_cels, RawCelIntegrationTest
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy


class TestRecordingGeneration(RawCelIntegrationTest):

    asset = 'base'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    @raw_cels(
        '''\
eventtype        | eventtime              | channame            | uniqueid      | linkedid     | extra
-----------------+------------------------+---------------------+---------------+--------------+---------------------------------------------------------------
CHAN_START       | 2021-01-01 00:00:00.01 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
APP_START        | 2021-01-01 00:00:00.02 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_START       | 2021-01-01 00:00:00.03 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_START | 2021-01-01 00:00:00.04 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"filename":"/tmp/foobar.wav","mixmonitor_id":"0x000000000001"}
ANSWER           | 2021-01-01 00:00:00.05 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
ANSWER           | 2021-01-01 00:00:00.06 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.07 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.08 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_STOP  | 2021-01-01 00:00:00.09 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"filename":"/tmp/foobar.wav","mixmonitor_id":"0x000000000001"}
BRIDGE_EXIT      | 2021-01-01 00:00:00.10 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.11 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.12 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
BRIDGE_EXIT      | 2021-01-01 00:00:00.13 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.14 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.15 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
LINKEDID_END     | 2021-01-01 00:00:00.16 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
    '''
    )
    def test_simple_mixmonitor(self):
        self._assert_last_recordings_match(
            '1000000000.1',
            has_properties(
                start_time=dt.fromisoformat('2021-01-01 00:00:00.040000+00:00'),
                end_time=dt.fromisoformat('2021-01-01 00:00:00.090000+00:00'),
                path='/tmp/foobar.wav',
            ),
        )

    @raw_cels(
        '''\
eventtype        | eventtime              | channame            | uniqueid      | linkedid     | extra
-----------------+------------------------+---------------------+---------------+--------------+-------
CHAN_START       | 2021-01-01 00:00:00.01 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
APP_START        | 2021-01-01 00:00:00.02 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_START       | 2021-01-01 00:00:00.03 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_START | 2021-01-01 00:00:00.04 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
ANSWER           | 2021-01-01 00:00:00.05 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
ANSWER           | 2021-01-01 00:00:00.06 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.07 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.08 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_STOP  | 2021-01-01 00:00:00.09 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
BRIDGE_EXIT      | 2021-01-01 00:00:00.10 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.11 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.12 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
BRIDGE_EXIT      | 2021-01-01 00:00:00.13 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.14 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.15 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
LINKEDID_END     | 2021-01-01 00:00:00.16 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
    '''
    )
    def test_missing_mixmonitor_extra(self):
        self._assert_last_recordings_match('1000000000.1')

    @raw_cels(
        '''\
eventtype        | eventtime              | channame            | uniqueid      | linkedid     | extra
-----------------+------------------------+---------------------+---------------+--------------+---------------------------------------------------------------
CHAN_START       | 2021-01-01 00:00:00.01 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
MIXMONITOR_START | 2021-01-01 00:00:00.02 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 | {"filename":"/tmp/foobar1.wav","mixmonitor_id":"0x000000000001"}
APP_START        | 2021-01-01 00:00:00.03 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_START       | 2021-01-01 00:00:00.04 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_START | 2021-01-01 00:00:00.05 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"filename":"/tmp/foobar2.wav","mixmonitor_id":"0x000000000002"}
ANSWER           | 2021-01-01 00:00:00.06 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
ANSWER           | 2021-01-01 00:00:00.07 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.08 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.09 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
BRIDGE_EXIT      | 2021-01-01 00:00:00.10 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.11 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.12 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
BRIDGE_EXIT      | 2021-01-01 00:00:00.13 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.14 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.15 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
LINKEDID_END     | 2021-01-01 00:00:00.16 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
    '''
    )
    def test_missing_mixmonitor_stop(self):
        self._assert_last_recordings_match(
            '1000000000.1',
            has_properties(
                start_time=dt.fromisoformat('2021-01-01 00:00:00.020000+00:00'),
                end_time=dt.fromisoformat('2021-01-01 00:00:00.150000+00:00'),
                path='/tmp/foobar1.wav',
            ),
            has_properties(
                start_time=dt.fromisoformat('2021-01-01 00:00:00.050000+00:00'),
                end_time=dt.fromisoformat('2021-01-01 00:00:00.120000+00:00'),
                path='/tmp/foobar2.wav',
            ),
        )

    @raw_cels(
        '''\
eventtype        | eventtime              | channame            | uniqueid      | linkedid     | extra
-----------------+------------------------+---------------------+---------------+--------------+---------------------------------------------------------------
CHAN_START       | 2021-01-01 00:00:00.01 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
MIXMONITOR_START | 2021-01-01 00:00:00.02 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 | {"filename":"/tmp/foobar1.wav","mixmonitor_id":"0x000000000001"}
APP_START        | 2021-01-01 00:00:00.03 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_START       | 2021-01-01 00:00:00.04 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_START | 2021-01-01 00:00:00.05 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"filename":"/tmp/foobar2.wav","mixmonitor_id":"0x000000000002"}
ANSWER           | 2021-01-01 00:00:00.06 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
ANSWER           | 2021-01-01 00:00:00.07 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.08 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
BRIDGE_ENTER     | 2021-01-01 00:00:00.09 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
MIXMONITOR_STOP  | 2021-01-01 00:00:00.10 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 | {"filename":"/tmp/foobar1.wav","mixmonitor_id":"0x000000000001"}
MIXMONITOR_STOP  | 2021-01-01 00:00:00.11 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"filename":"/tmp/foobar2.wav","mixmonitor_id":"0x000000000002"}
BRIDGE_EXIT      | 2021-01-01 00:00:00.12 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.13 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.14 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 |
BRIDGE_EXIT      | 2021-01-01 00:00:00.15 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
HANGUP           | 2021-01-01 00:00:00.16 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
CHAN_END         | 2021-01-01 00:00:00.17 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
LINKEDID_END     | 2021-01-01 00:00:00.18 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 |
    '''
    )
    def test_multiple_mixmonitors(self):
        self._assert_last_recordings_match(
            '1000000000.1',
            has_properties(
                start_time=dt.fromisoformat('2021-01-01 00:00:00.020000+00:00'),
                end_time=dt.fromisoformat('2021-01-01 00:00:00.100000+00:00'),
                path='/tmp/foobar1.wav',
            ),
            has_properties(
                start_time=dt.fromisoformat('2021-01-01 00:00:00.050000+00:00'),
                end_time=dt.fromisoformat('2021-01-01 00:00:00.110000+00:00'),
                path='/tmp/foobar2.wav',
            ),
        )

    def _get_last_call_log_generated(self):
        with self.cel_database.queries() as queries:

            def call_log_generated():
                return queries.find_last_call_log() is not None

            until.true(call_log_generated, tries=5)
            return queries.find_last_call_log().id

    def _assert_last_recordings_match(self, linkedid, *expected):
        with self.no_recordings(), self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)
            call_log_id = self._get_last_call_log_generated()

            with self.database.queries() as queries:
                recordings = queries.find_all_recordings(call_log_id=call_log_id)
                assert_that(recordings, contains_inanyorder(*expected))

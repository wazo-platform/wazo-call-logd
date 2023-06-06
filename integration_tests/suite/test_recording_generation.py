# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime as dt

from hamcrest import assert_that, contains_inanyorder, has_properties
from wazo_test_helpers import until

from .helpers.base import RawCelIntegrationTest, raw_cels
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
MIXMONITOR_STOP  | 2021-01-01 00:00:00.09 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"mixmonitor_id":"0x000000000001"}
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
MIXMONITOR_STOP  | 2021-01-01 00:00:00.10 | SIP/aaaaaa-00000001 | 1000000000.01 | 1000000000.1 | {"mixmonitor_id":"0x000000000001"}
MIXMONITOR_STOP  | 2021-01-01 00:00:00.11 | SIP/bbbbbb-00000002 | 1000000000.02 | 1000000000.1 | {"mixmonitor_id":"0x000000000002"}
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

    @raw_cels(
        '''\
    eventtype     |           eventtime           |     cid_name      | cid_num |                exten                 |     context     |                               channame                                |   uniqueid   |   linkedid   |                                                        appdata                                                        |                                                                               extra
------------------+-------------------------------+-------------------+---------+--------------------------------------+-----------------+-----------------------------------------------------------------------+--------------+--------------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------
 CHAN_START       | 2022-07-04 09:18:59.712195-04 |                   |         | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 |                                                                                                                       |
 CHAN_START       | 2022-07-04 09:18:59.712302-04 |                   |         | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 |                                                                                                                       |
 APP_START        | 2022-07-04 09:18:59.761707-04 | 1015              | 1015    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 | PJSIP/XFGkT4NB/sip:XFGkT4NB@10.37.0.236:1036                                                                          |
 CHAN_START       | 2022-07-04 09:18:59.76362-04  | Anastasia Romanov | 1011    | s                                    | inside          | PJSIP/XFGkT4NB-00000000                                               | 1656940739.2 | 1656940739.0 |                                                                                                                       |
 ANSWER           | 2022-07-04 09:19:01.815884-04 | Anastasia Romanov | 1011    | def42192-837a-41e0-aa4e-86390e46eb17 | inside          | PJSIP/XFGkT4NB-00000000                                               | 1656940739.2 | 1656940739.0 | (Outgoing Line)                                                                                                       |
 ANSWER           | 2022-07-04 09:19:01.817116-04 | 1015              | 1015    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 | PJSIP/XFGkT4NB/sip:XFGkT4NB@10.37.0.236:1036                                                                          |
 ANSWER           | 2022-07-04 09:19:01.818349-04 | Anastasia Romanov | 1011    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | (Outgoing Line)                                                                                                       |
 BRIDGE_ENTER     | 2022-07-04 09:19:01.837098-04 | Anastasia Romanov | 1011    |                                      | inside          | PJSIP/XFGkT4NB-00000000                                               | 1656940739.2 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"bridge_id":"14b1a919-1062-490a-b80c-9795a35d70ee","bridge_technology":"simple_bridge"}
 BRIDGE_ENTER     | 2022-07-04 09:19:01.85154-04  | 1015              | 1015    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 | PJSIP/XFGkT4NB/sip:XFGkT4NB@10.37.0.236:1036                                                                          | {"bridge_id":"14b1a919-1062-490a-b80c-9795a35d70ee","bridge_technology":"simple_bridge"}
 MIXMONITOR_START | 2022-07-04 09:19:02.984268-04 | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | /var/lib/wazo/sounds/tenants/2c34c282-433e-4bb8-8d56-fec14ff7e1e9/monitor/8976fcad-0233-4755-b28e-8e3845b0959e.wav,pP | {"filename":"/var/lib/wazo/sounds/tenants/2c34c282-433e-4bb8-8d56-fec14ff7e1e9/monitor/8976fcad-0233-4755-b28e-8e3845b0959e.wav","mixmonitor_id":"0x7f452802ebd0"}
 APP_START        | 2022-07-04 09:19:03.07498-04  | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | PJSIP/VRi5c6mT/sip:VRi5c6mT@10.37.0.235:5060,30,b(wazo-pre-dial-hooks^s^1)                                            |
 CHAN_START       | 2022-07-04 09:19:03.076867-04 | Olga Romanov      | 1015    | s                                    | inside          | PJSIP/VRi5c6mT-00000001                                               | 1656940743.3 | 1656940739.0 |                                                                                                                       |
 ANSWER           | 2022-07-04 09:19:04.710762-04 | Olga Romanov      | 1015    | s                                    | inside          | PJSIP/VRi5c6mT-00000001                                               | 1656940743.3 | 1656940739.0 | (Outgoing Line)                                                                                                       |
 BRIDGE_ENTER     | 2022-07-04 09:19:04.713051-04 | Olga Romanov      | 1015    |                                      | inside          | PJSIP/VRi5c6mT-00000001                                               | 1656940743.3 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"bridge_id":"30c6fad1-e053-4f52-8c97-771313a45980","bridge_technology":"simple_bridge"}
 BRIDGE_ENTER     | 2022-07-04 09:19:04.71501-04  | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | PJSIP/VRi5c6mT/sip:VRi5c6mT@10.37.0.235:5060,30,b(wazo-pre-dial-hooks^s^1)                                            | {"bridge_id":"30c6fad1-e053-4f52-8c97-771313a45980","bridge_technology":"simple_bridge"}
 BRIDGE_EXIT      | 2022-07-04 09:19:15.108608-04 | Olga Romanov      | 1015    |                                      | inside          | PJSIP/VRi5c6mT-00000001                                               | 1656940743.3 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"bridge_id":"30c6fad1-e053-4f52-8c97-771313a45980","bridge_technology":"simple_bridge"}
 BRIDGE_EXIT      | 2022-07-04 09:19:15.111585-04 | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | PJSIP/VRi5c6mT/sip:VRi5c6mT@10.37.0.235:5060,30,b(wazo-pre-dial-hooks^s^1)                                            | {"bridge_id":"30c6fad1-e053-4f52-8c97-771313a45980","bridge_technology":"simple_bridge"}
 HANGUP           | 2022-07-04 09:19:15.112995-04 | Olga Romanov      | 1015    |                                      | inside          | PJSIP/VRi5c6mT-00000001                                               | 1656940743.3 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"hangupcause":16,"hangupsource":"PJSIP/VRi5c6mT-00000001","dialstatus":""}
 CHAN_END         | 2022-07-04 09:19:15.112995-04 | Olga Romanov      | 1015    |                                      | inside          | PJSIP/VRi5c6mT-00000001                                               | 1656940743.3 | 1656940739.0 | (Outgoing Line)                                                                                                       |
 BRIDGE_EXIT      | 2022-07-04 09:19:15.118467-04 | Olga Romanov      | 1015    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 | PJSIP/XFGkT4NB/sip:XFGkT4NB@10.37.0.236:1036                                                                          | {"bridge_id":"14b1a919-1062-490a-b80c-9795a35d70ee","bridge_technology":"simple_bridge"}
 HANGUP           | 2022-07-04 09:19:15.119501-04 | Olga Romanov      | 1015    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 |                                                                                                                       | {"hangupcause":16,"hangupsource":"","dialstatus":"ANSWER"}
 CHAN_END         | 2022-07-04 09:19:15.119501-04 | Olga Romanov      | 1015    | def42192-837a-41e0-aa4e-86390e46eb17 | usersharedlines | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;2 | 1656940739.1 | 1656940739.0 |                                                                                                                       |
 BRIDGE_EXIT      | 2022-07-04 09:19:15.121665-04 | Anastasia Romanov | 1011    |                                      | inside          | PJSIP/XFGkT4NB-00000000                                               | 1656940739.2 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"bridge_id":"14b1a919-1062-490a-b80c-9795a35d70ee","bridge_technology":"simple_bridge"}
 HANGUP           | 2022-07-04 09:19:15.1249-04   | Anastasia Romanov | 1011    |                                      | inside          | PJSIP/XFGkT4NB-00000000                                               | 1656940739.2 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"hangupcause":16,"hangupsource":"","dialstatus":""}
 CHAN_END         | 2022-07-04 09:19:15.1249-04   | Anastasia Romanov | 1011    |                                      | inside          | PJSIP/XFGkT4NB-00000000                                               | 1656940739.2 | 1656940739.0 | (Outgoing Line)                                                                                                       |
 HANGUP           | 2022-07-04 09:19:15.129565-04 | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | (Outgoing Line)                                                                                                       | {"hangupcause":16,"hangupsource":"PJSIP/VRi5c6mT-00000001","dialstatus":"ANSWER"}
 CHAN_END         | 2022-07-04 09:19:15.129565-04 | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | (Outgoing Line)                                                                                                       |
 LINKEDID_END     | 2022-07-04 09:19:15.129565-04 | Anastasia Romanov | 1011    | s                                    | user            | Local/def42192-837a-41e0-aa4e-86390e46eb17@usersharedlines-00000000;1 | 1656940739.0 | 1656940739.0 | (Outgoing Line)                                                                                                       |

        '''
    )
    def test_recorded_originate(self):
        self._assert_last_recordings_match(
            '1656940739.0',
            has_properties(
                start_time=dt.fromisoformat('2022-07-04 13:19:02.984268+00:00'),
                end_time=dt.fromisoformat('2022-07-04 13:19:15.124900+00:00'),
                path='/var/lib/wazo/sounds/tenants/2c34c282-433e-4bb8-8d56-fec14ff7e1e9/monitor/8976fcad-0233-4755-b28e-8e3845b0959e.wav',
            ),
        )

    def _get_last_call_log_generated(self):
        with self.database.queries() as queries:

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

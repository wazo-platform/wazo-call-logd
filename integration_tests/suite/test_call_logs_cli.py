# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from datetime import (
    datetime as dt,
    timedelta as td,
)

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    contains_string,
    empty,
    has_properties,
)
from xivo_dao.alchemy.call_log import CallLog
from wazo_call_logd.database.models import Recording

from .helpers.base import cdr, raw_cels, RawCelIntegrationTest
from .helpers.constants import NOW
from .helpers.database import call_logs, recording
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy


class TestCallLogGeneration(RawCelIntegrationTest):

    asset = 'base'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    @raw_cels(
        '''\
eventtype    | eventtime                  | cid_name | cid_num | exten | context | channame            |      uniqueid |      linkedid

CHAN_START   | 2015-06-18 14:17:15.314919 | Elès 45  | 1045    | 1001  | default | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
APP_START    | 2015-06-18 14:17:15.418728 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
CHAN_START   | 2015-06-18 14:17:15.42325  | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000030 | 1434651435.48 | 1434651435.47
ANSWER       | 2015-06-18 14:17:17.632403 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000030 | 1434651435.48 | 1434651435.47
ANSWER       | 2015-06-18 14:17:17.641401 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
BRIDGE_ENTER | 2015-06-18 14:17:17.642693 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
BRIDGE_ENTER | 2015-06-18 14:17:17.644112 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000030 | 1434651435.48 | 1434651435.47
BRIDGE_EXIT  | 2015-06-18 14:17:22.249479 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000030 | 1434651435.48 | 1434651435.47
HANGUP       | 2015-06-18 14:17:22.259363 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000030 | 1434651435.48 | 1434651435.47
CHAN_END     | 2015-06-18 14:17:22.260562 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000030 | 1434651435.48 | 1434651435.47
BRIDGE_EXIT  | 2015-06-18 14:17:22.261986 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
HANGUP       | 2015-06-18 14:17:22.263564 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
CHAN_END     | 2015-06-18 14:17:22.264727 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
LINKEDID_END | 2015-06-18 14:17:22.266043 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002f | 1434651435.47 | 1434651435.47
CHAN_START   | 2015-06-18 14:17:24.135378 | Elès 45  | 1045    | 1001  | default | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
APP_START    | 2015-06-18 14:17:24.938839 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
CHAN_START   | 2015-06-18 14:17:24.943746 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
ANSWER       | 2015-06-18 14:17:27.124748 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
ANSWER       | 2015-06-18 14:17:27.134133 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
BRIDGE_ENTER | 2015-06-18 14:17:27.135653 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
BRIDGE_ENTER | 2015-06-18 14:17:27.136997 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
BRIDGE_EXIT  | 2015-06-18 14:17:30.54609  | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
HANGUP       | 2015-06-18 14:17:30.556918 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
CHAN_END     | 2015-06-18 14:17:30.558334 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000031 | 1434651444.49 | 1434651444.49
BRIDGE_EXIT  | 2015-06-18 14:17:30.559702 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
HANGUP       | 2015-06-18 14:17:30.561057 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
CHAN_END     | 2015-06-18 14:17:30.562551 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
LINKEDID_END | 2015-06-18 14:17:30.563808 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000032 | 1434651444.50 | 1434651444.49
CHAN_START   | 2015-06-18 14:17:32.195429 | Elès 45  | 1045    | 1001  | default | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
APP_START    | 2015-06-18 14:17:32.296484 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
CHAN_START   | 2015-06-18 14:17:32.301413 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000034 | 1434651452.52 | 1434651452.51
ANSWER       | 2015-06-18 14:17:34.066573 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000034 | 1434651452.52 | 1434651452.51
ANSWER       | 2015-06-18 14:17:34.079356 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
BRIDGE_ENTER | 2015-06-18 14:17:34.080717 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
BRIDGE_ENTER | 2015-06-18 14:17:34.082069 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000034 | 1434651452.52 | 1434651452.51
BRIDGE_EXIT  | 2015-06-18 14:17:37.528919 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000034 | 1434651452.52 | 1434651452.51
HANGUP       | 2015-06-18 14:17:37.538345 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000034 | 1434651452.52 | 1434651452.51
CHAN_END     | 2015-06-18 14:17:37.539689 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000034 | 1434651452.52 | 1434651452.51
BRIDGE_EXIT  | 2015-06-18 14:17:37.54106  | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
HANGUP       | 2015-06-18 14:17:37.542328 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
CHAN_END     | 2015-06-18 14:17:37.544217 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
LINKEDID_END | 2015-06-18 14:17:37.545342 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000033 | 1434651452.51 | 1434651452.51
        '''
    )
    def test_does_not_process_more_cel_than_cel_count_param(self):
        with self.no_call_logs():
            self.docker_exec(['wazo-call-logs', '--cel-count', '12'])

            with self.cel_database.queries() as queries:
                call_logs = queries.find_all_call_log()
                assert_that(
                    call_logs,
                    contains_inanyorder(
                        has_properties(
                            date=datetime.fromisoformat(
                                '2015-06-18 14:17:32.195429+00:00'
                            ),
                            date_answer=datetime.fromisoformat(
                                '2015-06-18 14:17:34.080717+00:00'
                            ),
                            date_end=datetime.fromisoformat(
                                '2015-06-18 14:17:37.544217+00:00'
                            ),
                        )
                    ),
                )

    @raw_cels(
        '''\
eventtype    | eventtime           | cid_name      | cid_num | exten | context | channame            |     uniqueid |     linkedid

CHAN_START   | 2013-01-01 08:00:00 | Bob Marley    |    1002 | 1001  | default | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
APP_START    | 2013-01-01 08:00:01 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
CHAN_START   | 2013-01-01 08:00:02 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
ANSWER       | 2013-01-01 08:00:03 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
ANSWER       | 2013-01-01 08:00:04 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
BRIDGE_START | 2013-01-01 08:00:05 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
BRIDGE_END   | 2013-01-01 08:00:06 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
HANGUP       | 2013-01-01 08:00:07 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
CHAN_END     | 2013-01-01 08:00:08 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
HANGUP       | 2013-01-01 08:00:09 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
CHAN_END     | 2013-01-01 08:00:10 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
LINKEDID_END | 2013-01-01 08:00:11 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
CHAN_START   | 2013-01-01 09:00:00 | Bob Marley    |    1002 | 1001  | default | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
APP_START    | 2013-01-01 09:00:01 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
CHAN_START   | 2013-01-01 09:00:02 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994781.2 | 1375994781.1
ANSWER       | 2013-01-01 09:00:03 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994781.2 | 1375994781.1
ANSWER       | 2013-01-01 09:00:04 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
BRIDGE_START | 2013-01-01 09:00:05 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
BRIDGE_END   | 2013-01-01 09:00:06 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
HANGUP       | 2013-01-01 09:00:07 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994781.2 | 1375994781.1
CHAN_END     | 2013-01-01 09:00:08 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994781.2 | 1375994781.1
HANGUP       | 2013-01-01 09:00:09 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
CHAN_END     | 2013-01-01 09:00:10 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
LINKEDID_END | 2013-01-01 09:00:11 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994781.1 | 1375994781.1
CHAN_START   | 2013-01-01 10:00:00 | Bob Marley    |    1002 | 1001  | default | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
APP_START    | 2013-01-01 10:00:01 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
CHAN_START   | 2013-01-01 10:00:02 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994782.2 | 1375994782.1
ANSWER       | 2013-01-01 10:00:03 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994782.2 | 1375994782.1
ANSWER       | 2013-01-01 10:00:04 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
BRIDGE_START | 2013-01-01 10:00:05 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
BRIDGE_END   | 2013-01-01 10:00:06 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
HANGUP       | 2013-01-01 10:00:07 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994782.2 | 1375994782.1
CHAN_END     | 2013-01-01 10:00:08 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994782.2 | 1375994782.1
HANGUP       | 2013-01-01 10:00:09 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
CHAN_END     | 2013-01-01 10:00:10 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
LINKEDID_END | 2013-01-01 10:00:11 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994782.1 | 1375994782.1
        '''
    )
    def test_process_cel_after_those_already_processed(self):
        with self.no_call_logs():
            self.docker_exec(['wazo-call-logs', '--cel-count', '12'])
            self.docker_exec(['wazo-call-logs', '--cel-count', '12'])

            with self.cel_database.queries() as queries:
                call_logs = queries.find_all_call_log()
                assert_that(
                    call_logs,
                    contains_inanyorder(
                        has_properties(
                            date=datetime.fromisoformat('2013-01-01 09:00:00+00:00'),
                            date_answer=datetime.fromisoformat(
                                '2013-01-01 09:00:05+00:00'
                            ),
                            date_end=datetime.fromisoformat(
                                '2013-01-01 09:00:10+00:00'
                            ),
                        ),
                        has_properties(
                            date=datetime.fromisoformat('2013-01-01 10:00:00+00:00'),
                            date_answer=datetime.fromisoformat(
                                '2013-01-01 10:00:05+00:00'
                            ),
                            date_end=datetime.fromisoformat(
                                '2013-01-01 10:00:10+00:00'
                            ),
                        ),
                    ),
                )

    @raw_cels(
        '''\
eventtype    | eventtime           | cid_name      | cid_num | exten | context | channame            |     uniqueid |     linkedid

CHAN_START   | 2013-01-01 08:00:00 | Bob Marley    |    1002 | 1001  | default | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
APP_START    | 2013-01-01 08:00:01 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
CHAN_START   | 2013-01-01 08:00:02 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
ANSWER       | 2013-01-01 08:00:03 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
ANSWER       | 2013-01-01 08:00:04 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
BRIDGE_START | 2013-01-01 08:00:05 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
BRIDGE_END   | 2013-01-01 08:00:06 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
HANGUP       | 2013-01-01 08:00:07 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
CHAN_END     | 2013-01-01 08:00:08 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1
HANGUP       | 2013-01-01 08:00:09 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
CHAN_END     | 2013-01-01 08:00:10 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
LINKEDID_END | 2013-01-01 08:00:11 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1
        '''
    )
    def test_process_complete_call(self):
        with self.no_call_logs():
            self.docker_exec(['wazo-call-logs', '--cel-count', '1'])

            with self.cel_database.queries() as queries:
                call_logs = queries.find_all_call_log()
                assert_that(
                    call_logs,
                    contains_inanyorder(
                        has_properties(
                            date=datetime.fromisoformat('2013-01-01 08:00:00+00:00'),
                            date_answer=datetime.fromisoformat(
                                '2013-01-01 08:00:05+00:00'
                            ),
                            date_end=datetime.fromisoformat(
                                '2013-01-01 08:00:10+00:00'
                            ),
                        ),
                    ),
                )

    @call_logs(
        [
            {
                'id': 42,
                'date': '2013-01-01 08:00:00',
                'date_answer': '2013-01-01 08:00:05',
                'date_end': None,
                'source_name': 'Bob Marley.',
                'source_exten': '1002',
                'destination_exten': '6666',
            }
        ]
    )
    @raw_cels(
        '''\
eventtype    | eventtime           | cid_name      | cid_num | exten | context | channame            |     uniqueid |     linkedid | call_log_id

CHAN_START   | 2013-01-01 08:00:00 | Bob Marley    |    1002 | 1001  | default | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |          42
APP_START    | 2013-01-01 08:00:01 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |          42
CHAN_START   | 2013-01-01 08:00:02 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1 |          42
ANSWER       | 2013-01-01 08:00:03 | Alice Aglisse |    1001 | s     | default | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1 |          42
ANSWER       | 2013-01-01 08:00:04 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |          42
BRIDGE_START | 2013-01-01 08:00:05 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |          42
BRIDGE_END   | 2013-01-01 08:00:06 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |
HANGUP       | 2013-01-01 08:00:07 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1 |
CHAN_END     | 2013-01-01 08:00:08 | Alice Aglisse |    1001 |       | user    | SIP/hg63xv-00000013 | 1375994780.2 | 1375994780.1 |
HANGUP       | 2013-01-01 08:00:09 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |
CHAN_END     | 2013-01-01 08:00:10 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |
LINKEDID_END | 2013-01-01 08:00:11 | Bob Marley    |    1002 | s     | user    | SIP/z77kvm-00000028 | 1375994780.1 | 1375994780.1 |
        '''
    )
    def test_process_partially_processed_call(self):
        with self.no_call_logs():
            self.docker_exec(['wazo-call-logs', '--cel-count', '20'])

            with self.cel_database.queries() as queries:
                call_logs = queries.find_all_call_log()
                assert_that(
                    call_logs,
                    contains_inanyorder(
                        has_properties(
                            date=datetime.fromisoformat('2013-01-01 08:00:00+00:00'),
                            date_answer=datetime.fromisoformat(
                                '2013-01-01 08:00:05+00:00'
                            ),
                            date_end=datetime.fromisoformat(
                                '2013-01-01 08:00:10+00:00'
                            ),
                            source_name='Bob Marley',
                            source_exten='1002',
                            destination_exten='1001',
                            source_line_identity='sip/z77kvm',
                            destination_line_identity='sip/hg63xv',
                        ),
                    ),
                )

    def test_only_one_cli_can_be_executed(self):
        output = self.docker_exec(['sh', '-c', 'wazo-call-logs & wazo-call-logs'])
        assert_that(
            output.decode('utf-8'),
            contains_string('An other instance of ourself is probably running'),
        )

    @call_logs([cdr(id_=1)])
    @recording(call_log_id=1)
    def test_delete_all(self, _):
        self.docker_exec(['wazo-call-logs', 'delete', '--all'])
        result = self.session.query(Recording).all()
        assert_that(result, empty())

    @call_logs([cdr(id_=1, start_time=NOW)])
    @recording(call_log_id=1)
    @call_logs([cdr(id_=2, start_time=NOW - td(days=2))])
    @recording(call_log_id=2)
    def test_delete_older(self, *_):
        print(self.docker_exec(['wazo-call-logs', 'delete', '--days', '1']))

        result = self.cel_session.query(CallLog).all()
        assert_that(result, contains(has_properties(id=2)))

        result = self.session.query(Recording).all()
        assert_that(result, contains(has_properties(call_log_id=2)))

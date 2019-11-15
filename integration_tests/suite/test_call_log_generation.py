# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    has_entries,
    has_key,
    has_properties,
    is_,
    not_,
    none,
)
from xivo_test_helpers import until

from .helpers.base import IntegrationTest
from .helpers.confd import MockContext, MockLine, MockUser
from .helpers.constants import USER_1_UUID, USER_2_UUID, USERS_TENANT, SERVICE_TENANT
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy


# this decorator takes the output of a psql and changes it into a list of dict
def raw_cels(cel_output):
    cels = []
    lines = cel_output.strip().split('\n')
    columns = [field.strip() for field in lines[0].split('|')]
    for line in lines[2:]:
        cel = [field.strip() for field in line.split('|')]
        cels.append(dict(zip(columns, cel)))

    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cels(cels):
                return func(self, *args, **kwargs)

        return wrapped_function

    return _decorate


class TestCallLogGeneration(IntegrationTest):

    asset = 'base'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def setUp(self):
        self.bus = self.make_bus()
        self.confd = self.make_confd()
        self.confd.reset()

    @raw_cels(
        '''\
eventtype    | eventtime                  | cid_name | cid_num | cid_ani | exten    | context                    | channame                                             | appname  | appdata                                               | uniqueid      | linkedid      | peer                                                 | extra
LINKEDID_END | 2019-08-28 15:29:32.275896 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000019                              | AppDial2 | (Outgoing Line)                                       | 1567020561.37 | 1567020560.33 |                                                      |
CHAN_END     | 2019-08-28 15:29:32.269711 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000019                              | AppDial2 | (Outgoing Line)                                       | 1567020561.37 | 1567020560.33 |                                                      |
HANGUP       | 2019-08-28 15:29:32.261363 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000019                              | AppDial2 | (Outgoing Line)                                       | 1567020561.37 | 1567020560.33 |                                                      | {"hangupcause":16,"hangupsource":"","dialstatus":""}
BRIDGE_EXIT  | 2019-08-28 15:29:32.255203 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000019                              | Stasis   | dial_mobile,join,67b292be-e7dd-4d73-8c1a-fc73461dc79a | 1567020561.37 | 1567020560.33 |                                                      | {"bridge_id":"67b292be-e7dd-4d73-8c1a-fc73461dc79a","bridge_technology":"simple_bridge"}
CHAN_END     | 2019-08-28 15:29:32.234511 | Alice    | 1001    | 1001    | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;2 |          |                                                       | 1567020561.35 | 1567020560.33 |                                                      |
HANGUP       | 2019-08-28 15:29:32.229211 | Alice    | 1001    | 1001    | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;2 |          |                                                       | 1567020561.35 | 1567020560.33 |                                                      | {"hangupcause":16,"hangupsource":"","dialstatus":""}
BRIDGE_EXIT  | 2019-08-28 15:29:32.224539 | Alice    | 1001    | 1001    | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;2 | Stasis   | dial_mobile,dial,ycetqvtr                             | 1567020561.35 | 1567020560.33 | PJSIP/ycetqvtr-00000019                              | {"bridge_id":"67b292be-e7dd-4d73-8c1a-fc73461dc79a","bridge_technology":"simple_bridge"}
CHAN_END     | 2019-08-28 15:29:32.219482 | Alice    | 1001    | 1001    | s        | user                       | PJSIP/qxqz31sq-00000017                              |          |                                                       | 1567020560.33 | 1567020560.33 |                                                      |
HANGUP       | 2019-08-28 15:29:32.21386  | Alice    | 1001    | 1001    | s        | user                       | PJSIP/qxqz31sq-00000017                              |          |                                                       | 1567020560.33 | 1567020560.33 |                                                      | {"hangupcause":16,"hangupsource":"PJSIP/qxqz31sq-00000017","dialstatus":"ANSWER"}
CHAN_END     | 2019-08-28 15:29:32.205737 | Alice    | 1001    |         |          | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | AppDial  | (Outgoing Line)                                       | 1567020561.34 | 1567020560.33 |                                                      |
HANGUP       | 2019-08-28 15:29:32.188355 | Alice    | 1001    |         |          | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | AppDial  | (Outgoing Line)                                       | 1567020561.34 | 1567020560.33 |                                                      | {"hangupcause":16,"hangupsource":"PJSIP/qxqz31sq-00000017","dialstatus":""}
BRIDGE_EXIT  | 2019-08-28 15:29:32.17354  | Alice    | 1001    |         |          | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | AppDial  | (Outgoing Line)                                       | 1567020561.34 | 1567020560.33 |                                                      | {"bridge_id":"0de77b8c-717e-4e61-b667-ce31e2666426","bridge_technology":"simple_bridge"}
BRIDGE_EXIT  | 2019-08-28 15:29:32.151658 | Alice    | 1001    | 1001    | s        | user                       | PJSIP/qxqz31sq-00000017                              | Dial     | Local/ycetqvtr@wazo_wait_for_registration,30,         | 1567020560.33 | 1567020560.33 | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | {"bridge_id":"0de77b8c-717e-4e61-b667-ce31e2666426","bridge_technology":"simple_bridge"}
BRIDGE_ENTER | 2019-08-28 15:29:26.663414 | Alice    | 1001    | 1001    | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;2 | Stasis   | dial_mobile,dial,ycetqvtr                             | 1567020561.35 | 1567020560.33 | PJSIP/ycetqvtr-00000019                              | {"bridge_id":"67b292be-e7dd-4d73-8c1a-fc73461dc79a","bridge_technology":"simple_bridge"}
BRIDGE_ENTER | 2019-08-28 15:29:26.635016 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000019                              | Stasis   | dial_mobile,join,67b292be-e7dd-4d73-8c1a-fc73461dc79a | 1567020561.37 | 1567020560.33 |                                                      | {"bridge_id":"67b292be-e7dd-4d73-8c1a-fc73461dc79a","bridge_technology":"simple_bridge"}
BRIDGE_ENTER | 2019-08-28 15:29:26.614724 | Alice    | 1001    | 1001    | s        | user                       | PJSIP/qxqz31sq-00000017                              | Dial     | Local/ycetqvtr@wazo_wait_for_registration,30,         | 1567020560.33 | 1567020560.33 | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | {"bridge_id":"0de77b8c-717e-4e61-b667-ce31e2666426","bridge_technology":"simple_bridge"}
BRIDGE_ENTER | 2019-08-28 15:29:26.605061 | Bob      | s       |         |          | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | AppDial  | (Outgoing Line)                                       | 1567020561.34 | 1567020560.33 |                                                      | {"bridge_id":"0de77b8c-717e-4e61-b667-ce31e2666426","bridge_technology":"simple_bridge"}
ANSWER       | 2019-08-28 15:29:26.599335 | Alice    | 1001    | 1001    | s        | user                       | PJSIP/qxqz31sq-00000017                              | Dial     | Local/ycetqvtr@wazo_wait_for_registration,30,         | 1567020560.33 | 1567020560.33 |                                                      |
ANSWER       | 2019-08-28 15:29:26.593743 | Bob      | s       |         | s        | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 | AppDial  | (Outgoing Line)                                       | 1567020561.34 | 1567020560.33 |                                                      |
ANSWER       | 2019-08-28 15:29:26.583625 | Alice    | 1001    | 1001    | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;2 | Stasis   | dial_mobile,dial,ycetqvtr                             | 1567020561.35 | 1567020560.33 |                                                      |
CHAN_END     | 2019-08-28 15:29:26.540774 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000018                              | AppDial2 | (Outgoing Line)                                       | 1567020561.36 | 1567020560.33 |                                                      |
HANGUP       | 2019-08-28 15:29:26.533224 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000018                              | AppDial2 | (Outgoing Line)                                       | 1567020561.36 | 1567020560.33 |                                                      | {"hangupcause":16,"hangupsource":"","dialstatus":""}
ANSWER       | 2019-08-28 15:29:26.280173 | Alice    | 1001    | 1001    | s        | inside                     | PJSIP/ycetqvtr-00000019                              | AppDial2 | (Outgoing Line)                                       | 1567020561.37 | 1567020560.33 |                                                      |
CHAN_START   | 2019-08-28 15:29:21.253562 | Bob      | 1002    |         | s        | inside                     | PJSIP/ycetqvtr-00000019                              |          |                                                       | 1567020561.37 | 1567020560.33 |                                                      |
CHAN_START   | 2019-08-28 15:29:21.23432  | Bob      | 1002    |         | s        | inside                     | PJSIP/ycetqvtr-00000018                              |          |                                                       | 1567020561.36 | 1567020560.33 |                                                      |
CHAN_START   | 2019-08-28 15:29:21.159727 |          |         |         | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;2 |          |                                                       | 1567020561.35 | 1567020560.33 |                                                      |
CHAN_START   | 2019-08-28 15:29:21.154157 |          |         |         | ycetqvtr | wazo_wait_for_registration | Local/ycetqvtr@wazo_wait_for_registration-00000005;1 |          |                                                       | 1567020561.34 | 1567020560.33 |                                                      |
APP_START    | 2019-08-28 15:29:21.145952 | Alice    | 1001    | 1001    | s        | user                       | PJSIP/qxqz31sq-00000017                              | Dial     | Local/ycetqvtr@wazo_wait_for_registration,30,         | 1567020560.33 | 1567020560.33 |                                                      |
CHAN_START   | 2019-08-28 15:29:20.778532 | Alice    | 1001    |         | 1002     | inside                     | PJSIP/qxqz31sq-00000017                              |          |                                                       | 1567020560.33 | 1567020560.33 |                                                      |
    '''
    )
    def test_call_to_mobile_dial(self):
        self._assert_last_call_log_matches(
            '1567020560.33',
            has_properties(
                source_name='Alice',
                source_exten='1001',
                destination_name='Bob',
                destination_exten='1002',
            ),
        )

    @raw_cels(
        '''\
  eventtype   |         eventtime          |       channame        |   uniqueid    |   linkedid    | cid_name | cid_num
--------------+----------------------------+-----------------------+---------------+---------------+----------+---------
 CHAN_START   | 2017-11-10 10:07:08.620283 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 042302
 XIVO_INCALL  | 2017-11-10 10:07:08.877093 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 APP_START    | 2017-11-10 10:07:09.15148  | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 CHAN_START   | 2017-11-10 10:07:09.156027 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 ANSWER       | 2017-11-10 10:07:11.986921 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 ANSWER       | 2017-11-10 10:07:11.993852 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 BRIDGE_ENTER | 2017-11-10 10:07:11.996672 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 BRIDGE_ENTER | 2017-11-10 10:07:12.007126 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 BRIDGE_EXIT  | 2017-11-10 10:07:13.69614  | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 HANGUP       | 2017-11-10 10:07:13.756533 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 CHAN_END     | 2017-11-10 10:07:13.758228 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 BRIDGE_EXIT  | 2017-11-10 10:07:13.759858 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 HANGUP       | 2017-11-10 10:07:13.761307 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 CHAN_END     | 2017-11-10 10:07:13.762793 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 LINKEDID_END | 2017-11-10 10:07:13.764775 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
'''
    )
    def test_incoming_call_no_cid_name_rewritten_cid_num(self):
        self._assert_last_call_log_matches(
            '1510326428.26',
            has_properties(
                source_name='',
                source_exten='42302',
            ),
        )

    @raw_cels(
        '''\
eventtype    | eventtime                  | channame            |      uniqueid | linkedid
-------------+----------------------------+---------------------+---------------+---------------
CHAN_START   | 2015-06-18 14:08:56.910686 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
APP_START    | 2015-06-18 14:08:57.014249 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
CHAN_START   | 2015-06-18 14:08:57.019202 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
ANSWER       | 2015-06-18 14:08:59.864053 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
ANSWER       | 2015-06-18 14:08:59.877155 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
BRIDGE_ENTER | 2015-06-18 14:08:59.878    | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
BRIDGE_ENTER | 2015-06-18 14:08:59.87976  | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
BRIDGE_EXIT  | 2015-06-18 14:09:02.250446 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
HANGUP       | 2015-06-18 14:09:02.26592  | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
CHAN_END     | 2015-06-18 14:09:02.267146 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
BRIDGE_EXIT  | 2015-06-18 14:09:02.268    | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
HANGUP       | 2015-06-18 14:09:02.269498 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
CHAN_END     | 2015-06-18 14:09:02.271033 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
LINKEDID_END | 2015-06-18 14:09:02.272325 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
'''
    )
    def test_given_cels_with_unknown_line_identities_when_generate_call_log_then_no_user_uuid(
        self,
    ):
        linkedid = '123456789.1011'
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_no_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, is_(not_(none())))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, empty())

            def bus_event_call_log_created(accumulator):
                assert_that(
                    accumulator.accumulate(),
                    contains_inanyorder(
                        has_entries(
                            name='call_log_created',
                            data=has_entries({'tenant_uuid': SERVICE_TENANT}),
                        )
                    ),
                )

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), empty())

            until.assert_(call_log_has_no_user_uuid, tries=5)
            until.assert_(
                bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25
            )
            until.assert_(
                bus_event_call_log_user_created,
                msg_accumulator_2,
                tries=10,
                interval=0.25,
            )

    @raw_cels(
        '''\
eventtype    | eventtime                  | channame            |      uniqueid | linkedid
-------------+----------------------------+---------------------+---------------+---------------
CHAN_START   | 2015-06-18 14:08:56.910686 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
APP_START    | 2015-06-18 14:08:57.014249 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
CHAN_START   | 2015-06-18 14:08:57.019202 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
ANSWER       | 2015-06-18 14:08:59.864053 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
ANSWER       | 2015-06-18 14:08:59.877155 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
BRIDGE_ENTER | 2015-06-18 14:08:59.878    | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
BRIDGE_ENTER | 2015-06-18 14:08:59.87976  | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
BRIDGE_EXIT  | 2015-06-18 14:09:02.250446 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
HANGUP       | 2015-06-18 14:09:02.26592  | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
CHAN_END     | 2015-06-18 14:09:02.267146 | SIP/je5qtq-00000020 | 1434650937.32 | 123456789.1011
BRIDGE_EXIT  | 2015-06-18 14:09:02.268    | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
HANGUP       | 2015-06-18 14:09:02.269498 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
CHAN_END     | 2015-06-18 14:09:02.271033 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
LINKEDID_END | 2015-06-18 14:09:02.272325 | SIP/as2mkq-0000001f | 1434650936.31 | 123456789.1011
'''
    )
    def test_given_cels_with_known_line_identities_when_generate_call_log_then_call_log_have_user_uuid_and_internal_extension(
        self,
    ):
        linkedid = '123456789.1011'
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
            MockUser(USER_2_UUID, USERS_TENANT, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='as2mkq',
                users=[{'uuid': USER_1_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            ),
            MockLine(
                id=2,
                name='je5qtq',
                users=[{'uuid': USER_2_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '102', 'context': 'default'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='default', tenant_uuid=USERS_TENANT)
        )
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_both_user_uuid_and_tenant_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(
                        call_log,
                        has_properties(
                            {
                                'tenant_uuid': USERS_TENANT,
                                'source_internal_exten': '101',
                                'source_internal_context': 'default',
                                'source_user_uuid': USER_1_UUID,
                                'destination_internal_exten': '102',
                                'destination_internal_context': 'default',
                                'destination_user_uuid': USER_2_UUID,
                            }
                        ),
                    )
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(
                        user_uuids, contains_inanyorder(USER_1_UUID, USER_2_UUID)
                    )

            def bus_event_call_log_created(accumulator):
                assert_that(
                    accumulator.accumulate(),
                    contains_inanyorder(
                        has_entries(name='call_log_created', data=has_key('tags'))
                    ),
                )

            def bus_event_call_log_user_created(accumulator):
                assert_that(
                    accumulator.accumulate(),
                    contains_inanyorder(
                        has_entries(
                            name='call_log_user_created',
                            required_acl='events.call_log.user.{}.created'.format(
                                USER_1_UUID
                            ),
                            data=not_(has_key('tags')),
                        ),
                        has_entries(
                            name='call_log_user_created',
                            required_acl='events.call_log.user.{}.created'.format(
                                USER_2_UUID
                            ),
                            data=not_(has_key('tags')),
                        ),
                    ),
                )

            until.assert_(call_log_has_both_user_uuid_and_tenant_uuid, tries=5)
            until.assert_(
                bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25
            )
            until.assert_(
                bus_event_call_log_user_created,
                msg_accumulator_2,
                tries=10,
                interval=0.25,
            )

    @raw_cels(
        '''\
   eventtype   |         eventtime          | cid_name | cid_num |       exten       |   context   |      channame       |   uniqueid   |   linkedid   | userfield
---------------+----------------------------+----------+---------+-------------------+-------------+---------------------+--------------+--------------+-----------
 CHAN_START    | 2018-04-24 14:27:17.922298 | Alicé    | 101     | 102               | default     | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 XIVO_USER_FWD | 2018-04-24 14:27:18.249093 | Alicé    | 101     | forward_voicemail | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 ANSWER        | 2018-04-24 14:27:18.748307 | Alicé    | 101     | pickup            | xivo-pickup | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 APP_START     | 2018-04-24 14:27:20.140238 | Alicé    | 101     | s                 | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 CHAN_START    | 2018-04-24 14:27:20.169787 | Charlié  | 103     | s                 | default     | SIP/rku3uo-00000002 | 1524594440.8 | 1524594437.7 |
 ANSWER        | 2018-04-24 14:27:26.471371 | Charlié  | 103     | s                 | default     | SIP/rku3uo-00000002 | 1524594440.8 | 1524594437.7 |
 BRIDGE_ENTER  | 2018-04-24 14:27:26.478948 | Charlié  | 103     |                   | default     | SIP/rku3uo-00000002 | 1524594440.8 | 1524594437.7 |
 BRIDGE_ENTER  | 2018-04-24 14:27:26.487775 | Alicé    | 101     | s                 | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 BRIDGE_EXIT   | 2018-04-24 14:27:27.195224 | Charlié  | 103     |                   | default     | SIP/rku3uo-00000002 | 1524594440.8 | 1524594437.7 |
 HANGUP        | 2018-04-24 14:27:27.210832 | Charlié  | 103     |                   | default     | SIP/rku3uo-00000002 | 1524594440.8 | 1524594437.7 |
 CHAN_END      | 2018-04-24 14:27:27.213126 | Charlié  | 103     |                   | default     | SIP/rku3uo-00000002 | 1524594440.8 | 1524594437.7 |
 BRIDGE_EXIT   | 2018-04-24 14:27:27.215685 | Alicé    | 101     | s                 | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 HANGUP        | 2018-04-24 14:27:27.226649 | Alicé    | 101     | s                 | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 CHAN_END      | 2018-04-24 14:27:27.250875 | Alicé    | 101     | s                 | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 LINKEDID_END  | 2018-04-24 14:27:27.25419  | Alicé    | 101     | s                 | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
'''
    )
    def test_given_cels_of_forwarded_call_when_generate_call_log_then_requested_different_from_destination(
        self,
    ):
        self.confd.set_lines(
            MockLine(
                id=1,
                name='101',
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            ),
            MockLine(
                id=2,
                name='rku3uo',
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '103', 'context': 'default'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='default', tenant_uuid=USERS_TENANT)
        )
        self._assert_last_call_log_matches(
            '1524594437.7',
            has_properties(
                tenant_uuid=USERS_TENANT,
                source_internal_exten='101',
                source_internal_context='default',
                requested_exten='102',
                requested_context='default',
                destination_exten='103',
                destination_internal_exten='103',
                destination_internal_context='default',
            ),
        )

    @raw_cels(
        '''\
   eventtype   |         eventtime          | cid_name     | cid_num | exten  |   context   |      channame       |   uniqueid    |   linkedid
---------------+----------------------------+--------------+---------+--------+-------------+---------------------+---------------+-------------
 CHAN_START    | 2018-04-24 15:15:50.146287 | John Rambo   | 42309   | 999101 | from-extern | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 XIVO_INCALL   | 2018-04-24 15:15:50.2177   | John Rambo   | 42309   | s      | did         | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 APP_START     | 2018-04-24 15:15:50.541953 | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 CHAN_START    | 2018-04-24 15:15:50.547682 | Arsène Lupin | 101     | s      | default     | SCCP/101-00000006   | 1524597350.10 | 1524597350.9
 ANSWER        | 2018-04-24 15:15:52.475678 | Arsène Lupin | 101     | s      | default     | SCCP/101-00000006   | 1524597350.10 | 1524597350.9
 ANSWER        | 2018-04-24 15:15:52.482163 | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 BRIDGE_ENTER  | 2018-04-24 15:15:52.484849 | Arsène Lupin | 101     |        | default     | SCCP/101-00000006   | 1524597350.10 | 1524597350.9
 BRIDGE_ENTER  | 2018-04-24 15:15:52.487482 | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 BRIDGE_EXIT   | 2018-04-24 15:15:53.784503 | Arsène Lupin | 101     |        | default     | SCCP/101-00000006   | 1524597350.10 | 1524597350.9
 BRIDGE_EXIT   | 2018-04-24 15:15:53.79021  | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 HANGUP        | 2018-04-24 15:15:53.798411 | Arsène Lupin | 101     |        | default     | SCCP/101-00000006   | 1524597350.10 | 1524597350.9
 CHAN_END      | 2018-04-24 15:15:53.803513 | Arsène Lupin | 101     |        | default     | SCCP/101-00000006   | 1524597350.10 | 1524597350.9
 HANGUP        | 2018-04-24 15:15:53.812298 | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 CHAN_END      | 2018-04-24 15:15:53.819273 | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 LINKEDID_END  | 2018-04-24 15:15:53.830883 | John Rambo   | 42309   | s      | user        | SIP/dev_32-00000003 | 1524597350.9  | 1524597350.9
 '''
    )
    def test_given_incoming_call_when_generate_call_log_then_requested_internal_extension_is_set(
        self,
    ):
        self.confd.set_lines(
            MockLine(
                id=1,
                name='101',
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            )
        )
        self.confd.set_contexts(
            MockContext(id=1, name='default', tenant_uuid=USERS_TENANT)
        )

        self._assert_last_call_log_matches(
            '1524597350.9',
            has_properties(
                tenant_uuid=USERS_TENANT,
                source_internal_exten=None,
                source_internal_context=None,
                requested_exten='999101',
                requested_context='from-extern',
                requested_internal_exten='101',
                requested_internal_context='default',
                destination_exten='101',
                destination_internal_exten='101',
                destination_internal_context='default',
            ),
        )

    @raw_cels(
        '''\
   eventtype   |         eventtime          |     cid_name      |  cid_num  |       exten       |          context           |                   channame                    |   uniqueid    |   linkedid
---------------+----------------------------+-------------------+-----------+-------------------+----------------------------+-----------------------------------------------+---------------+---------------
 CHAN_START    | 2019-08-02 14:20:00.516634 |                   |           | s                 | wazo-originate-mobile-leg1 | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 CHAN_START    | 2019-08-02 14:20:00.523812 |                   |           | s                 | wazo-originate-mobile-leg1 | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 XIVO_OUTCALL  | 2019-08-02 14:20:00.597891 | 101               | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 APP_START     | 2019-08-02 14:20:00.601205 | 101               | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 CHAN_START    | 2019-08-02 14:20:00.603373 | xivo              |           | s                 | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21
 ANSWER        | 2019-08-02 14:20:04.976083 |                   | **9742332 | dial              | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21
 ANSWER        | 2019-08-02 14:20:04.995816 | 101               | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 BRIDGE_ENTER  | 2019-08-02 14:20:04.99812  |                   | **9742332 |                   | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21
 BRIDGE_ENTER  | 2019-08-02 14:20:05.000422 | 101               | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 ANSWER        | 2019-08-02 14:20:05.002815 |                   | **9742332 | s                 | wazo-originate-mobile-leg1 | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 APP_START     | 2019-08-02 14:20:05.389309 | **9742332         | **9742332 | s                 | user                       | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 CHAN_START    | 2019-08-02 14:20:05.401146 | Alice Woonderland | 101       | s                 | default                    | SCCP/101-0000000a                             | 1564770005.24 | 1564770000.21
 ANSWER        | 2019-08-02 14:20:09.269941 | Alice Woonderland | 101       | s                 | default                    | SCCP/101-0000000a                             | 1564770005.24 | 1564770000.21
 BRIDGE_ENTER  | 2019-08-02 14:20:09.279343 | Alice Woonderland | 101       |                   | default                    | SCCP/101-0000000a                             | 1564770005.24 | 1564770000.21
 BRIDGE_ENTER  | 2019-08-02 14:20:09.281647 | **9742332         | **9742332 | s                 | user                       | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 BRIDGE_EXIT   | 2019-08-02 14:20:12.292321 | Alice Woonderland | 101       |                   | default                    | SCCP/101-0000000a                             | 1564770005.24 | 1564770000.21
 HANGUP        | 2019-08-02 14:20:12.297821 | Alice Woonderland | 101       |                   | default                    | SCCP/101-0000000a                             | 1564770005.24 | 1564770000.21
 CHAN_END      | 2019-08-02 14:20:12.300253 | Alice Woonderland | 101       |                   | default                    | SCCP/101-0000000a                             | 1564770005.24 | 1564770000.21
 BRIDGE_EXIT   | 2019-08-02 14:20:12.302639 | **9742332         | **9742332 | s                 | user                       | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 HANGUP        | 2019-08-02 14:20:12.304888 | **9742332         | **9742332 | s                 | user                       | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 CHAN_END      | 2019-08-02 14:20:12.307043 | **9742332         | **9742332 | s                 | user                       | Local/s@wazo-originate-mobile-leg1-00000001;1 | 1564770000.21 | 1564770000.21
 BRIDGE_EXIT   | 2019-08-02 14:20:12.312344 | Alice Woonderland | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 HANGUP        | 2019-08-02 14:20:12.315722 | Alice Woonderland | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 BRIDGE_EXIT   | 2019-08-02 14:20:12.318094 |                   | **9742332 |                   | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21
 CHAN_END      | 2019-08-02 14:20:12.320487 | Alice Woonderland | 101       | dial              | outcall                    | Local/s@wazo-originate-mobile-leg1-00000001;2 | 1564770000.22 | 1564770000.21
 HANGUP        | 2019-08-02 14:20:12.322631 |                   | **9742332 |                   | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21
 CHAN_END      | 2019-08-02 14:20:12.327546 |                   | **9742332 |                   | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21
 LINKEDID_END  | 2019-08-02 14:20:12.329958 |                   | **9742332 |                   | from-extern                | PJSIP/dev_32-00000009                         | 1564770000.23 | 1564770000.21

'''
    )
    def test_originate_from_mobile(self):
        self._assert_last_call_log_matches(
            '1564770000.21',
            has_properties(
                source_name='',
                source_exten='**9742332',
                destination_name='Alice Woonderland',
                destination_exten='101',
            ),
        )

    @raw_cels('''\
 eventtype    | eventtime                  | cid_name | cid_num | exten | context | channame            |      uniqueid |     linkedid  | userfield
--------------+----------------------------+----------+---------+-------+---------+---------------------+---------------+---------------+-----------
 CHAN_START   | 2015-06-18 14:08:56.910686 | Elès 45  | 1045    | 1001  | default | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 APP_START    | 2015-06-18 14:08:57.014249 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 CHAN_START   | 2015-06-18 14:08:57.019202 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000020 | 1434650937.32 | 1434650936.31 |
 ANSWER       | 2015-06-18 14:08:59.864053 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000020 | 1434650937.32 | 1434650936.31 |
 ANSWER       | 2015-06-18 14:08:59.877155 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 BRIDGE_ENTER | 2015-06-18 14:08:59.878    | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 BRIDGE_ENTER | 2015-06-18 14:08:59.87976  | Elès 01  | 1001    |       | default | SIP/je5qtq-00000020 | 1434650937.32 | 1434650936.31 |
 BRIDGE_EXIT  | 2015-06-18 14:09:02.250446 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000020 | 1434650937.32 | 1434650936.31 |
 HANGUP       | 2015-06-18 14:09:02.26592  | Elès 01  | 1001    |       | default | SIP/je5qtq-00000020 | 1434650937.32 | 1434650936.31 |
 CHAN_END     | 2015-06-18 14:09:02.267146 | Elès 01  | 1001    |       | default | SIP/je5qtq-00000020 | 1434650937.32 | 1434650936.31 |
 BRIDGE_EXIT  | 2015-06-18 14:09:02.268    | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 HANGUP       | 2015-06-18 14:09:02.269498 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 CHAN_END     | 2015-06-18 14:09:02.271033 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
 LINKEDID_END | 2015-06-18 14:09:02.272325 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000001f | 1434650936.31 | 1434650936.31 |
    ''')
    def test_answered_internal(self):
        self._assert_last_call_log_matches(
            '1434650936.31',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:08:56.910686+00:00'),
                date_answer=datetime.fromisoformat('2015-06-18 14:08:59.878+00:00'),
                date_end=datetime.fromisoformat('2015-06-18 14:09:02.271033+00:00'),
                source_name='Elès 45',
                source_exten='1045',
                requested_exten='1001',
                requested_context='default',
                destination_exten='1001',
                source_line_identity='sip/as2mkq',
                destination_line_identity='sip/je5qtq',
            )
        )

    @raw_cels('''\
 eventtype    | eventtime                  | cid_name | cid_num | exten | context | channame            |      uniqueid |     linkedid  | userfield

 CHAN_START   | 2015-06-18 14:10:24.586638 | Elès 45  | 1045    | 1001  | default | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 APP_START    | 2015-06-18 14:10:24.6893   | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 CHAN_START   | 2015-06-18 14:10:24.694166 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000022 | 1434651024.34 | 1434651024.33 |
 HANGUP       | 2015-06-18 14:10:28.280456 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000022 | 1434651024.34 | 1434651024.33 |
 CHAN_END     | 2015-06-18 14:10:28.28819  | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000022 | 1434651024.34 | 1434651024.33 |
 HANGUP       | 2015-06-18 14:10:28.289431 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 CHAN_END     | 2015-06-18 14:10:28.290746 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 LINKEDID_END | 2015-06-18 14:10:28.292243 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
    ''')
    def test_internal_no_answer(self):
        self._assert_last_call_log_matches(
            '1434651024.33',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:10:24.586638+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2015-06-18 14:10:28.290746+00:00'),
                source_name='Elès 45',
                source_exten='1045',
                requested_exten='1001',
                requested_context='default',
                destination_exten='1001',
                source_line_identity='sip/as2mkq',
                destination_line_identity='sip/je5qtq',
            ),
        )

    @raw_cels('''\
 eventtype     | eventtime                  | cid_name         | cid_num | exten             | context     | channame            |      uniqueid |      linkedid

 CHAN_START    | 2018-02-02 15:00:25.106723 | Alice            |     101 | 103               | default     | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 XIVO_USER_FWD | 2018-02-02 15:00:25.546267 | Alice            |     101 | forward_voicemail | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 ANSWER        | 2018-02-02 15:00:26.051203 | Alice            |     101 | pickup            | xivo-pickup | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 APP_START     | 2018-02-02 15:00:27.373161 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 CHAN_START    | 2018-02-02 15:00:27.392589 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17
 ANSWER        | 2018-02-02 15:00:29.207311 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17
 BRIDGE_ENTER  | 2018-02-02 15:00:29.227529 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17
 BRIDGE_ENTER  | 2018-02-02 15:00:29.22922  | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 BRIDGE_EXIT   | 2018-02-02 15:00:30.464687 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17
 HANGUP        | 2018-02-02 15:00:30.471676 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17
 CHAN_END      | 2018-02-02 15:00:30.476368 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17
 BRIDGE_EXIT   | 2018-02-02 15:00:30.478914 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 HANGUP        | 2018-02-02 15:00:30.481403 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 CHAN_END      | 2018-02-02 15:00:30.484065 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
 LINKEDID_END  | 2018-02-02 15:00:30.486225 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17
    ''')
    def test_internal_unconditional_forwarded_answered_call(self):
        self._assert_last_call_log_matches(
            '1517601625.17',
            has_properties(
                date=datetime.fromisoformat('2018-02-02 15:00:25.106723+00:00'),
                date_answer=datetime.fromisoformat('2018-02-02 15:00:29.229220+00:00'),
                date_end=datetime.fromisoformat('2018-02-02 15:00:30.484065+00:00'),
                source_exten='101',
                requested_exten='103',
                requested_context='default',
                destination_exten='102',
                destination_name='Bernard',
                source_line_identity='sccp/101',
                destination_line_identity='sip/dm77z3',
            ),

        )

    @raw_cels('''\
 eventtype     | eventtime                  | cid_name         | cid_num | exten             | context     | channame            |      uniqueid |      linkedid

 CHAN_START    | 2018-02-06 13:33:31.114956 | Alice            |     101 | 103               | default     | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 APP_START     | 2018-02-06 13:33:31.897767 | Alice            |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 CHAN_START    | 2018-02-06 13:33:31.927285 | Charlie          |     103 | s                 | default     | SIP/rku3uo-0000000e | 1517942011.17 | 1517942011.16
 HANGUP        | 2018-02-06 13:33:33.272605 | Charlie          |     103 | s                 | default     | SIP/rku3uo-0000000e | 1517942011.17 | 1517942011.16
 CHAN_END      | 2018-02-06 13:33:33.287358 | Charlie          |     103 | s                 | default     | SIP/rku3uo-0000000e | 1517942011.17 | 1517942011.16
 XIVO_USER_FWD | 2018-02-06 13:33:33.28969  | Alice            |     101 | forward_voicemail | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 ANSWER        | 2018-02-06 13:33:33.778962 | Alice            |     101 | pickup            | xivo-pickup | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 APP_START     | 2018-02-06 13:33:35.089841 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 CHAN_START    | 2018-02-06 13:33:35.107786 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16
 ANSWER        | 2018-02-06 13:33:36.315745 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16
 BRIDGE_ENTER  | 2018-02-06 13:33:36.331304 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16
 BRIDGE_ENTER  | 2018-02-06 13:33:36.333193 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 BRIDGE_EXIT   | 2018-02-06 13:33:37.393726 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16
 HANGUP        | 2018-02-06 13:33:37.401862 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16
 CHAN_END      | 2018-02-06 13:33:37.404542 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16
 BRIDGE_EXIT   | 2018-02-06 13:33:37.407847 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 HANGUP        | 2018-02-06 13:33:37.410228 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 CHAN_END      | 2018-02-06 13:33:37.412453 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
 LINKEDID_END  | 2018-02-06 13:33:37.414762 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16
    ''')
    def test_internal_busy_fwd_answered_call(self):
        self._assert_last_call_log_matches(
            '1517942011.16',
            has_properties(
                date=datetime.fromisoformat('2018-02-06 13:33:31.114956+00:00'),
                date_answer=datetime.fromisoformat('2018-02-06 13:33:36.333193+00:00'),
                date_end=datetime.fromisoformat('2018-02-06 13:33:37.412453+00:00'),
                source_exten='101',
                requested_exten='103',
                requested_context='default',
                destination_exten='102',
                source_line_identity='sccp/101',
                destination_line_identity='sip/dm77z3',
            ),
        )

    @contextmanager
    def cels(self, cels):
        with self.database.queries() as queries:
            for cel in cels:
                cel['id'] = queries.insert_cel(**cel)

        yield

        with self.database.queries() as queries:
            for cel in cels:
                queries.delete_cel(cel['id'])

    @contextmanager
    def no_call_logs(self):
        with self.database.queries() as queries:
            queries.clear_call_logs()

        yield

        with self.database.queries() as queries:
            queries.clear_call_logs()

    def _assert_last_call_log_matches(self, linkedid, expected):
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_generated():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, expected)

            until.assert_(call_log_generated, tries=5)

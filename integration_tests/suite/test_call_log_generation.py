# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

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
from .helpers.confd import (
    MockLine,
    MockUser,
)
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy

USER_1_UUID = '11111111-1111-1111-1111-111111111111'
USER_2_UUID = '22222222-2222-2222-2222-222222222222'


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

    @raw_cels('''\
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
''')
    def test_incoming_call_no_cid_name_rewritten_cid_num(self):
        linkedid = '1510326428.26'
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_transformed_number():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(
                        call_log,
                        has_properties(
                            'source_name', '',
                            'source_exten', '42302'))

            until.assert_(call_log_has_transformed_number, tries=5)

    @raw_cels('''\
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
''')
    def test_given_cels_with_unknown_line_identities_when_generate_call_log_then_no_user_uuid(self):
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
                assert_that(accumulator.accumulate(), contains_inanyorder(has_entries(
                    name='call_log_created',
                    data=has_key('tags')
                )))

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), empty())

            until.assert_(call_log_has_no_user_uuid, tries=5)
            until.assert_(bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25)
            until.assert_(bus_event_call_log_user_created, msg_accumulator_2, tries=10, interval=0.25)

    @raw_cels('''\
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
''')
    def test_given_cels_with_known_line_identities_when_generate_call_log_then_call_log_have_user_uuid_and_internal_extension(self):
        linkedid = '123456789.1011'
        self.confd.set_users(
            MockUser(USER_1_UUID, line_ids=[1]), MockUser(USER_2_UUID, line_ids=[2])
        )
        self.confd.set_lines(
            MockLine(id=1, name='as2mkq',
                     users=[{'uuid': USER_1_UUID}],
                     extensions=[{'exten': '101', 'context': 'default'}]),
            MockLine(id=2, name='je5qtq',
                     users=[{'uuid': USER_2_UUID}],
                     extensions=[{'exten': '102', 'context': 'default'}]),
        )
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_both_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, has_properties({
                        'source_internal_exten': '101',
                        'source_internal_context': 'default',
                        'destination_internal_exten': '102',
                        'destination_internal_context': 'default',
                    }))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, contains_inanyorder(USER_1_UUID, USER_2_UUID))

            def bus_event_call_log_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(has_entries(
                    name='call_log_created',
                    data=has_key('tags')
                )))

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(
                    has_entries(
                        name='call_log_user_created',
                        required_acl='events.call_log.user.{}.created'.format(USER_1_UUID),
                        data=not_(has_key('tags')),
                    ),
                    has_entries(
                        name='call_log_user_created',
                        required_acl='events.call_log.user.{}.created'.format(USER_2_UUID),
                        data=not_(has_key('tags')),
                    )
                ))

            until.assert_(call_log_has_both_user_uuid, tries=5)
            until.assert_(bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25)
            until.assert_(bus_event_call_log_user_created, msg_accumulator_2, tries=10, interval=0.25)

    @raw_cels('''\
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
''')
    def test_given_cels_of_forwarded_call_when_generate_call_log_then_requested_different_from_destination(self):
        self.confd.set_lines(
            MockLine(id=1, name='101',
                     extensions=[{'exten': '101', 'context': 'default'}]),
            MockLine(id=2, name='rku3uo',
                     extensions=[{'exten': '103', 'context': 'default'}]),
        )

        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid='1524594437.7')

            def call_log_has_destination_different_from_requested():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, has_properties({
                        'source_internal_exten': '101',
                        'source_internal_context': 'default',
                        'requested_exten': '102',
                        'requested_context': 'default',
                        'destination_exten': '103',
                        'destination_internal_exten': '103',
                        'destination_internal_context': 'default',
                    }))

            until.assert_(call_log_has_destination_different_from_requested, tries=10)

    @raw_cels('''\
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
 ''')
    def test_given_incoming_call_when_generate_call_log_then_requested_internal_extension_is_set(self):
        self.confd.set_lines(
            MockLine(id=1, name='101',
                     extensions=[{'exten': '101', 'context': 'default'}]),
        )

        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid='1524597350.9')

            def call_log_has_destination_different_from_requested():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, has_properties({
                        'source_internal_exten': None,
                        'source_internal_context': None,
                        'requested_exten': '999101',
                        'requested_context': 'from-extern',
                        'requested_internal_exten': '101',
                        'requested_internal_context': 'default',
                        'destination_exten': '101',
                        'destination_internal_exten': '101',
                        'destination_internal_context': 'default',
                    }))

            until.assert_(call_log_has_destination_different_from_requested, tries=5)

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

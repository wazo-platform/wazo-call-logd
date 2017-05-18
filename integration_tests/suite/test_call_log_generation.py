# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from contextlib import contextmanager
from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import is_
from hamcrest import not_
from hamcrest import none
from xivo_test_helpers import until

from .test_api.base import IntegrationTest
from .test_api.confd import MockUser, MockLine


class TestCallLogGeneration(IntegrationTest):

    asset = 'base'

    def setUp(self):
        self.bus = self.make_bus()
        self.confd = self.make_confd()
        self.confd.reset()
        until.true(self.bus.is_up, tries=10, interval=0.5)

    def test_given_cels_with_unknown_line_identities_when_generate_call_log_then_no_user_uuid(self):
        linkedid = '123456789.1011'
        cels = [
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:56.910686',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'APP_START',
             'eventtime': '2015-06-18 14:08:57.014249',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:57.019202',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.864053',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.877155',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.878',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.87976',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.250446',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.26592',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.267146',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.268',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.269498',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.271033',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'LINKEDID_END',
             'eventtime': '2015-06-18 14:09:02.272325',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
        ]
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.cels(cels), self.no_call_logs():
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

    def test_given_cels_with_known_line_identities_when_generate_call_log_then_call_log_have_user_uuid(self):
        linkedid = '123456789.1011'
        cels = [
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:56.910686',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'APP_START',
             'eventtime': '2015-06-18 14:08:57.014249',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:57.019202',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.864053',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.877155',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.878',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.87976',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.250446',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.26592',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.267146',
             'channame': u'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.268',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.269498',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.271033',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'LINKEDID_END',
             'eventtime': '2015-06-18 14:09:02.272325',
             'channame': u'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
        ]
        self.confd.set_users(MockUser('user_1_uuid', line_ids=[1]), MockUser('user_2_uuid', line_ids=[2]))
        self.confd.set_lines(MockLine(id=1, name='as2mkq', users=[{'uuid': 'user_1_uuid'}]), MockLine(id=2, name='je5qtq', users=[{'uuid': 'user_2_uuid'}]))
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.cels(cels), self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_both_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, is_(not_(none())))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, contains_inanyorder('user_1_uuid', 'user_2_uuid'))

            def bus_event_call_log_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(has_entries(
                    name='call_log_created',
                    data=has_key('tags')
                )))

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(
                    has_entries(
                        name='call_log_user_created',
                        required_acl='events.call_log.user.user_1_uuid.created',
                        data=not_(has_key('tags')),
                    ),
                    has_entries(
                        name='call_log_user_created',
                        required_acl='events.call_log.user.user_2_uuid.created',
                        data=not_(has_key('tags')),
                    )
                ))

            until.assert_(call_log_has_both_user_uuid, tries=5)
            until.assert_(bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25)
            until.assert_(bus_event_call_log_user_created, msg_accumulator_2, tries=10, interval=0.25)

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

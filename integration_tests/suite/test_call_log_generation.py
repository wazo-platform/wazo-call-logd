# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from contextlib import contextmanager
from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import has_entry
from hamcrest import has_entries
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
        with self.cels(cels):
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_no_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, is_(not_(none())))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, empty())

            until.assert_(call_log_has_no_user_uuid, tries=5)

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
        with self.cels(cels):
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_no_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, is_(not_(none())))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, contains_inanyorder('user_1_uuid', 'user_2_uuid'))

            until.assert_(call_log_has_no_user_uuid, tries=5)

    @contextmanager
    def cels(self, cels):
        with self.database.queries() as queries:
            for cel in cels:
                cel['id'] = queries.insert_cel(**cel)

        yield

        with self.database.queries() as queries:
            for cel in cels:
                queries.delete_cel(cel['id'])

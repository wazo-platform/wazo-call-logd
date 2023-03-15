# Copyright 2022-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from hamcrest import (
    assert_that,
    all_of,
    any_of,
    contains,
    contains_inanyorder,
    empty,
    has_entries,
    has_item,
    has_key,
    has_length,
    has_properties,
    is_,
    not_,
    not_none,
    none,
)
from wazo_test_helpers import until

from .helpers.base import raw_cels, RawCelIntegrationTest
from .helpers.confd import MockContext, MockLine, MockUser
from .helpers.constants import (
    USER_1_UUID,
    USER_2_UUID,
    USER_3_UUID,
    USERS_TENANT,
    SERVICE_TENANT,
)


class TestCallLogGeneration(RawCelIntegrationTest):
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
  eventtype                 |  eventtime                    |  cid_name         |  cid_num  |  exten                |  context      |  channame                  |  uniqueid        |  linkedid        |  extra
----------------------------+-------------------------------+-------------------+-----------+-----------------------+---------------+----------------------------+------------------+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 CHAN_START                 | 2022-07-05 15:10:17.477554    | Harry Potter      | 1603      | 1604                  | mycontext     | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |
 APP_START                  | 2022-07-05 15:10:17.676004    | Harry Potter      | 1603      | s                     | user          | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |
 XIVO_USER_FWD              | 2022-07-05 15:10:17.677551    | Harry Potter      | 1603      | forward_voicemail     | user          | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |{"extra":"NUM:1604,CONTEXT:mycontext,NAME:Willy Wonka"}
 WAZO_USER_MISSED_CALL      | 2022-07-05 15:10:17.677582    | Harry Potter      | 1603      | forward_voicemail     | user          | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |{"extra":"wazo_tenant_uuid: 006a72c4-eb68-481a-808f-33b28ec109c8,source_user_uuid: cb79f29b-f69a-4b93-85c2-49dcce119a9f,destination_user_uuid: c3f297bd-93e1-46f6-a309-79b320acb7fb,destination_exten: 1604,source_name: Gryffindor%2C%20Harry%20Potter,destination_name: Willy%20Wonka"}
 ANSWER                     | 2022-07-05 15:10:17.679283    | Harry Potter      | 1603      | pickup                | xivo-pickup   | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |
 HANGUP                     | 2022-07-05 15:10:23.918826    | Harry Potter      | 1603      | unreachable           | user          | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |{"hangupcause":3,"hangupsource":"dialplan/builtin","dialstatus":""}
 CHAN_END                   | 2022-07-05 15:10:23.918826    | Harry Potter      | 1603      | unreachable           | user          | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |
 LINKEDID_END               | 2022-07-05 15:10:23.918826    | Harry Potter      | 1603      | unreachable           | user          | PJSIP/cul113qn-00000007    | 1657048217.7     | 1657048217.7     |
'''
    )
    def test_when_calling_unreachable_phone_then_destination_info_is_set_within_call_log(
        self,
    ):
        linkedid = '1657048217.7'
        wazo_tenant_uuid = '006a72c4-eb68-481a-808f-33b28ec109c8'
        source_user_uuid = 'cb79f29b-f69a-4b93-85c2-49dcce119a9f'
        destination_user_uuid = 'c3f297bd-93e1-46f6-a309-79b320acb7fb'
        self.confd.set_users(
            MockUser(
                source_user_uuid,
                wazo_tenant_uuid,
                line_ids=[1],
                userfield='Montreal,Quebec',
            ),
            MockUser(
                destination_user_uuid,
                wazo_tenant_uuid,
                line_ids=[2],
                userfield='Paris,France',
            ),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='cul113qn',
                users=[{'uuid': source_user_uuid}],
                tenant_uuid=wazo_tenant_uuid,
                extensions=[{'exten': '1603', 'context': 'mycontext'}],
            ),
            MockLine(
                id=2,
                name='xfloi61j',
                users=[{'uuid': destination_user_uuid}],
                tenant_uuid=wazo_tenant_uuid,
                extensions=[{'exten': '1604', 'context': 'mycontext'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='mycontext', tenant_uuid=wazo_tenant_uuid)
        )
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_all_required_fields_set():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(
                        call_log,
                        has_properties(
                            date_answer=None,
                            tenant_uuid=wazo_tenant_uuid,
                            source_name='Gryffindor, Harry Potter',
                            source_internal_name='Harry Potter',
                            source_exten='1603',
                            source_line_identity='pjsip/cul113qn',
                            destination_name='Willy Wonka',
                            destination_exten='1604',
                            direction='internal',
                            requested_name='Willy Wonka',
                            requested_exten='1604',
                            requested_context='mycontext',
                            requested_internal_exten='1604',
                            requested_internal_context='mycontext',
                            source_user_uuid=source_user_uuid,
                            destination_user_uuid=destination_user_uuid,
                            participants=contains_inanyorder(
                                has_properties(
                                    role='source',
                                    user_uuid=source_user_uuid,
                                    line_id=1,
                                    tags=contains_inanyorder('Montreal', 'Quebec'),
                                    answered=False,
                                ),
                                has_properties(
                                    role='destination',
                                    user_uuid=destination_user_uuid,
                                    line_id=2,
                                    tags=contains_inanyorder('Paris', 'France'),
                                    answered=False,
                                ),
                            ),
                        ),
                    )
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(
                        user_uuids,
                        contains_inanyorder(source_user_uuid, destination_user_uuid),
                    )

            until.assert_(call_log_has_all_required_fields_set, tries=5)

    @raw_cels(
        '''\
  eventtype                 |  eventtime                    |  cid_name         |  cid_num  |  exten                |  context      |  channame                  |  uniqueid        |  linkedid        |  extra
----------------------------+-------------------------------+-------------------+-----------+-----------------------+---------------+----------------------------+------------------+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 CHAN_START                 | 2022-07-07 15:52:09.928395    | Harry Potter      | 1603      | 91800                 | mycontext     | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |
 XIVO_INCALL                | 2022-07-07 15:52:09.964649    | Harry Potter      | 1603      | s                     | did           | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |{"extra":"006a72c4-eb68-481a-808f-33b28ec109c8"}
 APP_START                  | 2022-07-07 15:52:10.117812    | Harry Potter      | 1603      | s                     | user          | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |
 CHAN_START                 | 2022-07-07 15:52:10.119383    | Harry Potter      | 1603      | s                     | mycontext     | PJSIP/cul113qn-0000000a    | 1657223530.10    | 1657223529.9     |
 XIVO_USER_FWD              | 2022-07-07 15:52:13.7577      | Harry Potter      | 1603      | forward_voicemail     | user          | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |{"extra":"NUM:1603,CONTEXT:mycontext,NAME:Harry Potter"}
 WAZO_USER_MISSED_CALL      | 2022-07-07 15:52:13.757839    | Harry Potter      | 1603      | forward_voicemail     | user          | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |{"extra":"wazo_tenant_uuid: 006a72c4-eb68-481a-808f-33b28ec109c8,source_user_uuid: ,destination_user_uuid: cb79f29b-f69a-4b93-85c2-49dcce119a9f,destination_exten: 1800,source_name: Gryffindor%2C%20Harry%20Potter,destination_name: Harry%20Potter"}
 ANSWER                     | 2022-07-07 15:52:13.765261    | Harry Potter      | 1603      | pickup                | xivo-pickup   | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |
 HANGUP                     | 2022-07-07 15:52:13.775339    | Harry Potter      | 1603      | s                     | mycontext     | PJSIP/cul113qn-0000000a    | 1657223530.10    | 1657223529.9     |{"hangupcause":19,"hangupsource":"PJSIP/cul113qn-0000000a","dialstatus":""}
 CHAN_END                   | 2022-07-07 15:52:13.775339    | Harry Potter      | 1603      | s                     | mycontext     | PJSIP/cul113qn-0000000a    | 1657223530.10    | 1657223529.9     |
 HANGUP                     | 2022-07-07 15:52:20.041784    | Harry Potter      | 1603      | unreachable           | user          | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |{"hangupcause":19,"hangupsource":"dialplan/builtin","dialstatus":"NOANSWER"}
 CHAN_END                   | 2022-07-07 15:52:20.041784    | Harry Potter      | 1603      | unreachable           | user          | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |
 LINKEDID_END               | 2022-07-07 15:52:20.041784    | Harry Potter      | 1603      | unreachable           | user          | PJSIP/cul113qn-00000009    | 1657223529.9     | 1657223529.9     |
'''
    )
    def test_when_incall_and_unreachable_phone_then_call_log_contains_no_source_user_uuid(
        self,
    ):
        linkedid = '1657223529.9'
        wazo_tenant_uuid = '006a72c4-eb68-481a-808f-33b28ec109c8'
        destination_user_uuid = 'cb79f29b-f69a-4b93-85c2-49dcce119a9f'
        self.confd.set_users(
            MockUser(
                destination_user_uuid,
                wazo_tenant_uuid,
                line_ids=[2],
                userfield='Paris,France',
            ),
        )
        self.confd.set_lines(
            MockLine(
                id=2,
                name='cul113qn',
                users=[{'uuid': destination_user_uuid}],
                tenant_uuid=wazo_tenant_uuid,
                extensions=[{'exten': '1800', 'context': 'mycontext'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='mycontext', tenant_uuid=wazo_tenant_uuid)
        )

        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_is_missing_source_user():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(
                        call_log,
                        has_properties(
                            date_answer=None,
                            tenant_uuid='006a72c4-eb68-481a-808f-33b28ec109c8',
                            source_name='Gryffindor, Harry Potter',
                            source_internal_name='Harry Potter',
                            source_exten='1603',
                            source_line_identity='pjsip/cul113qn',
                            destination_name='Harry Potter',
                            destination_exten='1603',
                            direction='inbound',
                            requested_name='Harry Potter',
                            requested_exten='91800',
                            requested_context='mycontext',
                            requested_internal_exten='1603',
                            requested_internal_context='mycontext',
                            source_user_uuid=None,
                            destination_user_uuid='cb79f29b-f69a-4b93-85c2-49dcce119a9f',
                            participants=contains_inanyorder(
                                has_properties(
                                    role='destination',
                                    user_uuid='cb79f29b-f69a-4b93-85c2-49dcce119a9f',
                                    tags=contains_inanyorder('Paris', 'France'),
                                    answered=False,
                                ),
                            ),
                        ),
                    )
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(
                        user_uuids,
                        contains(destination_user_uuid),
                    )

            until.assert_(call_log_is_missing_source_user, tries=5)

    @raw_cels(
        '''\
  eventtype                     | eventtime                         | cid_name          | cid_num   | cid_ani   | exten     | context    | channame                 | linkedid       | uniqueid       | extra
--------------------------------+-----------------------------------+-------------------+-----------+-----------+-----------+------------+--------------------------+----------------+----------------+-----------------------------------------------------------------------------------------
 CHAN_START                     | 2022-07-20 17:56:12.094533        | Harry Potter      | 1603      |           | 1604      | mycontext  | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  |
 WAZO_CALL_LOG_DESTINATION      | 2022-07-20 17:56:12.285233        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  | {"extra":"type: user,uuid: c3f297bd-93e1-46f6-a309-79b320acb7fb,name: Willy Wonka"}
 APP_START                      | 2022-07-20 17:56:12.303842        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  |
 CHAN_START                     | 2022-07-20 17:56:12.305099        | Willy Wonka       | 1604      |           | s         | mycontext  | PJSIP/xfloi61j-0000000d  | 1658354172.12  | 1658354172.12  |
 ANSWER                         | 2022-07-20 17:56:15.681486        | Willy Wonka       | 1604      | 1604      | s         | mycontext  | PJSIP/xfloi61j-0000000d  | 1658354172.12  | 1658354172.12  |
 ANSWER                         | 2022-07-20 17:56:15.681914        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  |
 BRIDGE_ENTER                   | 2022-07-20 17:56:15.685321        | Willy Wonka       | 1604      | 1604      |           | mycontext  | PJSIP/xfloi61j-0000000d  | 1658354172.12  | 1658354172.12  | {"bridge_id":"e2cfd944-9a3e-4885-9ee9-9d1b33886ecf","bridge_technology":"simple_bridge"}
 BRIDGE_ENTER                   | 2022-07-20 17:56:15.687332        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  | {"bridge_id":"e2cfd944-9a3e-4885-9ee9-9d1b33886ecf","bridge_technology":""simple_bridge"}
 BRIDGE_EXIT                    | 2022-07-20 17:56:18.109222        | Willy Wonka       | 1604      | 1604      |           | mycontext  | PJSIP/xfloi61j-0000000d  | 1658354172.12  | 1658354172.12  | {"bridge_id":"e2cfd944-9a3e-4885-9ee9-9d1b33886ecf","bridge_technology":"simple_bridge"}
 HANGUP                         | 2022-07-20 17:56:18.11027         | Willy Wonka       | 1604      | 1604      |           | mycontext  | PJSIP/xfloi61j-0000000d  | 1658354172.12  | 1658354172.12  | {"hangupcause":16,"hangupsource":"PJSIP/xfloi61j-0000000d","dialstatus":""}
 CHAN_END                       | 2022-07-20 17:56:18.11027         | Willy Wonka       | 1604      | 1604      |           | mycontext  | PJSIP/xfloi61j-0000000d  | 1658354172.12  | 1658354172.12  |
 BRIDGE_EXIT                    | 2022-07-20 17:56:18.114121        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  | {"bridge_id":"e2cfd944-9a3e-4885-9ee9-9d1b33886ecf","bridge_technology":"simple_bridge"}
 HANGUP                         | 2022-07-20 17:56:18.116943        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  | {"hangupcause":16,"hangupsource":"PJSIP/xfloi61j-0000000d","dialstatus":"ANSWER"}
 CHAN_END                       | 2022-07-20 17:56:18.116943        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  |
 LINKEDID_END                   | 2022-07-20 17:56:18.116943        | Harry Potter      | 1603      | 1603      | s         | user       | PJSIP/cul113qn-0000000c  | 1658354172.12  | 1658354172.12  |
'''
    )
    def test_internal_call_has_destination_details_setup_correctly(self):
        user_uuid = 'c3f297bd-93e1-46f6-a309-79b320acb7fb'
        user_name = 'Willy Wonka'
        self._assert_last_call_log_matches(
            '1658354172.12',
            has_properties(
                direction='internal',
                destination_details=contains_inanyorder(
                    has_properties(
                        destination_details_key='type',
                        destination_details_value='user',
                    ),
                    has_properties(
                        destination_details_key='user_uuid',
                        destination_details_value=user_uuid,
                    ),
                    has_properties(
                        destination_details_key='user_name',
                        destination_details_value=user_name,
                    ),
                ),
            ),
        )

    @raw_cels(
        '''\
 eventtype                      | eventtime                         | cid_name              | cid_num       | cid_ani   | exten     | context       | channame                  | linkedid      | uniqueid          | extra
--------------------------------+-----------------------------------+-----------------------+---------------+-----------+-----------+---------------+---------------------------+---------------+-------------------+-------------------------------------------------------------------------------------------------------------------------------------------------
 CHAN_START                     | 2022-07-21 09:31:28.178728        | Harry Potter          | 1603          |           | 91800     | mycontext     | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      |
 XIVO_INCALL                    | 2022-07-21 09:31:28.236466        | Harry Potter          | 1603          | 1603      | s         | did           | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"extra":"006a72c4-eb68-481a-808f-33b28ec109c8"}
 WAZO_CALL_LOG_DESTINATION      | 2022-07-21 09:31:28.73542         | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"extra":"type: user,uuid: cb79f29b-f69a-4b93-85c2-49dcce119a9f,name: Harry Potter"}
 APP_START                      | 2022-07-21 09:31:28.758777        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      |
 CHAN_START                     | 2022-07-21 09:31:28.764391        | Harry Potter          | 1603          |           | s         | mycontext     | PJSIP/cul113qn-00000001   | 1658410288.0  | 1658410288.1      |
 ANSWER                         | 2022-07-21 09:31:31.637187        | Harry Potter          | 1603          | 1603      | s         | mycontext     | PJSIP/cul113qn-00000001   | 1658410288.0  | 1658410288.1      |
 ANSWER                         | 2022-07-21 09:31:31.637723        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      |
 BRIDGE_ENTER                   | 2022-07-21 09:31:31.641326        | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000001   | 1658410288.0  | 1658410288.1      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
 BRIDGE_ENTER                   | 2022-07-21 09:31:31.643468        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
 BRIDGE_EXIT                    | 2022-07-21 09:31:36.363285        | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000001   | 1658410288.0  | 1658410288.1      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
 HANGUP                         | 2022-07-21 09:31:36.36417         | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000001   | 1658410288.0  | 1658410288.1      | {"hangupcause":16,"hangupsource":"PJSIP/cul113qn-00000001","dialstatus":""}
 CHAN_END                       | 2022-07-21 09:31:36.36417         | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000001   | 1658410288.0  | 1658410288.1      |
 BRIDGE_EXIT                    | 2022-07-21 09:31:36.367518        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
 HANGUP                         | 2022-07-21 09:31:36.373807        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"hangupcause":16,"hangupsource":"PJSIP/cul113qn-00000001","dialstatus":"ANSWER"}
 CHAN_END                       | 2022-07-21 09:31:36.373807        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      |
 LINKEDID_END                   | 2022-07-21 09:31:36.373807        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      |
'''
    )
    def test_incoming_call_has_destination_details_setup_correctly(self):
        user_uuid = 'cb79f29b-f69a-4b93-85c2-49dcce119a9f'
        user_name = 'Harry Potter'
        self._assert_last_call_log_matches(
            '1658410288.0',
            has_properties(
                tenant_uuid='006a72c4-eb68-481a-808f-33b28ec109c8',
                direction='inbound',
                destination_details=contains_inanyorder(
                    has_properties(
                        destination_details_key='type',
                        destination_details_value='user',
                    ),
                    has_properties(
                        destination_details_key='user_uuid',
                        destination_details_value=user_uuid,
                    ),
                    has_properties(
                        destination_details_key='user_name',
                        destination_details_value=user_name,
                    ),
                ),
            ),
        )

    @raw_cels(
        '''\
 eventtype                      | eventtime                         | cid_name              | cid_num       | cid_ani   | exten         | context       | channame                  | linkedid      | uniqueid          | extra
--------------------------------+-----------------------------------+-----------------------+---------------+-----------+---------------+---------------+---------------------------+---------------+-------------------+--------------------------------------------------------------------------------------------------
 CHAN_START                     | 2022-07-22 18:56:20.25982         | Harry Potter          | 1603          |           | *41250219     | mycontext     | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      |
 WAZO_MEETING_NAME              | 2022-07-22 18:56:20.276538        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      | {"extra":"Meeting with Harry Potter"}
 WAZO_CALL_LOG_DESTINATION      | 2022-07-22 18:56:20.276577        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      | {"extra":"type: meeting,uuid: 9195757f-c381-4f38-b684-98fef848f48b,name: Meeting with Harry Potter"}
 ANSWER                         | 2022-07-22 18:56:20.276866        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      |
 BRIDGE_ENTER                   | 2022-07-22 18:56:20.820304        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      | {"bridge_id":"14307928-6fa7-44f7-b121-f297d47863c4","bridge_technology":"softmix"}
 BRIDGE_EXIT                    | 2022-07-22 18:56:52.836832        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      | {"bridge_id":"14307928-6fa7-44f7-b121-f297d47863c4","bridge_technology":"softmix"}
 HANGUP                         | 2022-07-22 18:56:53.053578        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      | {"hangupcause":16,"hangupsource":"PJSIP/cul113qn-00000001","dialstatus":""}
 CHAN_END                       | 2022-07-22 18:56:53.053578        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      |
 LINKEDID_END                   | 2022-07-22 18:56:53.053578        | Harry Potter          | 1603          | 1603      | participant   | wazo-meeting  | PJSIP/cul113qn-00000001   | 1658530580.3  | 1658530580.3      |
'''
    )
    def test_meeting_has_destination_details_setup_correctly(self):
        meeting_uuid = '9195757f-c381-4f38-b684-98fef848f48b'
        meeting_name = 'Meeting with Harry Potter'
        self._assert_last_call_log_matches(
            '1658530580.3',
            has_properties(
                destination_details=contains_inanyorder(
                    has_properties(
                        destination_details_key='type',
                        destination_details_value='meeting',
                    ),
                    has_properties(
                        destination_details_key='meeting_uuid',
                        destination_details_value=meeting_uuid,
                    ),
                    has_properties(
                        destination_details_key='meeting_name',
                        destination_details_value=meeting_name,
                    ),
                ),
            ),
        )

    @raw_cels(
        '''\
 eventtype                      | eventtime                         | cid_name              | cid_num       | cid_ani   | exten         | context       | channame                  | linkedid      | uniqueid          | extra
--------------------------------+-----------------------------------+-----------------------+---------------+-----------+---------------+---------------+---------------------------+---------------+-------------------+--------------------------------------------------------------------------------------------------
 CHAN_START                     | 2022-07-22 19:18:47.630038        | Harry Potter          | 1603          |           | 1900          | mycontext     | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     |
 WAZO_CONFERENCE                | 2022-07-22 19:18:47.667896        | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     | {"extra":" NAME: myconference"}
 ANSWER                         | 2022-07-22 19:18:47.671298        | Harry Potter          | 1603          | 1603      | pickup        | xivo-pickup   | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     |
 WAZO_CALL_LOG_DESTINATION      | 2022-07-22 19:18:48.698413        | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     | {"extra":"type: conference,id: 1"}
 BRIDGE_ENTER                   | 2022-07-22 19:18:52.804353        | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     | {"bridge_id":"1f633aec-e2f9-4910-a8bb-0601439fab15","bridge_technology":"softmix"}
 BRIDGE_EXIT                    | 2022-07-22 19:18:53.150128        | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     | {"bridge_id":"1f633aec-e2f9-4910-a8bb-0601439fab15","bridge_technology":"softmix"}
 HANGUP                         | 2022-07-22 19:18:53.54901         | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     | {"hangupcause":16,"hangupsource":"PJSIP/cul113qn-00000004","dialstatus":""}
 CHAN_END                       | 2022-07-22 19:18:53.54901         | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     |
 LINKEDID_END                   | 2022-07-22 19:18:53.54901         | Harry Potter          | 1603          | 1603      | s             | conference    | PJSIP/cul113qn-00000004   | 1658531927.10 | 1658531927.10     |
'''
    )
    def test_conference_has_destination_details_setup_correctly(self):
        conference_id = '1'
        self._assert_last_call_log_matches(
            '1658531927.10',
            has_properties(
                destination_details=contains_inanyorder(
                    has_properties(
                        destination_details_key='type',
                        destination_details_value='conference',
                    ),
                    has_properties(
                        destination_details_key='conference_id',
                        destination_details_value=conference_id,
                    ),
                ),
            ),
        )

    @raw_cels(
        '''\
  eventtype   |         eventtime          |       channame        |   uniqueid    |   linkedid    | cid_name | cid_num | extra
--------------+----------------------------+-----------------------+---------------+---------------+----------+---------+-------------------------------------------------
 CHAN_START   | 2017-11-10 10:07:08.620283 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 042302  |
 XIVO_INCALL  | 2017-11-10 10:07:08.877093 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   | {"extra": "2c34c282-433e-4bb8-8d56-fec14ff7e1e9"}
 APP_START    | 2017-11-10 10:07:09.15148  | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
 CHAN_START   | 2017-11-10 10:07:09.156027 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645    |
 ANSWER       | 2017-11-10 10:07:11.986921 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645    |
 ANSWER       | 2017-11-10 10:07:11.993852 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
 BRIDGE_ENTER | 2017-11-10 10:07:11.996672 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645    |
 BRIDGE_ENTER | 2017-11-10 10:07:12.007126 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
 BRIDGE_EXIT  | 2017-11-10 10:07:13.69614  | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645    |
 HANGUP       | 2017-11-10 10:07:13.756533 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645    |
 CHAN_END     | 2017-11-10 10:07:13.758228 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645    |
 BRIDGE_EXIT  | 2017-11-10 10:07:13.759858 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
 HANGUP       | 2017-11-10 10:07:13.761307 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
 CHAN_END     | 2017-11-10 10:07:13.762793 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
 LINKEDID_END | 2017-11-10 10:07:13.764775 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302   |
'''
    )
    def test_incoming_call_no_cid_name_rewritten_cid_num(self):
        self._assert_last_call_log_matches(
            '1510326428.26',
            has_properties(
                source_name='',
                source_exten='42302',
                tenant_uuid='2c34c282-433e-4bb8-8d56-fec14ff7e1e9',
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
        events = self.bus.accumulator(headers={'name': 'call_log_created'})
        user_events = self.bus.accumulator(headers={'name': 'call_log_user_created'})
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
                    accumulator.accumulate(with_headers=True),
                    contains_inanyorder(
                        has_entries(
                            message=has_entries(
                                data=has_entries(tenant_uuid=SERVICE_TENANT)
                            ),
                            headers=has_entries(
                                name='call_log_created',
                                tenant_uuid=SERVICE_TENANT,
                            ),
                        )
                    ),
                )

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), empty())

            until.assert_(call_log_has_no_user_uuid, tries=5)
            until.assert_(bus_event_call_log_created, events, tries=10, interval=0.25)
            until.assert_(
                bus_event_call_log_user_created, user_events, tries=10, interval=0.25
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
        events = self.bus.accumulator(headers={'name': 'call_log_created'})
        user_events = self.bus.accumulator(headers={'name': 'call_log_user_created'})
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
                    accumulator.accumulate(with_headers=True),
                    contains_inanyorder(
                        has_entries(
                            message=has_entries(data=has_key('tags')),
                            headers=has_entries(
                                name='call_log_created',
                                tenant_uuid=USERS_TENANT,
                            ),
                        )
                    ),
                )

            def bus_event_call_log_user_created(accumulator):
                assert_that(
                    accumulator.accumulate(with_headers=True),
                    contains_inanyorder(
                        has_entries(
                            message=has_entries(
                                data=not_(has_key('tags')),
                            ),
                            headers=has_entries(
                                {f'user_uuid:{USER_1_UUID}': True},
                                name='call_log_user_created',
                                required_acl=f'events.call_log.user.{USER_1_UUID}.created',
                                tenant_uuid=USERS_TENANT,
                            ),
                        ),
                        has_entries(
                            message=has_entries(
                                data=not_(has_key('tags')),
                            ),
                            headers=has_entries(
                                {f'user_uuid:{USER_2_UUID}': True},
                                name='call_log_user_created',
                                required_acl=f'events.call_log.user.{USER_2_UUID}.created',
                                tenant_uuid=USERS_TENANT,
                            ),
                        ),
                    ),
                )

            until.assert_(call_log_has_both_user_uuid_and_tenant_uuid, tries=5)
            until.assert_(bus_event_call_log_created, events, tries=10, interval=0.25)
            until.assert_(
                bus_event_call_log_user_created, user_events, tries=10, interval=0.25
            )

    @raw_cels(
        '''\
   eventtype   |         eventtime          | cid_name | cid_num |       exten       |   context   |      channame       |   uniqueid   |   linkedid   | extra
---------------+----------------------------+----------+---------+-------------------+-------------+---------------------+--------------+--------------+-----------
 CHAN_START    | 2018-04-24 14:27:17.922298 | Alicé    | 101     | 102               | default     | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 |
 XIVO_USER_FWD | 2018-04-24 14:27:18.249093 | Alicé    | 101     | forward_voicemail | user        | SCCP/101-00000005   | 1524594437.7 | 1524594437.7 | {"extra":"NUM:102,CONTEXT:default,NAME:Bob Lépine"}
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
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
            MockUser(USER_2_UUID, USERS_TENANT, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='101',
                users=[{'uuid': USER_1_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            ),
            MockLine(
                id=2,
                name='rku3uo',
                users=[{'uuid': USER_2_UUID}],
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
                requested_name='Bob Lépine',
                requested_exten='102',
                requested_context='default',
                requested_internal_exten='102',
                requested_internal_context='default',
                destination_name='Charlié',
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
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='101',
                users=[{'uuid': USER_1_UUID}],
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
                requested_name='Arsène Lupin',
                requested_exten='999101',
                requested_context='from-extern',
                requested_internal_exten='101',
                requested_internal_context='default',
                destination_name='Arsène Lupin',
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

    @raw_cels(
        '''\
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
    '''
    )
    def test_answered_internal(self):
        self._assert_last_call_log_matches(
            '1434650936.31',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:08:56.910686+00:00'),
                date_answer=datetime.fromisoformat('2015-06-18 14:08:59.878+00:00'),
                date_end=datetime.fromisoformat('2015-06-18 14:09:02.271033+00:00'),
                source_name='Elès 45',
                source_exten='1045',
                source_line_identity='sip/as2mkq',
                requested_name='Elès 01',
                requested_exten='1001',
                requested_context='default',
                destination_name='Elès 01',
                destination_exten='1001',
                destination_line_identity='sip/je5qtq',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime                  | cid_name | cid_num | exten | context | channame            |      uniqueid |     linkedid  | userfield

 CHAN_START   | 2015-06-18 14:10:24.586638 | Elès 45  | 1045    | 1001  | default | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 APP_START    | 2015-06-18 14:10:24.6893   | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 CHAN_START   | 2015-06-18 14:10:24.694166 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000022 | 1434651024.34 | 1434651024.33 |
 HANGUP       | 2015-06-18 14:10:28.280456 | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000022 | 1434651024.34 | 1434651024.33 |
 CHAN_END     | 2015-06-18 14:10:28.28819  | Elès 01  | 1001    | s     | default | SIP/je5qtq-00000022 | 1434651024.34 | 1434651024.33 |
 HANGUP       | 2015-06-18 14:10:28.289431 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 CHAN_END     | 2015-06-18 14:10:28.290746 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
 LINKEDID_END | 2015-06-18 14:10:28.292243 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-00000021 | 1434651024.33 | 1434651024.33 |
    '''
    )
    def test_internal_no_answer(self):
        self._assert_last_call_log_matches(
            '1434651024.33',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:10:24.586638+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2015-06-18 14:10:28.290746+00:00'),
                source_name='Elès 45',
                source_exten='1045',
                source_line_identity='sip/as2mkq',
                requested_name='Elès 01',
                requested_exten='1001',
                requested_context='default',
                destination_name='Elès 01',
                destination_exten='1001',
                destination_line_identity='sip/je5qtq',
            ),
        )

    @raw_cels(
        '''\
 eventtype     | eventtime                  | cid_name         | cid_num | exten             | context     | channame            | uniqueid      | linkedid      | extra

 CHAN_START    | 2018-02-02 15:00:25.106723 | Alice            |     101 | 103               | default     | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 XIVO_USER_FWD | 2018-02-02 15:00:25.546267 | Alice            |     101 | forward_voicemail | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 | {"extra":"NUM:103,CONTEXT:default,NAME:Charlie"}
 ANSWER        | 2018-02-02 15:00:26.051203 | Alice            |     101 | pickup            | xivo-pickup | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 APP_START     | 2018-02-02 15:00:27.373161 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 CHAN_START    | 2018-02-02 15:00:27.392589 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17 |
 ANSWER        | 2018-02-02 15:00:29.207311 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17 |
 BRIDGE_ENTER  | 2018-02-02 15:00:29.227529 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17 |
 BRIDGE_ENTER  | 2018-02-02 15:00:29.22922  | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 BRIDGE_EXIT   | 2018-02-02 15:00:30.464687 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17 |
 HANGUP        | 2018-02-02 15:00:30.471676 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17 |
 CHAN_END      | 2018-02-02 15:00:30.476368 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000a | 1517601627.18 | 1517601625.17 |
 BRIDGE_EXIT   | 2018-02-02 15:00:30.478914 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 HANGUP        | 2018-02-02 15:00:30.481403 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 CHAN_END      | 2018-02-02 15:00:30.484065 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
 LINKEDID_END  | 2018-02-02 15:00:30.486225 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000007   | 1517601625.17 | 1517601625.17 |
    '''
    )
    def test_internal_unconditional_forwarded_answered_call(self):
        self._assert_last_call_log_matches(
            '1517601625.17',
            has_properties(
                date=datetime.fromisoformat('2018-02-02 15:00:25.106723+00:00'),
                date_answer=datetime.fromisoformat('2018-02-02 15:00:29.229220+00:00'),
                date_end=datetime.fromisoformat('2018-02-02 15:00:30.484065+00:00'),
                source_exten='101',
                source_line_identity='sccp/101',
                requested_name='Charlie',
                requested_exten='103',
                requested_context='default',
                requested_internal_exten='103',
                requested_internal_context='default',
                destination_name='Bernard',
                destination_exten='102',
                destination_line_identity='sip/dm77z3',
            ),
        )

    @raw_cels(
        '''\
 eventtype     | eventtime                  | cid_name         | cid_num | exten             | context     | channame            | uniqueid      | linkedid      | extra

 CHAN_START    | 2018-02-06 13:33:31.114956 | Alice            |     101 | 103               | default     | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 APP_START     | 2018-02-06 13:33:31.897767 | Alice            |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 CHAN_START    | 2018-02-06 13:33:31.927285 | Charlie          |     103 | s                 | default     | SIP/rku3uo-0000000e | 1517942011.17 | 1517942011.16 |
 HANGUP        | 2018-02-06 13:33:33.272605 | Charlie          |     103 | s                 | default     | SIP/rku3uo-0000000e | 1517942011.17 | 1517942011.16 |
 CHAN_END      | 2018-02-06 13:33:33.287358 | Charlie          |     103 | s                 | default     | SIP/rku3uo-0000000e | 1517942011.17 | 1517942011.16 |
 XIVO_USER_FWD | 2018-02-06 13:33:33.28969  | Alice            |     101 | forward_voicemail | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 | {"extra":"NUM:103,CONTEXT:default,NAME:Charlie"}
 ANSWER        | 2018-02-06 13:33:33.778962 | Alice            |     101 | pickup            | xivo-pickup | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 APP_START     | 2018-02-06 13:33:35.089841 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 CHAN_START    | 2018-02-06 13:33:35.107786 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16 |
 ANSWER        | 2018-02-06 13:33:36.315745 | Bernard          |     102 | s                 | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16 |
 BRIDGE_ENTER  | 2018-02-06 13:33:36.331304 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16 |
 BRIDGE_ENTER  | 2018-02-06 13:33:36.333193 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 BRIDGE_EXIT   | 2018-02-06 13:33:37.393726 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16 |
 HANGUP        | 2018-02-06 13:33:37.401862 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16 |
 CHAN_END      | 2018-02-06 13:33:37.404542 | Bernard          |     102 |                   | default     | SIP/dm77z3-0000000f | 1517942015.18 | 1517942011.16 |
 BRIDGE_EXIT   | 2018-02-06 13:33:37.407847 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 HANGUP        | 2018-02-06 13:33:37.410228 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 CHAN_END      | 2018-02-06 13:33:37.412453 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
 LINKEDID_END  | 2018-02-06 13:33:37.414762 | Charlie -> Alice |     101 | s                 | user        | SCCP/101-00000002   | 1517942011.16 | 1517942011.16 |
    '''
    )
    def test_internal_busy_fwd_answered_call(self):
        self._assert_last_call_log_matches(
            '1517942011.16',
            has_properties(
                date=datetime.fromisoformat('2018-02-06 13:33:31.114956+00:00'),
                date_answer=datetime.fromisoformat('2018-02-06 13:33:36.333193+00:00'),
                date_end=datetime.fromisoformat('2018-02-06 13:33:37.412453+00:00'),
                source_exten='101',
                source_line_identity='sccp/101',
                requested_name='Charlie',
                requested_exten='103',
                requested_context='default',
                requested_internal_exten='103',
                requested_internal_context='default',
                destination_name='Bernard',
                destination_exten='102',
                destination_line_identity='sip/dm77z3',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime             | cid_name   |    cid_num | exten | context     | channame            |      uniqueid |      linkedid

 CHAN_START   | 2013-01-01 11:02:38.0 | 612345678  |  612345678 | 1002  | from-extern | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 APP_START    | 2013-01-01 11:02:38.1 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 CHAN_START   | 2013-01-01 11:02:38.2 | Bob Marley |       1002 | s     | default     | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 ANSWER       | 2013-01-01 11:02:42.0 | Bob Marley |       1002 | s     | default     | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 ANSWER       | 2013-01-01 11:02:42.1 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 BRIDGE_START | 2013-01-01 11:02:42.2 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 BRIDGE_END   | 2013-01-01 11:02:45.0 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 HANGUP       | 2013-01-01 11:02:45.1 | Bob Marley |       1002 |       | user        | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 CHAN_END     | 2013-01-01 11:02:45.2 | Bob Marley |       1002 |       | user        | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 HANGUP       | 2013-01-01 11:02:45.3 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 CHAN_END     | 2013-01-01 11:02:45.4 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 LINKEDID_END | 2013-01-01 11:02:45.5 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
    '''
    )
    def test_answered_incoming_call(self):
        self._assert_last_call_log_matches(
            '1376060558.17',
            has_properties(
                date=datetime.fromisoformat('2013-01-01 11:02:38.000000+00:00'),
                date_answer=datetime.fromisoformat('2013-01-01 11:02:42.200000+00:00'),
                date_end=datetime.fromisoformat('2013-01-01 11:02:45.400000+00:00'),
                source_name='612345678',
                source_exten='0612345678',
                source_line_identity='sip/trunk',
                requested_name='Bob Marley',
                requested_exten='1002',
                requested_context='from-extern',
                destination_name='Bob Marley',
                destination_exten='1002',
                destination_line_identity='sip/hg63xv',
            ),
        )

    @raw_cels(
        '''\
 eventtype     | eventtime             | cid_name   |    cid_num  | exten             | context     | channame                | uniqueid      | linkedid      | extra

 CHAN_START    | 2020-04-06 14:44:08.0 | fb          | 0123456789 | 000101            | from-extern | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
 XIVO_INCALL   | 2020-04-06 14:44:08.1 | fb          | 0123456789 | s                 | did         | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
 XIVO_USER_FWD | 2020-04-06 14:44:08.2 | fb          | 0123456789 | forward_voicemail | user        | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 | {"extra":"NUM:101,CONTEXT:internal1,NAME:Alicié"}
 ANSWER        | 2020-04-06 14:44:08.3 | fb          | 0123456789 | pickup            | xivo-pickup | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
 APP_START     | 2020-04-06 14:44:13.0 | fb          | 0123456789 | s                 | user        | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
 CHAN_START    | 2020-04-06 14:44:13.0 | Bob Marley  | 102        | s                 | internal2   | PJSIP/qo6ac582-0000001c | 1586198653.36 | 1586198648.35 |
 HANGUP        | 2020-04-06 14:44:15.0 | Bob Marley  | 102        | s                 | internal2   | PJSIP/qo6ac582-0000001c | 1586198653.36 | 1586198648.35 |
 CHAN_END      | 2020-04-06 14:44:15.1 | Bob Marley  | 102        | s                 | internal2   | PJSIP/qo6ac582-0000001c | 1586198653.36 | 1586198648.35 |
 XIVO_USER_FWD | 2020-04-06 14:44:15.2 | fb          | 0123456789 | forward_voicemail | user        | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 | {"extra":"NUM:102,CONTEXT:internal2,NAME:Bob Marley"}
 HANGUP        | 2020-04-06 14:44:17.0 | fb          | 0123456789 | unreachable       | user        | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
 CHAN_END      | 2020-04-06 14:44:17.1 | fb          | 0123456789 | unreachable       | user        | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
 LINKEDID_END  | 2020-04-06 14:44:17.2 | fb          | 0123456789 | unreachable       | user        | PJSIP/dev_44-0000001b   | 1586198648.35 | 1586198648.35 |
    '''
    )
    def test_not_answered_incoming_call_with_unconditional_forward(self):
        self._assert_last_call_log_matches(
            '1586198648.35',
            has_properties(
                date=datetime.fromisoformat('2020-04-06 14:44:08.000000+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2020-04-06 14:44:17.100000+00:00'),
                source_name='fb',
                source_exten='0123456789',
                source_line_identity='pjsip/dev_44',
                requested_name='Alicié',
                requested_exten='000101',
                requested_context='from-extern',
                requested_internal_exten='101',
                requested_internal_context='internal1',
                destination_name='Bob Marley',
                destination_exten='102',
                destination_line_identity='pjsip/qo6ac582',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime             | cid_name   |    cid_num | exten | context     | channame            |      uniqueid |      linkedid

 CHAN_START   | 2013-01-01 11:02:38.0 | 612345678  |  612345678 | s     | from-extern | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 XIVO_FROM_S  | 2013-01-01 11:02:38.1 | 612345678  |  612345678 | 1002  | from-extern | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 APP_START    | 2013-01-01 11:02:38.1 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 CHAN_START   | 2013-01-01 11:02:38.2 | Bob Marley |       1002 | s     | default     | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 ANSWER       | 2013-01-01 11:02:42.0 | Bob Marley |       1002 | s     | default     | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 ANSWER       | 2013-01-01 11:02:42.1 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 BRIDGE_START | 2013-01-01 11:02:42.2 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 BRIDGE_END   | 2013-01-01 11:02:45.0 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 HANGUP       | 2013-01-01 11:02:45.1 | Bob Marley |       1002 |       | user        | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 CHAN_END     | 2013-01-01 11:02:45.2 | Bob Marley |       1002 |       | user        | SIP/hg63xv-00000013 | 1376060558.18 | 1376060558.17
 HANGUP       | 2013-01-01 11:02:45.3 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 CHAN_END     | 2013-01-01 11:02:45.4 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
 LINKEDID_END | 2013-01-01 11:02:45.5 |            | 0612345678 | s     | user        | SIP/trunk-00000028  | 1376060558.17 | 1376060558.17
    '''
    )
    def test_answered_incoming_call_on_s(self):
        self._assert_last_call_log_matches(
            '1376060558.17',
            has_properties(
                date=datetime.fromisoformat('2013-01-01 11:02:38.000000+00:00'),
                date_answer=datetime.fromisoformat('2013-01-01 11:02:42.200000+00:00'),
                date_end=datetime.fromisoformat('2013-01-01 11:02:45.400000+00:00'),
                source_name='612345678',
                source_exten='0612345678',
                source_line_identity='sip/trunk',
                requested_name='Bob Marley',
                requested_exten='1002',
                requested_context='from-extern',
                destination_name='Bob Marley',
                destination_exten='1002',
                destination_line_identity='sip/hg63xv',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime                  | cid_name | cid_num   | exten     | context     | channame              |      uniqueid |     linkedid  | userfield

 CHAN_START   | 2015-06-18 14:12:05.935283 | Elès 01  | 1001      | **9642301 | default     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 XIVO_OUTCALL | 2015-06-18 14:12:06.118509 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 APP_START    | 2015-06-18 14:12:06.123695 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 CHAN_START   | 2015-06-18 14:12:06.124957 |          |           | s         | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
 ANSWER       | 2015-06-18 14:12:12.500153 |          | **9642301 | dial      | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
 ANSWER       | 2015-06-18 14:12:12.514389 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 BRIDGE_ENTER | 2015-06-18 14:12:12.515753 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 BRIDGE_ENTER | 2015-06-18 14:12:12.517027 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
 BRIDGE_EXIT  | 2015-06-18 14:12:16.85455  | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 HANGUP       | 2015-06-18 14:12:16.861414 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 CHAN_END     | 2015-06-18 14:12:16.862638 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000025   | 1434651125.37 | 1434651125.37 |
 BRIDGE_EXIT  | 2015-06-18 14:12:16.863979 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
 HANGUP       | 2015-06-18 14:12:16.865316 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
 CHAN_END     | 2015-06-18 14:12:16.866615 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
 LINKEDID_END | 2015-06-18 14:12:16.867848 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000026 | 1434651126.38 | 1434651125.37 |
    '''
    )
    def test_answered_outgoing_call(self):
        self._assert_last_call_log_matches(
            '1434651125.37',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:12:05.935283+00:00'),
                date_answer=datetime.fromisoformat('2015-06-18 14:12:12.515753+00:00'),
                date_end=datetime.fromisoformat('2015-06-18 14:12:16.862638+00:00'),
                source_name='Elès 01',
                source_exten='1001',
                source_line_identity='sip/je5qtq',
                requested_name='',
                requested_exten='**9642301',
                requested_context='default',
                destination_name='',
                destination_exten='**9642301',
                destination_line_identity='sip/dev_34-1',
                user_field='',
            ),
        )

    @raw_cels(
        '''\
    eventtype     |           eventtime           |   cid_name   |  cid_num   |   exten    |   context   |                                channame                                |   uniqueid   |   linkedid

 CHAN_START       | 2021-07-19 11:12:54.23216-04  | Olga Romanov | 1015       | 5551112222 | inside      | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 MIXMONITOR_START | 2021-07-19 11:12:54.764512-04 | O Romanov    | 5550001234 | s          | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 XIVO_OUTCALL     | 2021-07-19 11:12:54.776572-04 | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 APP_START        | 2021-07-19 11:12:54.805195-04 | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 CHAN_START       | 2021-07-19 11:12:54.806786-04 | wazo         |            | s          | from-extern | PJSIP/voipms_trunk_2c34c282-433e-4bb8-8d56-fec14ff7e1e9_39756-00000008 | 1626707574.8 | 1626707574.7
 ANSWER           | 2021-07-19 11:13:04.25334-04  |              | 5551112222 | dial       | from-extern | PJSIP/voipms_trunk_2c34c282-433e-4bb8-8d56-fec14ff7e1e9_39756-00000008 | 1626707574.8 | 1626707574.7
 ANSWER           | 2021-07-19 11:13:04.254462-04 | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 BRIDGE_ENTER     | 2021-07-19 11:13:04.258807-04 |              | 5551112222 |            | from-extern | PJSIP/voipms_trunk_2c34c282-433e-4bb8-8d56-fec14ff7e1e9_39756-00000008 | 1626707574.8 | 1626707574.7
 BRIDGE_ENTER     | 2021-07-19 11:13:04.259302-04 | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 BRIDGE_EXIT      | 2021-07-19 11:13:06.99904-04  |              | 5551112222 |            | from-extern | PJSIP/voipms_trunk_2c34c282-433e-4bb8-8d56-fec14ff7e1e9_39756-00000008 | 1626707574.8 | 1626707574.7
 BRIDGE_EXIT      | 2021-07-19 11:13:07.000866-04 | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 HANGUP           | 2021-07-19 11:13:07.002422-04 |              | 5551112222 |            | from-extern | PJSIP/voipms_trunk_2c34c282-433e-4bb8-8d56-fec14ff7e1e9_39756-00000008 | 1626707574.8 | 1626707574.7
 CHAN_END         | 2021-07-19 11:13:07.002422-04 |              | 5551112222 |            | from-extern | PJSIP/voipms_trunk_2c34c282-433e-4bb8-8d56-fec14ff7e1e9_39756-00000008 | 1626707574.8 | 1626707574.7
 HANGUP           | 2021-07-19 11:13:07.00682-04  | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 CHAN_END         | 2021-07-19 11:13:07.00682-04  | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
 LINKEDID_END     | 2021-07-19 11:13:07.00682-04  | O Romanov    | 5550001234 | dial       | outcall     | PJSIP/ru3fqt3x-00000007                                                | 1626707574.7 | 1626707574.7
        '''
    )
    def test_answered_outgoing_call_with_custom_caller_id(self):
        self._assert_last_call_log_matches(
            '1626707574.7',
            has_properties(
                source_name='O Romanov',
                source_exten='5550001234',
                source_internal_name='Olga Romanov',
                requested_exten='5551112222',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime                  | cid_name | cid_num   | exten     | context     | channame              |      uniqueid |     linkedid  | userfield

 CHAN_START   | 2015-06-18 14:13:18.176182 | Elès 01  | 1001      | **9642301 | default     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 |
 XIVO_OUTCALL | 2015-06-18 14:13:18.250067 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 APP_START    | 2015-06-18 14:13:18.254452 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 CHAN_START   | 2015-06-18 14:13:18.255915 |          |           | s         | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
 ANSWER       | 2015-06-18 14:13:20.98612  |          | **9642301 | dial      | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
 ANSWER       | 2015-06-18 14:13:20.998113 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 BRIDGE_ENTER | 2015-06-18 14:13:21.190246 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 BRIDGE_ENTER | 2015-06-18 14:13:21.192798 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
 BRIDGE_EXIT  | 2015-06-18 14:13:24.137056 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 HANGUP       | 2015-06-18 14:13:24.146256 | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 CHAN_END     | 2015-06-18 14:13:24.14759  | Elès 01  | 1001      | dial      | outcall     | SIP/je5qtq-00000027   | 1434651198.39 | 1434651198.39 | foo
 BRIDGE_EXIT  | 2015-06-18 14:13:24.148734 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
 HANGUP       | 2015-06-18 14:13:24.149943 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
 CHAN_END     | 2015-06-18 14:13:24.151296 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
 LINKEDID_END | 2015-06-18 14:13:24.152458 |          | **9642301 |           | from-extern | SIP/dev_34-1-00000028 | 1434651198.40 | 1434651198.39 |
    '''
    )
    def test_answered_outgoing_call_with_userfield(self):
        self._assert_last_call_log_matches(
            '1434651198.39',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:13:18.176182+00:00'),
                date_answer=datetime.fromisoformat('2015-06-18 14:13:21.190246+00:00'),
                date_end=datetime.fromisoformat('2015-06-18 14:13:24.147590+00:00'),
                source_name='Elès 01',
                source_exten='1001',
                source_line_identity='sip/je5qtq',
                requested_exten='**9642301',
                requested_context='default',
                destination_name='',
                destination_exten='**9642301',
                destination_line_identity='sip/dev_34-1',
                user_field='foo',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime             | cid_name         | cid_num | exten | context | channame            | uniqueid      | linkedid

 CHAN_START   | 2013-12-04 14:20:58.0 | Neelix Talaxian  | 1066    | 1624  | default | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 APP_START    | 2013-12-04 14:20:58.1 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 CHAN_START   | 2013-12-04 14:20:58.2 | Donald MacRonald | 1624    | s     | default | SIP/zsp7wv-0000000a | 1386184858.10 | 1386184858.9
 ANSWER       | 2013-12-04 14:21:05.3 | Donald MacRonald | 1624    | s     | default | SIP/zsp7wv-0000000a | 1386184858.10 | 1386184858.9
 ANSWER       | 2013-12-04 14:21:05.4 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 BRIDGE_START | 2013-12-04 14:21:05.5 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 BRIDGE_END   | 2013-12-04 14:21:06.6 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 HANGUP       | 2013-12-04 14:21:06.7 | Donald MacRonald | 1624    |       | user    | SIP/zsp7wv-0000000a | 1386184858.10 | 1386184858.9
 CHAN_END     | 2013-12-04 14:21:06.8 | Donald MacRonald | 1624    |       | user    | SIP/zsp7wv-0000000a | 1386184858.10 | 1386184858.9
 HANGUP       | 2013-12-04 14:21:06.9 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 CHAN_END     | 2013-12-04 14:21:07.1 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
 LINKEDID_END | 2013-12-04 14:21:07.2 | Neelix Talaxian  | 1066    | s     | user    | SIP/2dvtpb-00000009 | 1386184858.9  | 1386184858.9
    '''
    )
    def test_uniqueids_that_do_not_have_the_same_sort_order_chonologically_and_alphabetically(
        self,
    ):
        self._assert_last_call_log_matches(
            '1386184858.9',
            has_properties(
                date=datetime.fromisoformat('2013-12-04 14:20:58.000000+00:00'),
                date_answer=datetime.fromisoformat('2013-12-04 14:21:05.500000+00:00'),
                date_end=datetime.fromisoformat('2013-12-04 14:21:07.100000+00:00'),
                source_name='Neelix Talaxian',
                source_exten='1066',
                source_line_identity='sip/2dvtpb',
                requested_name='Donald MacRonald',
                requested_exten='1624',
                requested_context='default',
                destination_name='Donald MacRonald',
                destination_exten='1624',
                destination_line_identity='sip/zsp7wv',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime                  | cid_name | cid_num | exten | context | channame            |      uniqueid |     linkedid

 CHAN_START   | 2015-06-18 14:15:12.978338 | Elès 45  | 1045    | s     | default | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 ANSWER       | 2015-06-18 14:15:14.587341 | 1001     | 1001    |       | default | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 APP_START    | 2015-06-18 14:15:14.697414 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 CHAN_START   | 2015-06-18 14:15:14.702394 | Elès 01  | 1001    | s     | default | SIP/je5qtq-0000002c | 1434651314.44 | 1434651312.43
 ANSWER       | 2015-06-18 14:15:16.389857 | Elès 01  | 1001    | s     | default | SIP/je5qtq-0000002c | 1434651314.44 | 1434651312.43
 BRIDGE_ENTER | 2015-06-18 14:15:16.396213 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 BRIDGE_ENTER | 2015-06-18 14:15:16.397787 | Elès 01  | 1001    |       | default | SIP/je5qtq-0000002c | 1434651314.44 | 1434651312.43
 BRIDGE_EXIT  | 2015-06-18 14:15:19.192422 | Elès 01  | 1001    |       | default | SIP/je5qtq-0000002c | 1434651314.44 | 1434651312.43
 HANGUP       | 2015-06-18 14:15:19.206152 | Elès 01  | 1001    |       | default | SIP/je5qtq-0000002c | 1434651314.44 | 1434651312.43
 CHAN_END     | 2015-06-18 14:15:19.208217 | Elès 01  | 1001    |       | default | SIP/je5qtq-0000002c | 1434651314.44 | 1434651312.43
 BRIDGE_EXIT  | 2015-06-18 14:15:19.209432 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 HANGUP       | 2015-06-18 14:15:19.211393 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 CHAN_END     | 2015-06-18 14:15:19.212596 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
 LINKEDID_END | 2015-06-18 14:15:19.213763 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002b | 1434651312.43 | 1434651312.43
    '''
    )
    def test_answered_originate(self):
        self._assert_last_call_log_matches(
            '1434651312.43',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:15:12.978338+00:00'),
                date_answer=datetime.fromisoformat('2015-06-18 14:15:16.396213+00:00'),
                date_end=datetime.fromisoformat('2015-06-18 14:15:19.212596+00:00'),
                source_name='Elès 45',
                source_exten='1045',
                source_line_identity='sip/as2mkq',
                requested_name='Elès 01',
                requested_exten='1001',
                requested_context='default',
                destination_name='Elès 01',
                destination_exten='1001',
                destination_line_identity='sip/je5qtq',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime                  | cid_name | cid_num | exten | context | channame            |      uniqueid |     linkedid

 CHAN_START   | 2015-06-18 14:15:48.836632 | Elès 45  | 1045    | s     | default | SIP/as2mkq-0000002d | 1434651348.45 | 1434651348.45
 ANSWER       | 2015-06-18 14:15:50.127815 | 1001     | 1001    |       | default | SIP/as2mkq-0000002d | 1434651348.45 | 1434651348.45
 APP_START    | 2015-06-18 14:15:50.220755 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002d | 1434651348.45 | 1434651348.45
 CHAN_START   | 2015-06-18 14:15:50.22621  | Elès 01  | 1001    | s     | default | SIP/je5qtq-0000002e | 1434651350.46 | 1434651348.45
 HANGUP       | 2015-06-18 14:15:54.936991 | Elès 01  | 1001    | s     | default | SIP/je5qtq-0000002e | 1434651350.46 | 1434651348.45
 CHAN_END     | 2015-06-18 14:15:54.949784 | Elès 01  | 1001    | s     | default | SIP/je5qtq-0000002e | 1434651350.46 | 1434651348.45
 HANGUP       | 2015-06-18 14:15:54.951351 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002d | 1434651348.45 | 1434651348.45
 CHAN_END     | 2015-06-18 14:15:54.952707 | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002d | 1434651348.45 | 1434651348.45
 LINKEDID_END | 2015-06-18 14:15:54.9539   | Elès 45  | 1045    | s     | user    | SIP/as2mkq-0000002d | 1434651348.45 | 1434651348.45
    '''
    )
    def test_unanswered_originate(self):
        self._assert_last_call_log_matches(
            '1434651348.45',
            has_properties(
                date=datetime.fromisoformat('2015-06-18 14:15:48.836632+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2015-06-18 14:15:54.952707+00:00'),
                source_name='Elès 45',
                source_exten='1045',
                source_line_identity='sip/as2mkq',
                requested_name='Elès 01',
                requested_exten='1001',
                requested_context='default',
                destination_name='Elès 01',
                destination_exten='1001',
                destination_line_identity='sip/je5qtq',
            ),
        )

    @raw_cels(
        '''\
 eventtype    | eventtime                  | cid_name | cid_num | exten                | context | channame            |     uniqueid |     linkedid

 CHAN_START   | 2014-02-20 09:28:46.683014 | Carlos   |    1003 | s                    | pcmdev  | SIP/d49t0y-00000003 | 1392906526.4 | 1392906526.4
 ANSWER       | 2014-02-20 09:28:47.183651 | 1002     |    1002 |                      | pcmdev  | SIP/d49t0y-00000003 | 1392906526.4 | 1392906526.4
 APP_START    | 2014-02-20 09:28:47.288346 | Carlos   |    1003 | s                    | user    | SIP/d49t0y-00000003 | 1392906526.4 | 1392906526.4
 CHAN_START   | 2014-02-20 09:28:47.288466 | Bõb      |    1002 | s                    | pcmdev  | SCCP/1002-00000001  | 1392906527.5 | 1392906526.4
 HANGUP       | 2014-02-20 09:29:00.306587 | Bõb      |    1002 | s                    | pcmdev  | SCCP/1002-00000001  | 1392906527.5 | 1392906526.4
 CHAN_END     | 2014-02-20 09:29:00.307651 | Bõb      |    1002 | s                    | pcmdev  | SCCP/1002-00000001  | 1392906527.5 | 1392906526.4
 HANGUP       | 2014-02-20 09:29:00.308165 | Carlos   |    1003 | endcall:hangupsilent | forward | SIP/d49t0y-00000003 | 1392906526.4 | 1392906526.4
 CHAN_END     | 2014-02-20 09:29:00.309786 | Carlos   |    1003 | endcall:hangupsilent | forward | SIP/d49t0y-00000003 | 1392906526.4 | 1392906526.4
 LINKEDID_END | 2014-02-20 09:29:00.309806 | Carlos   |    1003 | endcall:hangupsilent | forward | SIP/d49t0y-00000003 | 1392906526.4 | 1392906526.4
    '''
    )
    def test_originate_hung_up_by_switchboard(self):
        self._assert_last_call_log_matches(
            '1392906526.4',
            has_properties(
                date=datetime.fromisoformat('2014-02-20 09:28:46.683014+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2014-02-20 09:29:00.309786+00:00'),
                source_name='Carlos',
                source_exten='1003',
                source_line_identity='sip/d49t0y',
                requested_name='Bõb',
                requested_exten='1002',
                requested_context='pcmdev',
                destination_name='Bõb',
                destination_exten='1002',
                destination_line_identity='sccp/1002',
            ),
        )

    @raw_cels(
        '''\
  eventtype   |        eventtime      | cid_name |  cid_num  |   exten   |   context   |        channame         |   uniqueid   |   linkedid

 CHAN_START   | 2020-05-04 12:21:47.1 | User 01  | 1001      | **9742310 | internal    | PJSIP/d6jtulhp-00000002 | 1588609307.2 | 1588609307.2
 XIVO_OUTCALL | 2020-05-04 12:21:47.2 | User 01  | 1001      | dial      | outcall     | PJSIP/d6jtulhp-00000002 | 1588609307.2 | 1588609307.2
 APP_START    | 2020-05-04 12:21:47.3 | User 01  | 1001      | dial      | outcall     | PJSIP/d6jtulhp-00000002 | 1588609307.2 | 1588609307.2
 CHAN_START   | 2020-05-04 12:21:47.4 | wazo     |           | s         | from-extern | PJSIP/dev_44-00000003   | 1588609307.3 | 1588609307.2
 HANGUP       | 2020-05-04 12:21:50.1 |          | **9742310 | dial      | from-extern | PJSIP/dev_44-00000003   | 1588609307.3 | 1588609307.2
 CHAN_END     | 2020-05-04 12:21:50.2 |          | **9742310 | dial      | from-extern | PJSIP/dev_44-00000003   | 1588609307.3 | 1588609307.2
 HANGUP       | 2020-05-04 12:21:50.3 | User 01  | 1001      | dial      | outcall     | PJSIP/d6jtulhp-00000002 | 1588609307.2 | 1588609307.2
 CHAN_END     | 2020-05-04 12:21:50.4 | User 01  | 1001      | dial      | outcall     | PJSIP/d6jtulhp-00000002 | 1588609307.2 | 1588609307.2
 LINKEDID_END | 2020-05-04 12:21:50.5 | User 01  | 1001      | dial      | outcall     | PJSIP/d6jtulhp-00000002 | 1588609307.2 | 1588609307.2
    '''
    )
    def test_unanswered_outcall(self):
        self._assert_last_call_log_matches(
            '1588609307.2',
            has_properties(
                date=datetime.fromisoformat('2020-05-04 12:21:47.100000+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2020-05-04 12:21:50.400000+00:00'),
                source_name='User 01',
                source_exten='1001',
                source_line_identity='pjsip/d6jtulhp',
                requested_name='',
                requested_exten='**9742310',
                requested_context='internal',  # FIXME: WAZO-1751 should be to-extern
                destination_name='',
                destination_exten='**9742310',
                destination_line_identity='pjsip/dev_44',
            ),
        )

    @raw_cels(
        '''\
  eventtype   |           eventtime           |                               channame                                |   uniqueid    |   linkedid
--------------+-------------------------------+-----------------------------------------------------------------------+---------------+---------------
 CHAN_START   | 2021-02-08 18:41:01.659557+00 | PJSIP/d6jtulhp-00000005                                               | 1612809661.11 | 1612809661.11
 ANSWER       | 2021-02-08 18:41:01.815568+00 | PJSIP/d6jtulhp-00000005                                               | 1612809661.11 | 1612809661.11
 CHAN_START   | 2021-02-08 18:41:02.941447+00 | Local/64f7ec70-71b7-4430-8446-74d8dc563d33@usersharedlines-00000003;1 | 1612809662.12 | 1612809661.11
 CHAN_START   | 2021-02-08 18:41:02.941561+00 | Local/64f7ec70-71b7-4430-8446-74d8dc563d33@usersharedlines-00000003;2 | 1612809662.13 | 1612809661.11
 CHAN_START   | 2021-02-08 18:41:02.942066+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;1 | 1612809662.14 | 1612809661.11
 CHAN_START   | 2021-02-08 18:41:02.942112+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;2 | 1612809662.15 | 1612809661.11
 CHAN_START   | 2021-02-08 18:41:02.961053+00 | PJSIP/uzyebgp2-00000006                                               | 1612809662.16 | 1612809661.11
 CHAN_START   | 2021-02-08 18:41:02.973626+00 | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 ANSWER       | 2021-02-08 18:41:07.285784+00 | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 ANSWER       | 2021-02-08 18:41:07.28644+00  | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;2 | 1612809662.15 | 1612809661.11
 BRIDGE_ENTER | 2021-02-08 18:41:07.287287+00 | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 BRIDGE_ENTER | 2021-02-08 18:41:07.287658+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;2 | 1612809662.15 | 1612809661.11
 ANSWER       | 2021-02-08 18:41:07.288317+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;1 | 1612809662.14 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:07.289082+00 | Local/64f7ec70-71b7-4430-8446-74d8dc563d33@usersharedlines-00000003;1 | 1612809662.12 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:07.289082+00 | Local/64f7ec70-71b7-4430-8446-74d8dc563d33@usersharedlines-00000003;1 | 1612809662.12 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:07.291606+00 | Local/64f7ec70-71b7-4430-8446-74d8dc563d33@usersharedlines-00000003;2 | 1612809662.13 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:07.291606+00 | Local/64f7ec70-71b7-4430-8446-74d8dc563d33@usersharedlines-00000003;2 | 1612809662.13 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:07.292405+00 | PJSIP/uzyebgp2-00000006                                               | 1612809662.16 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:07.292405+00 | PJSIP/uzyebgp2-00000006                                               | 1612809662.16 | 1612809661.11
 BRIDGE_ENTER | 2021-02-08 18:41:07.314984+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;1 | 1612809662.14 | 1612809661.11
 BRIDGE_ENTER | 2021-02-08 18:41:07.315137+00 | PJSIP/d6jtulhp-00000005                                               | 1612809661.11 | 1612809661.11
 BRIDGE_EXIT  | 2021-02-08 18:41:07.315452+00 | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 BRIDGE_EXIT  | 2021-02-08 18:41:07.31554+00  | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;1 | 1612809662.14 | 1612809661.11
 BRIDGE_ENTER | 2021-02-08 18:41:07.315559+00 | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:07.315862+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;1 | 1612809662.14 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:07.315862+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;1 | 1612809662.14 | 1612809661.11
 BRIDGE_EXIT  | 2021-02-08 18:41:07.316473+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;2 | 1612809662.15 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:07.316698+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;2 | 1612809662.15 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:07.316698+00 | Local/03d26082-7c29-4db3-9814-79ba30640b47@usersharedlines-00000004;2 | 1612809662.15 | 1612809661.11
 BRIDGE_EXIT  | 2021-02-08 18:41:08.891712+00 | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 BRIDGE_EXIT  | 2021-02-08 18:41:08.891858+00 | PJSIP/d6jtulhp-00000005                                               | 1612809661.11 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:08.892839+00 | PJSIP/d6jtulhp-00000005                                               | 1612809661.11 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:08.892839+00 | PJSIP/d6jtulhp-00000005                                               | 1612809661.11 | 1612809661.11
 CHAN_END     | 2021-02-08 18:41:08.90886+00  | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 HANGUP       | 2021-02-08 18:41:08.90886+00  | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
 LINKEDID_END | 2021-02-08 18:41:08.90886+00  | PJSIP/9jqihz0h-00000007                                               | 1612809662.17 | 1612809661.11
'''
    )
    def test_given_group_call_then_destination_user_uuid_should_be_answered_callee(
        self,
    ):
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
            MockUser(USER_2_UUID, USERS_TENANT, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='uzyebgp2',
                users=[{'uuid': USER_1_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            ),
            MockLine(
                id=2,
                name='9jqihz0h',
                users=[{'uuid': USER_2_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '102', 'context': 'default'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='default', tenant_uuid=USERS_TENANT)
        )

        self._assert_last_call_log_matches(
            '1612809661.11',
            has_properties(
                date=datetime.fromisoformat('2021-02-08 18:41:01.659557+00:00'),
                date_answer=datetime.fromisoformat('2021-02-08 18:41:07.315137+00:00'),
                date_end=datetime.fromisoformat('2021-02-08 18:41:08.892839+00:00'),
                source_line_identity='pjsip/d6jtulhp',
                destination_line_identity='pjsip/9jqihz0h',
                destination_user_uuid=USER_2_UUID,
            ),
        )

    @raw_cels(
        '''\
  eventtype   |           eventtime           |        channame         |   uniqueid    |   linkedid
--------------+-------------------------------+-------------------------+---------------+---------------
 CHAN_START   | 2021-02-10 15:39:11.425631+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 ANSWER       | 2021-02-10 15:39:11.801189+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 CHAN_START   | 2021-02-10 15:39:12.944278+00 | PJSIP/w6hpvj79-00000034 | 1612971552.60 | 1612971551.59
 CHAN_START   | 2021-02-10 15:39:12.946258+00 | PJSIP/o7r761lt-00000035 | 1612971552.61 | 1612971551.59
 ANSWER       | 2021-02-10 15:39:14.086632+00 | PJSIP/o7r761lt-00000035 | 1612971552.61 | 1612971551.59
 CHAN_END     | 2021-02-10 15:39:14.090523+00 | PJSIP/w6hpvj79-00000034 | 1612971552.60 | 1612971551.59
 HANGUP       | 2021-02-10 15:39:14.090523+00 | PJSIP/w6hpvj79-00000034 | 1612971552.60 | 1612971551.59
 BRIDGE_ENTER | 2021-02-10 15:39:14.413385+00 | PJSIP/o7r761lt-00000035 | 1612971552.61 | 1612971551.59
 BRIDGE_ENTER | 2021-02-10 15:39:14.413848+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 BRIDGE_EXIT  | 2021-02-10 15:39:15.640067+00 | PJSIP/o7r761lt-00000035 | 1612971552.61 | 1612971551.59
 BRIDGE_EXIT  | 2021-02-10 15:39:15.640637+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 CHAN_END     | 2021-02-10 15:39:15.6414+00   | PJSIP/o7r761lt-00000035 | 1612971552.61 | 1612971551.59
 HANGUP       | 2021-02-10 15:39:15.6414+00   | PJSIP/o7r761lt-00000035 | 1612971552.61 | 1612971551.59
 CHAN_END     | 2021-02-10 15:39:15.641666+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 HANGUP       | 2021-02-10 15:39:15.641666+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 LINKEDID_END | 2021-02-10 15:39:15.641666+00 | PJSIP/svlhxtj3-00000033 | 1612971551.59 | 1612971551.59
 '''
    )
    def test_given_queue_call_then_destination_user_uuid_should_be_answered_callee(
        self,
    ):
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
            MockUser(USER_2_UUID, USERS_TENANT, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='w6hpvj79',
                users=[{'uuid': USER_1_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            ),
            MockLine(
                id=2,
                name='o7r761lt',
                users=[{'uuid': USER_2_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '102', 'context': 'default'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='default', tenant_uuid=USERS_TENANT)
        )

        self._assert_last_call_log_matches(
            '1612971551.59',
            has_properties(
                date=datetime.fromisoformat('2021-02-10 15:39:11.425631+00:00'),
                date_answer=datetime.fromisoformat('2021-02-10 15:39:14.413848+00:00'),
                date_end=datetime.fromisoformat('2021-02-10 15:39:15.641666+00:00'),
                source_line_identity='pjsip/svlhxtj3',
                destination_line_identity='pjsip/o7r761lt',
                destination_user_uuid=USER_2_UUID,
            ),
        )

    @raw_cels(
        '''\
   eventtype   |           eventtime           |           channame           |    uniqueid    |    linkedid
--------------+-------------------------------+------------------------------+----------------+----------------
 CHAN_START   | 2021-03-10 15:52:46.207359-05 | SCCP/101-0000000b            | 1615409566.206 | 1615409566.206
 CHAN_START   | 2021-03-10 15:52:46.427365-05 | Local/104@default-0000004f;1 | 1615409566.207 | 1615409566.206
 CHAN_START   | 2021-03-10 15:52:46.427441-05 | Local/104@default-0000004f;2 | 1615409566.208 | 1615409566.206
 CHAN_START   | 2021-03-10 15:52:46.869701-05 | PJSIP/mvkph8he-00000025      | 1615409566.209 | 1615409566.206
 WAZO_USER    | 2021-03-10 15:52:46.873033-05 | PJSIP/mvkph8he-00000025      | 1615409566.209 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:01.501216-05 | Local/104@default-0000004f;1 | 1615409566.207 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:01.501216-05 | Local/104@default-0000004f;1 | 1615409566.207 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:01.503904-05 | Local/104@default-0000004f;2 | 1615409566.208 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:01.503904-05 | Local/104@default-0000004f;2 | 1615409566.208 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:01.506432-05 | PJSIP/mvkph8he-00000025      | 1615409566.209 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:01.506432-05 | PJSIP/mvkph8he-00000025      | 1615409566.209 | 1615409566.206
 CHAN_START   | 2021-03-10 15:53:06.501732-05 | Local/104@default-00000050;1 | 1615409586.210 | 1615409566.206
 CHAN_START   | 2021-03-10 15:53:06.501859-05 | Local/104@default-00000050;2 | 1615409586.211 | 1615409566.206
 CHAN_START   | 2021-03-10 15:53:06.792964-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 WAZO_USER    | 2021-03-10 15:53:06.796245-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 ANSWER       | 2021-03-10 15:53:08.641888-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 ANSWER       | 2021-03-10 15:53:08.642619-05 | Local/104@default-00000050;2 | 1615409586.211 | 1615409566.206
 ANSWER       | 2021-03-10 15:53:08.645208-05 | Local/104@default-00000050;1 | 1615409586.210 | 1615409566.206
 BRIDGE_ENTER | 2021-03-10 15:53:08.651079-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 BRIDGE_ENTER | 2021-03-10 15:53:08.651592-05 | Local/104@default-00000050;2 | 1615409586.211 | 1615409566.206
 ANSWER       | 2021-03-10 15:53:09.258801-05 | SCCP/101-0000000b            | 1615409566.206 | 1615409566.206
 BRIDGE_ENTER | 2021-03-10 15:53:09.260174-05 | Local/104@default-00000050;1 | 1615409586.210 | 1615409566.206
 BRIDGE_ENTER | 2021-03-10 15:53:09.261166-05 | SCCP/101-0000000b            | 1615409566.206 | 1615409566.206
 BRIDGE_EXIT  | 2021-03-10 15:53:09.275335-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 BRIDGE_EXIT  | 2021-03-10 15:53:09.275506-05 | Local/104@default-00000050;1 | 1615409586.210 | 1615409566.206
 BRIDGE_ENTER | 2021-03-10 15:53:09.275531-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:09.276109-05 | Local/104@default-00000050;1 | 1615409586.210 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:09.276109-05 | Local/104@default-00000050;1 | 1615409586.210 | 1615409566.206
 BRIDGE_EXIT  | 2021-03-10 15:53:09.277653-05 | Local/104@default-00000050;2 | 1615409586.211 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:09.277997-05 | Local/104@default-00000050;2 | 1615409586.211 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:09.277997-05 | Local/104@default-00000050;2 | 1615409586.211 | 1615409566.206
 BRIDGE_EXIT  | 2021-03-10 15:53:10.292963-05 | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 BRIDGE_EXIT  | 2021-03-10 15:53:10.294797-05 | SCCP/101-0000000b            | 1615409566.206 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:10.29554-05  | SCCP/101-0000000b            | 1615409566.206 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:10.29554-05  | SCCP/101-0000000b            | 1615409566.206 | 1615409566.206
 CHAN_END     | 2021-03-10 15:53:10.29859-05  | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 HANGUP       | 2021-03-10 15:53:10.29859-05  | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
 LINKEDID_END | 2021-03-10 15:53:10.29859-05  | PJSIP/mvkph8he-00000026      | 1615409586.212 | 1615409566.206
    '''
    )
    def test_group_call_has_no_duplicate_participant(self):
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
            MockUser(USER_2_UUID, USERS_TENANT, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='101',
                users=[{'uuid': USER_1_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '101', 'context': 'default'}],
            ),
            MockLine(
                id=2,
                name='mvkph8he',
                users=[{'uuid': USER_2_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '102', 'context': 'default'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='default', tenant_uuid=USERS_TENANT)
        )

        self._assert_last_call_log_matches(
            '1615409566.206',
            has_properties(
                participants=all_of(
                    has_length(2),
                    has_item(has_properties(user_uuid=USER_2_UUID, answered=True)),
                )
            ),
        )

    @raw_cels(
        '''\
     eventtype     |           eventtime           |                       exten                       |     cid_name     | cid_num |        channame         |    uniqueid     |    linkedid     |                                       extra
-------------------+-------------------------------+---------------------------------------------------+------------------+---------+-------------------------+-----------------+-----------------+------------------------------------------------------------------------------------
 CHAN_START        | 2021-09-20 19:54:34.688108+00 | wazo-meeting-07ae2b47-7da6-4c89-8b7c-283b6f457fc5 | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 |
 WAZO_MEETING_NAME | 2021-09-20 19:54:34.691618+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 | {"extra":"Meeting with Shevek"}
 ANSWER            | 2021-09-20 19:54:34.693609+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 |
 BRIDGE_ENTER      | 2021-09-20 19:54:35.496867+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 | {"bridge_id":"d12017b8-0697-439e-a372-d02130481bce","bridge_technology":"softmix"}
 BRIDGE_EXIT       | 2021-09-20 19:54:38.689367+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 | {"bridge_id":"d12017b8-0697-439e-a372-d02130481bce","bridge_technology":"softmix"}
 HANGUP            | 2021-09-20 19:54:39.075497+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 | {"hangupcause":16,"hangupsource":"PJSIP/9lh0igq4-00000b11","dialstatus":""}
 CHAN_END          | 2021-09-20 19:54:39.075497+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 |
 LINKEDID_END      | 2021-09-20 19:54:39.075497+00 | participant                                       | Shevek | 8032    | PJSIP/9lh0igq4-00000b11 | 1632167674.4076 | 1632167674.4076 |
'''
    )
    def test_meeting_call_has_no_weird_exten(self):
        self._assert_last_call_log_matches(
            '1632167674.4076',
            has_properties(
                destination_exten='',
                requested_exten='',
            ),
        )

    @raw_cels(
        '''\
    eventtype    |           eventtime           |   cid_name   | cid_num | cid_dnid | exten  |   context   |        channame         |     appname     |                  appdata                   |   uniqueid   |   linkedid   |                                       extra
-----------------+-------------------------------+--------------+---------+----------+--------+-------------+-------------------------+-----------------+--------------------------------------------+--------------+--------------+------------------------------------------------------------------------------------
 CHAN_START      | 2021-11-17 11:10:30.972173-05 | Alice WebRTC | 1101    |          | 4001   | inside      | PJSIP/ycetqvtr-00000000 |                 |                                            | 1637165430.0 | 1637165430.0 |
 WAZO_CONFERENCE | 2021-11-17 11:10:31.931269-05 | Alice WebRTC | 1101    | 4001     | s      | conference  | PJSIP/ycetqvtr-00000000 | CELGenUserEvent | WAZO_CONFERENCE,NAME:test                  | 1637165430.0 | 1637165430.0 | {"extra":"NAME: test"}
 ANSWER          | 2021-11-17 11:10:31.934801-05 | Alice WebRTC | 1101    | 4001     | pickup | xivo-pickup | PJSIP/ycetqvtr-00000000 | Answer          |                                            | 1637165430.0 | 1637165430.0 |
 BRIDGE_ENTER    | 2021-11-17 11:10:37.201038-05 | Alice WebRTC | 1101    | 4001     | s      | conference  | PJSIP/ycetqvtr-00000000 | ConfBridge      | wazo-conference-1,,,xivo-default-user-menu | 1637165430.0 | 1637165430.0 | {"bridge_id":"e2b45e4c-10ba-4561-a59a-9ac28efd454d","bridge_technology":"softmix"}
 BRIDGE_EXIT     | 2021-11-17 11:10:38.206207-05 | Alice WebRTC | 1101    | 4001     | s      | conference  | PJSIP/ycetqvtr-00000000 | ConfBridge      | wazo-conference-1,,,xivo-default-user-menu | 1637165430.0 | 1637165430.0 | {"bridge_id":"e2b45e4c-10ba-4561-a59a-9ac28efd454d","bridge_technology":"softmix"}
 HANGUP          | 2021-11-17 11:10:38.615574-05 | Alice WebRTC | 1101    | 4001     | s      | conference  | PJSIP/ycetqvtr-00000000 |                 |                                            | 1637165430.0 | 1637165430.0 | {"hangupcause":16,"hangupsource":"PJSIP/ycetqvtr-00000000","dialstatus":""}
 CHAN_END        | 2021-11-17 11:10:38.615574-05 | Alice WebRTC | 1101    | 4001     | s      | conference  | PJSIP/ycetqvtr-00000000 |                 |                                            | 1637165430.0 | 1637165430.0 |
 LINKEDID_END    | 2021-11-17 11:10:38.615574-05 | Alice WebRTC | 1101    | 4001     | s      | conference  | PJSIP/ycetqvtr-00000000 |                 |                                            | 1637165430.0 | 1637165430.0 |
'''
    )
    def test_conference_has_a_destination_name(self):
        self._assert_last_call_log_matches(
            '1637165430.0',
            has_properties(destination_exten='4001', destination_name='test'),
        )

    @raw_cels(
        '''\
    eventtype     |           eventtime           | cid_name  | cid_num | cid_ani |      exten       |      context      |        channame         |  appname   |                                                        appdata                                                        |   uniqueid    |   linkedid    |                      peer                       |                                                                               extra
------------------+-------------------------------+-----------+---------+---------+------------------+-------------------+-------------------------+------------+-----------------------------------------------------------------------------------------------------------------------+---------------+---------------+-------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------
 CHAN_START       | 2021-10-06 13:53:54.410847-04 | fb user1  | 1801    |         | 1130             | internal          | PJSIP/pa9pkxh5-00000010 |            |                                                                                                                       | 1633542834.28 | 1633542834.28 |                                                 |
 APP_START        | 2021-10-06 13:53:55.140581-04 | fb user1  | 1801    | 1801    | s                | user              | PJSIP/pa9pkxh5-00000010 | Dial       | PJSIP/Y4sSJpnV/sip:mjaasgm4@127.0.0.1:50240;transport=ws,30,HTXb(wazo-pre-dial-hooks^s^1)                             | 1633542834.28 | 1633542834.28 |                                                 |
 CHAN_START       | 2021-10-06 13:53:55.141093-04 | Alice pcm | 1130    |         | s                | internal          | PJSIP/Y4sSJpnV-00000011 |            |                                                                                                                       | 1633542835.29 | 1633542834.28 |                                                 |
 ANSWER           | 2021-10-06 13:53:59.536051-04 | Alice pcm | 1130    | 1130    | s                | internal          | PJSIP/Y4sSJpnV-00000011 | AppDial    | (Outgoing Line)                                                                                                       | 1633542835.29 | 1633542834.28 |                                                 |
 ANSWER           | 2021-10-06 13:53:59.536318-04 | fb user1  | 1801    | 1801    | s                | user              | PJSIP/pa9pkxh5-00000010 | Dial       | PJSIP/Y4sSJpnV/sip:mjaasgm4@127.0.0.1:50240;transport=ws,30,HTXb(wazo-pre-dial-hooks^s^1)                             | 1633542834.28 | 1633542834.28 |                                                 |
 BRIDGE_ENTER     | 2021-10-06 13:53:59.537795-04 | Alice pcm | 1130    | 1130    |                  | internal          | PJSIP/Y4sSJpnV-00000011 | AppDial    | (Outgoing Line)                                                                                                       | 1633542835.29 | 1633542834.28 |                                                 | {"bridge_id":"9389022b-efca-427c-875d-567ec4394358","bridge_technology":"simple_bridge"}
 BRIDGE_ENTER     | 2021-10-06 13:53:59.538102-04 | fb user1  | 1801    | 1801    | s                | user              | PJSIP/pa9pkxh5-00000010 | Dial       | PJSIP/Y4sSJpnV/sip:mjaasgm4@127.0.0.1:50240;transport=ws,30,HTXb(wazo-pre-dial-hooks^s^1)                             | 1633542834.28 | 1633542834.28 | PJSIP/Y4sSJpnV-00000011                         | {"bridge_id":"9389022b-efca-427c-875d-567ec4394358","bridge_technology":"simple_bridge"}
 BRIDGE_EXIT      | 2021-10-06 13:55:34.348449-04 | Alice pcm | 1130    | 1130    | adhoc_conference | convert_to_stasis | PJSIP/Y4sSJpnV-00000011 | AppDial    | (Outgoing Line)                                                                                                       | 1633542835.29 | 1633542834.28 |                                                 | {"bridge_id":"9389022b-efca-427c-875d-567ec4394358","bridge_technology":"simple_bridge"}
 BRIDGE_EXIT      | 2021-10-06 13:55:34.348561-04 | fb user1  | 1801    | 1801    | h                | convert_to_stasis | PJSIP/pa9pkxh5-00000010 | Dial       | PJSIP/Y4sSJpnV/sip:mjaasgm4@127.0.0.1:50240;transport=ws,30,HTXb(wazo-pre-dial-hooks^s^1)                             | 1633542834.28 | 1633542834.28 |                                                 | {"bridge_id":"9389022b-efca-427c-875d-567ec4394358","bridge_technology":"simple_bridge"}
 HANGUP           | 2021-10-06 13:55:34.350263-04 | fb user1  | 1801    | 1801    | h                | convert_to_stasis | PJSIP/pa9pkxh5-00000010 |            |                                                                                                                       | 1633542834.28 | 1633542834.28 |                                                 | {"hangupcause":16,"hangupsource":"","dialstatus":"ANSWER"}
 CHAN_END         | 2021-10-06 13:55:34.350263-04 | fb user1  | 1801    | 1801    | h                | convert_to_stasis | PJSIP/pa9pkxh5-00000010 |            |                                                                                                                       | 1633542834.28 | 1633542834.28 |                                                 |
 BRIDGE_ENTER     | 2021-10-06 13:55:34.639291-04 | Alice pcm | 1130    | 1130    | adhoc_conference | convert_to_stasis | PJSIP/Y4sSJpnV-00000011 | Stasis     | adhoc_conference,abc9c96e-2a96-43b6-9784-bb3e70c587e5                                                                 | 1633542835.29 | 1633542834.28 | PJSIP/pa9pkxh5-00000012,PJSIP/auc6927d-00000013 | {"bridge_id":"abc9c96e-2a96-43b6-9784-bb3e70c587e5","bridge_technology":"simple_bridge"}
 BRIDGE_EXIT      | 2021-10-06 13:55:58.619722-04 | fb user1  | 1801    | 1801    | adhoc_conference | convert_to_stasis | PJSIP/pa9pkxh5-00000012 | Stasis     | adhoc_conference,abc9c96e-2a96-43b6-9784-bb3e70c587e5                                                                 | 1633542905.30 | 1633542834.28 | PJSIP/Y4sSJpnV-00000011,PJSIP/auc6927d-00000013 | {"bridge_id":"abc9c96e-2a96-43b6-9784-bb3e70c587e5","bridge_technology":"softmix"}
 HANGUP           | 2021-10-06 13:55:58.622227-04 | fb user1  | 1801    | 1801    | adhoc_conference | convert_to_stasis | PJSIP/pa9pkxh5-00000012 |            |                                                                                                                       | 1633542905.30 | 1633542834.28 |                                                 | {"hangupcause":16,"hangupsource":"PJSIP/pa9pkxh5-00000012","dialstatus":"ANSWER"}
 CHAN_END         | 2021-10-06 13:55:58.622227-04 | fb user1  | 1801    | 1801    | adhoc_conference | convert_to_stasis | PJSIP/pa9pkxh5-00000012 |            |                                                                                                                       | 1633542905.30 | 1633542834.28 |                                                 |
 BRIDGE_EXIT      | 2021-10-06 13:55:58.692085-04 | Alice pcm | 1130    | 1130    | adhoc_conference | convert_to_stasis | PJSIP/Y4sSJpnV-00000011 | Stasis     | adhoc_conference,abc9c96e-2a96-43b6-9784-bb3e70c587e5                                                                 | 1633542835.29 | 1633542834.28 | PJSIP/auc6927d-00000013                         | {"bridge_id":"abc9c96e-2a96-43b6-9784-bb3e70c587e5","bridge_technology":"simple_bridge"}
 HANGUP           | 2021-10-06 13:55:58.692876-04 | Alice pcm | 1130    | 1130    | adhoc_conference | convert_to_stasis | PJSIP/Y4sSJpnV-00000011 | AppDial    | (Outgoing Line)                                                                                                       | 1633542835.29 | 1633542834.28 |                                                 | {"hangupcause":16,"hangupsource":"","dialstatus":""}
 CHAN_END         | 2021-10-06 13:55:58.692876-04 | Alice pcm | 1130    | 1130    | adhoc_conference | convert_to_stasis | PJSIP/Y4sSJpnV-00000011 | AppDial    | (Outgoing Line)                                                                                                       | 1633542835.29 | 1633542834.28 |                                                 |
 BRIDGE_EXIT      | 2021-10-06 13:55:58.718222-04 | fb user2  | 1802    | 1802    | adhoc_conference | convert_to_stasis | PJSIP/auc6927d-00000013 | Stasis     | adhoc_conference,abc9c96e-2a96-43b6-9784-bb3e70c587e5                                                                 | 1633542906.31 | 1633542834.28 |                                                 | {"bridge_id":"abc9c96e-2a96-43b6-9784-bb3e70c587e5","bridge_technology":"simple_bridge"}
 HANGUP           | 2021-10-06 13:55:58.718839-04 | fb user2  | 1802    | 1802    | adhoc_conference | convert_to_stasis | PJSIP/auc6927d-00000013 | AppDial    | (Outgoing Line)                                                                                                       | 1633542906.31 | 1633542834.28 |                                                 | {"hangupcause":16,"hangupsource":"","dialstatus":""}
 CHAN_END         | 2021-10-06 13:55:58.718839-04 | fb user2  | 1802    | 1802    | adhoc_conference | convert_to_stasis | PJSIP/auc6927d-00000013 | AppDial    | (Outgoing Line)                                                                                                       | 1633542906.31 | 1633542834.28 |                                                 |
 LINKEDID_END     | 2021-10-06 13:55:58.718839-04 | fb user2  | 1802    | 1802    | adhoc_conference | convert_to_stasis | PJSIP/auc6927d-00000013 | AppDial    | (Outgoing Line)                                                                                                       | 1633542906.31 | 1633542834.28 |                                                 |
'''
    )
    def test_adhoc_conference(self):
        self.confd.set_users(
            MockUser(USER_1_UUID, USERS_TENANT, line_ids=[1]),
            MockUser(USER_2_UUID, USERS_TENANT, line_ids=[2]),
            MockUser(USER_3_UUID, USERS_TENANT, line_ids=[3]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='pa9pkxh5',
                users=[{'uuid': USER_1_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '1801', 'context': 'internal'}],
            ),
            MockLine(
                id=2,
                name='auc6927d',
                users=[{'uuid': USER_2_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '1802', 'context': 'internal'}],
            ),
            MockLine(
                id=3,
                name='Y4sSJpnV',
                users=[{'uuid': USER_3_UUID}],
                tenant_uuid=USERS_TENANT,
                extensions=[{'exten': '1130', 'context': 'internal'}],
            ),
        )
        self.confd.set_contexts(
            MockContext(id=1, name='internal', tenant_uuid=USERS_TENANT)
        )

        self._assert_last_call_log_matches(
            '1633542834.28',
            has_properties(
                id=not_none(),
                participants=contains_inanyorder(
                    has_properties(
                        uuid=not_none(), user_uuid=USER_1_UUID, role='source'
                    ),
                    any_of(
                        # One of the participant is ignored
                        has_properties(
                            uuid=not_none(), user_uuid=USER_2_UUID, role='destination'
                        ),
                        has_properties(
                            uuid=not_none(), user_uuid=USER_3_UUID, role='destination'
                        ),
                    ),
                ),
            ),
        )

    @raw_cels(
        '''\
        linkedid      | uniqueid      | eventtime                | eventtype                 | channame                | cid_name   | cid_num   | extra
        --------------+---------------+--------------------------+---------------------------+-------------------------+------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:00.0+00 | CHAN_START                | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      |
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:01.0+00 | XIVO_INCALL               | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:02.0+00 | WAZO_CALL_LOG_DESTINATION | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"type: user,uuid: ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,name: A Mctest"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:03.0+00 | APP_START                 | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      |
        1674248467.40 | 1674248468.41 | 2023-01-20 00:00:04.0+00 | CHAN_START                | PJSIP/9EYlfTvB-00000029 | A Mctest   | 8001      |
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:05.0+00 | XIVO_USER_FWD             | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"NUM:8001,CONTEXT:default-key-4wfgx-internal,NAME:A Mctest"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:06.0+00 | WAZO_USER_MISSED_CALL     | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"wazo_tenant_uuid: 54eb71f8-1f4b-4ae4-8730-638062fbe521,source_user_uuid: ,destination_user_uuid: ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,destination_exten: 8001,source_name: test-UC-1,destination_name: A Mctest"}
        1674248467.40 | 1674248468.41 | 2023-01-20 00:00:07.0+00 | HANGUP                    | PJSIP/9EYlfTvB-00000029 | A Mctest   | 8001      | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        1674248467.40 | 1674248468.41 | 2023-01-20 00:00:08.0+00 | CHAN_END                  | PJSIP/9EYlfTvB-00000029 | A Mctest   | 8001      |
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:09.0+00 | WAZO_CALL_LOG_DESTINATION | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"type: user,uuid: 31be0853-dde6-48cd-986d-85bc708754a1,name: B McTest"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:10.0+00 | APP_START                 | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      |
        1674248467.40 | 1674248473.42 | 2023-01-20 00:00:11.0+00 | CHAN_START                | PJSIP/rNXlGVeY-0000002a | B McTest   | 8002      |
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:12.0+00 | XIVO_USER_FWD             | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"NUM:8002,CONTEXT:default-key-4wfgx-internal,NAME:B McTest"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:13.0+00 | WAZO_USER_MISSED_CALL     | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"extra":"wazo_tenant_uuid: 54eb71f8-1f4b-4ae4-8730-638062fbe521,source_user_uuid: ,destination_user_uuid: 31be0853-dde6-48cd-986d-85bc708754a1,destination_exten: 8001,source_name: test-UC-1,destination_name: B McTest"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:14.0+00 | ANSWER                    | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      |
        1674248467.40 | 1674248473.42 | 2023-01-20 00:00:15.0+00 | HANGUP                    | PJSIP/rNXlGVeY-0000002a | B McTest   | 8002      | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        1674248467.40 | 1674248473.42 | 2023-01-20 00:00:16.0+00 | CHAN_END                  | PJSIP/rNXlGVeY-0000002a | B McTest   | 8002      |
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:17.0+00 | HANGUP                    | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      | {"hangupcause":16,"hangupsource":"dialplan/builtin","dialstatus":"NOANSWER"}
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:18.0+00 | CHAN_END                  | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      |
        1674248467.40 | 1674248467.40 | 2023-01-20 00:00:19.0+00 | LINKEDID_END              | PJSIP/rgcZLNGE-00000028 | test-UC-1  | 8000      |
        '''
    )
    def test_user_missed_call_fallback_missed(self):
        # user A missed, fallback to user B, missed too.
        # Both were called, call log should include both as participants.
        user_a_uuid = "ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6"
        user_b_uuid = "31be0853-dde6-48cd-986d-85bc708754a1"
        user_b_name = "B McTest"
        tenant = "54eb71f8-1f4b-4ae4-8730-638062fbe521"
        self.confd.set_users(
            MockUser(user_a_uuid, tenant, line_ids=[1]),
            MockUser(user_b_uuid, tenant, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='9EYlfTvB',
                users=[{'uuid': user_a_uuid}],
                tenant_uuid=tenant,
                extensions=[{'exten': '8001', 'context': 'internal'}],
            ),
            MockLine(
                id=2,
                name='rNXlGVeY',
                users=[{'uuid': user_b_uuid}],
                tenant_uuid=tenant,
                extensions=[{'exten': '8002', 'context': 'internal'}],
            ),
        )
        self.confd.set_contexts(MockContext(id=1, name='internal', tenant_uuid=tenant))

        self._assert_last_call_log_matches(
            '1674248467.40',
            has_properties(
                id=not_none(),
                participants=contains_inanyorder(
                    has_properties(
                        uuid=not_none(),
                        user_uuid=user_a_uuid,
                        role='destination',
                        answered=False,
                    ),
                    has_properties(
                        uuid=not_none(),
                        user_uuid=user_b_uuid,
                        role='destination',
                        answered=False,
                    ),
                ),
                destination_user_uuid=user_b_uuid,
                destination_name=user_b_name,
                destination_details=contains_inanyorder(
                    has_properties(
                        uuid=not_none(),
                        destination_details_key="type",
                        destination_details_value="user",
                    ),
                    has_properties(
                        uuid=not_none(),
                        destination_details_key="user_uuid",
                        destination_details_value=user_b_uuid,
                    ),
                    has_properties(
                        uuid=not_none(),
                        destination_details_key="user_name",
                        destination_details_value=user_b_name,
                    ),
                ),
            ),
        )

    @raw_cels(
        '''\
        linkedid      | uniqueid      | eventtime                | eventtype                 | channame                | cid_name   | cid_num   | extra
        --------------+---------------+--------------------------+---------------------------+-------------------------+------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:00.0+00 | CHAN_START                | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      |
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:01.0+00 | XIVO_INCALL               | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"extra":"54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:02.0+00 | WAZO_CALL_LOG_DESTINATION | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"extra":"type: user,uuid: ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,name: A Mctest"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:03.0+00 | APP_START                 | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      |
        1674485777.43 | 1674485778.44 | 2023-01-23 00:00:04.0+00 | CHAN_START                | PJSIP/9EYlfTvB-0000002c | A Mctest   | 8001      |
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:05.0+00 | XIVO_USER_FWD             | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"extra":"NUM:8001,CONTEXT:default-key-4wfgx-internal,NAME:A Mctest"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:06.0+00 | WAZO_USER_MISSED_CALL     | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"extra":"wazo_tenant_uuid: 54eb71f8-1f4b-4ae4-8730-638062fbe521,source_user_uuid: ,destination_user_uuid: ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,destination_exten: 8001,source_name: test-UC-1,destination_name: A Mctest"}
        1674485777.43 | 1674485778.44 | 2023-01-23 00:00:07.0+00 | CHAN_END                  | PJSIP/9EYlfTvB-0000002c | A Mctest   | 8001      |
        1674485777.43 | 1674485778.44 | 2023-01-23 00:00:08.0+00 | HANGUP                    | PJSIP/9EYlfTvB-0000002c | A Mctest   | 8001      | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:09.0+00 | WAZO_CALL_LOG_DESTINATION | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"extra":"type: user,uuid: 31be0853-dde6-48cd-986d-85bc708754a1,name: B McTest"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:10.0+00 | APP_START                 | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      |
        1674485777.43 | 1674485783.45 | 2023-01-23 00:00:11.0+00 | CHAN_START                | PJSIP/rNXlGVeY-0000002d | B McTest   | 8002      |
        1674485777.43 | 1674485783.45 | 2023-01-23 00:00:12.0+00 | ANSWER                    | PJSIP/rNXlGVeY-0000002d | B McTest   | 8002      |
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:13.0+00 | ANSWER                    | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      |
        1674485777.43 | 1674485783.45 | 2023-01-23 00:00:14.0+00 | BRIDGE_ENTER              | PJSIP/rNXlGVeY-0000002d | B McTest   | 8002      | {"bridge_id":"4829874c-dcd2-4e4c-bf72-370cb6c54933","bridge_technology":"simple_bridge"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:15.0+00 | BRIDGE_ENTER              | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"bridge_id":"4829874c-dcd2-4e4c-bf72-370cb6c54933","bridge_technology":"simple_bridge"}
        1674485777.43 | 1674485783.45 | 2023-01-23 00:00:16.0+00 | BRIDGE_EXIT               | PJSIP/rNXlGVeY-0000002d | B McTest   | 8002      | {"bridge_id":"4829874c-dcd2-4e4c-bf72-370cb6c54933","bridge_technology":"simple_bridge"}
        1674485777.43 | 1674485783.45 | 2023-01-23 00:00:17.0+00 | HANGUP                    | PJSIP/rNXlGVeY-0000002d | B McTest   | 8002      | {"hangupcause":16,"hangupsource":"PJSIP/rNXlGVeY-0000002d","dialstatus":""}
        1674485777.43 | 1674485783.45 | 2023-01-23 00:00:18.0+00 | CHAN_END                  | PJSIP/rNXlGVeY-0000002d | B McTest   | 8002      |
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:19.0+00 | BRIDGE_EXIT               | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"bridge_id":"4829874c-dcd2-4e4c-bf72-370cb6c54933","bridge_technology":"simple_bridge"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:20.0+00 | CHAN_END                  | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      |
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:21.0+00 | HANGUP                    | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      | {"hangupcause":16,"hangupsource":"PJSIP/rNXlGVeY-0000002d","dialstatus":"ANSWER"}
        1674485777.43 | 1674485777.43 | 2023-01-23 00:00:22.0+00 | LINKEDID_END              | PJSIP/rgcZLNGE-0000002b | test-UC-1  | 8000      |
        '''
    )
    def test_user_missed_call_fallback_answered(self):
        # user A missed, fallback to user B, answered.
        # Both were called, call log should include both as participants.
        user_a_uuid = "ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6"
        user_a_name = "A Mctest"
        user_b_uuid = "31be0853-dde6-48cd-986d-85bc708754a1"
        user_b_name = "B McTest"
        tenant = "54eb71f8-1f4b-4ae4-8730-638062fbe521"
        self.confd.set_users(
            MockUser(user_a_uuid, tenant, line_ids=[1]),
            MockUser(user_b_uuid, tenant, line_ids=[2]),
        )
        self.confd.set_lines(
            MockLine(
                id=1,
                name='9EYlfTvB',
                users=[{'uuid': user_a_uuid}],
                tenant_uuid=tenant,
                extensions=[{'exten': '8001', 'context': 'internal'}],
            ),
            MockLine(
                id=2,
                name='rNXlGVeY',
                users=[{'uuid': user_b_uuid}],
                tenant_uuid=tenant,
                extensions=[{'exten': '8002', 'context': 'internal'}],
            ),
        )
        self.confd.set_contexts(MockContext(id=1, name='internal', tenant_uuid=tenant))

        self._assert_last_call_log_matches(
            '1674485777.43',
            has_properties(
                id=not_none(),
                participants=contains_inanyorder(
                    has_properties(
                        uuid=not_none(),
                        user_uuid=user_a_uuid,
                        role='destination',
                        answered=False,
                    ),
                    has_properties(
                        uuid=not_none(),
                        user_uuid=user_b_uuid,
                        role='destination',
                        answered=True,
                    ),
                ),
                destination_user_uuid=user_b_uuid,
                destination_name=user_b_name,
                destination_details=contains_inanyorder(
                    has_properties(
                        uuid=not_none(),
                        destination_details_key="type",
                        destination_details_value="user",
                    ),
                    has_properties(
                        uuid=not_none(),
                        destination_details_key="user_uuid",
                        destination_details_value=user_b_uuid,
                    ),
                    has_properties(
                        uuid=not_none(),
                        destination_details_key="user_name",
                        destination_details_value=user_b_name,
                    ),
                ),
            ),
        )

# Copyright 2013-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from functools import wraps
from typing import get_type_hints
from unittest import TestCase
from unittest.mock import MagicMock, Mock, create_autospec
from uuid import uuid4

from hamcrest import assert_that, contains_inanyorder, has_properties
from requests import HTTPError

# from xivo_dao.alchemy.cel import CEL
from wazo_confd_client import Client as ConfdClient

from wazo_call_logd.cel_interpretor import default_interpretors, parse_eventtime
from wazo_call_logd.generator import CallLogsGenerator

from .helpers.hamcrest.datetime_close_to import datetime_close_to

logger = logging.getLogger(__name__)


def parse_fields(line: str) -> list[str]:
    return [field.strip() for field in line.split('|')]


def parse_raw_cels(text_table: str) -> list[dict]:
    cels = []
    lines = [
        line
        for line in text_table.strip().split('\n')
        if line and set(line.strip()) != set('+-')
    ]
    logger.debug('parsing %d lines of cel table', len(lines))
    columns = parse_fields(lines.pop(0))
    logger.debug('parsed %d fields in cel table header', len(columns))

    for i, line in enumerate(lines):
        cel = parse_fields(line)
        logger.debug('parsed %d fields in row %d', len(cel), i)
        assert len(cel) == len(columns), (columns, cel)
        cels.append(dict(zip(columns, cel)))
    return cels


@dataclass
class CEL:
    id: int
    uniqueid: str
    linkedid: str
    eventtime: datetime
    amaflags: int = 0
    eventtype: str = ''
    userdeftype: str = ''
    cid_name: str = ''
    cid_num: str = ''
    cid_ani: str = ''
    cid_rdnis: str = ''
    cid_dnid: str = ''
    exten: str = ''
    context: str = ''
    channame: str = ''
    appname: str = ''
    appdata: str = ''
    accountcode: str = ''
    peeraccount: str = ''
    userfield: str = ''
    peer: str = ''
    extra: str = None
    call_log_id: int = None

    def __post_init__(self, **kwargs):
        for field in fields(self):
            current_value = getattr(self, field.name)
            converter = (
                parse_eventtime
                if field.name == 'eventtime'
                else get_type_hints(self.__class__)[field.name]
            )
            if current_value is not None:
                try:
                    setattr(
                        self,
                        field.name,
                        converter(current_value),
                    )
                except Exception:
                    logger.exception(
                        'Error processing field %s of CEL for input %s',
                        field.name,
                        current_value,
                    )
                    raise


def raw_cels(cel_output, row_count=None):
    '''
    this decorator takes the output of a psql query
    and parses it into CEL entries that are loaded into the database
    '''
    cels = parse_raw_cels(cel_output)
    if row_count:
        assert (
            len(cels) == row_count
        ), f'parsed row count ({len(cels)}) different from expected row count ({row_count})'

    rich_cels = [CEL(id=i, **fields) for i, fields in enumerate(cels)]

    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            return func(
                self,
                list(rich_cels),
                *args,
                **kwargs,
            )

        return wrapped_function

    return _decorate


def mock_dict(m: dict) -> MagicMock:
    mock = MagicMock(m)
    mock.__getitem__.side_effect = m.__getitem__
    mock.__delitem__.side_effect = m.__delitem__
    mock.__setitem__.side_effect = m.__setitem__

    return mock


def mock_user(
    uuid: str,
    tenant_uuid: str,
    line_ids: list[str] | None = None,
    mobile: str | None = None,
    userfield: str | None = None,
) -> dict[str, any]:
    return mock_dict(
        {
            'uuid': uuid,
            'tenant_uuid': tenant_uuid,
            'lines': (
                [{'id': line_id, 'extensions': [], 'name': ''} for line_id in line_ids]
                if line_ids
                else []
            ),
            'mobile_phone_number': mobile,
            'userfield': userfield,
        }
    )


def mock_line(
    id: int,
    name: str | None = None,
    protocol: str | None = None,
    users: list[dict] | None = None,
    context: dict | None = None,
    extensions: list[str] | None = None,
    tenant_uuid: str | None = None,
) -> dict:
    return mock_dict(
        {
            'id': id,
            'name': name,
            'protocol': protocol,
            'users': users or [],
            'context': context,
            'extensions': extensions or [],
            'tenant_uuid': tenant_uuid,
        }
    )


def mock_switchboard(uuid: str, name: str | None = None) -> dict:
    return mock_dict({'uuid': uuid, 'name': name})


def mock_context(id: int, name: str, tenant_uuid: str) -> dict[str, int | str]:
    return mock_dict({'id': id, 'name': name, 'tenant_uuid': tenant_uuid})


def mock_confd_client(
    lines: list[dict] = None,
    users: list[dict] = None,
    contexts: list[dict] = None,
) -> ConfdClient:
    confd_client = create_autospec(
        ConfdClient, instance=True, lines=Mock(), users=Mock(), contexts=Mock()
    )

    def list_lines(name=None, **kwargs):
        if lines is None:
            filtered_lines = []
        elif name:
            filtered_lines = [line for line in lines if line['name'] == name]
        else:
            filtered_lines = lines
        return {'items': filtered_lines}

    confd_client.lines.list.side_effect = list_lines

    def get_user(uuid):
        try:
            return next(user for user in users if user['uuid'] == uuid)
        except StopIteration:
            raise HTTPError(response=Mock(status_code=404, request=Mock()))

    confd_client.users.get.side_effect = get_user if users is not None else HTTPError

    def list_contexts(name=None, **kwargs):
        if contexts is None:
            filtered_contexts = []
        elif name:
            filtered_contexts = [
                context for context in contexts if context['name'] == name
            ]
        else:
            filtered_contexts = contexts
        return {'items': filtered_contexts}

    confd_client.contexts.list.side_effect = list_contexts
    return confd_client


class TestCallLogGenerationScenarios(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s: %(name)s:%(lineno)d : %(funcName)s: %(message)s',
        )

    def setUp(self) -> None:
        super().setUp()
        self.confd_client = mock_confd_client()
        self.generator = CallLogsGenerator(
            self.confd_client,
            default_interpretors(),
        )

    @raw_cels(
        '''
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
    def test_incoming_call_has_destination_details_setup_correctly(
        self, cels: list[CEL]
    ):
        tenant_uuid = '006a72c4-eb68-481a-808f-33b28ec109c8'
        user_uuid = 'cb79f29b-f69a-4b93-85c2-49dcce119a9f'
        user_name = 'Harry Potter'
        self.generator.confd = mock_confd_client(
            users=[mock_user(uuid=user_uuid, tenant_uuid=tenant_uuid)]
        )

        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        assert_that(
            call_logs[0],
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
        '''
            eventtime                 |   linkedid    |   uniqueid    |  eventtype   | cid_name  | cid_num | exten |        channame         |             peer             |                                                    extra
        ------------------------------+---------------+---------------+--------------+-----------+---------+-------+-------------------------+------------------------------+-------------------------------------------------------------------------------------------------------------
        2023-09-06 18:07:22.626751+00 | 1694023642.7  | 1694023642.7  | CHAN_START   | Caller    | 8001    | 91001 | PJSIP/9EYlfTvB-00000003 |                              |
        2023-09-06 18:07:22.766486+00 | 1694023642.7  | 1694023642.7  | XIVO_INCALL  | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              | {"extra":"54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        2023-09-06 18:07:22.800934+00 | 1694023642.7  | 1694023642.7  | ANSWER       | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              |
        2023-09-06 18:07:24.634089+00 | 1694023642.7  | 1694023642.7  | BRIDGE_ENTER | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 | Announcer/ARI_MOH-00000002;2 | {"bridge_id":"switchboard-34aba842-e9d3-49c7-ba36-45cdf78bb1fb-queue","bridge_technology":"holding_bridge"}
        2023-09-06 18:07:27.249116+00 | 1694023642.7  | 1694023647.10 | CHAN_START   | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000004 |                              |
        2023-09-06 18:07:27.279066+00 | 1694023642.7  | 1694023642.7  | BRIDGE_EXIT  | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 | Announcer/ARI_MOH-00000002;2 | {"bridge_id":"switchboard-34aba842-e9d3-49c7-ba36-45cdf78bb1fb-queue","bridge_technology":"holding_bridge"}
        2023-09-06 18:07:28.621623+00 | 1694023642.7  | 1694023647.10 | ANSWER       | Caller    | 8001    | s     | PJSIP/KvXYRheV-00000004 |                              |
        2023-09-06 18:07:28.748438+00 | 1694023642.7  | 1694023642.7  | BRIDGE_ENTER | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              | {"bridge_id":"2513e8a5-184f-4399-a592-a8c629b2aaed","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:28.77778+00  | 1694023642.7  | 1694023647.10 | BRIDGE_ENTER | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000004 | PJSIP/9EYlfTvB-00000003      | {"bridge_id":"2513e8a5-184f-4399-a592-a8c629b2aaed","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:33.990541+00 | 1694023642.7  | 1694023642.7  | BRIDGE_EXIT  | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 | PJSIP/KvXYRheV-00000004      | {"bridge_id":"2513e8a5-184f-4399-a592-a8c629b2aaed","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:33.991055+00 | 1694023642.7  | 1694023642.7  | BRIDGE_ENTER | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 | Announcer/ARI_MOH-00000003;2 | {"bridge_id":"switchboard-34aba842-e9d3-49c7-ba36-45cdf78bb1fb-hold","bridge_technology":"holding_bridge"}
        2023-09-06 18:07:34.01182+00  | 1694023642.7  | 1694023647.10 | BRIDGE_EXIT  | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000004 |                              | {"bridge_id":"2513e8a5-184f-4399-a592-a8c629b2aaed","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:34.01327+00  | 1694023642.7  | 1694023647.10 | HANGUP       | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000004 |                              | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        2023-09-06 18:07:34.01327+00  | 1694023642.7  | 1694023647.10 | CHAN_END     | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000004 |                              |
        2023-09-06 18:07:39.145551+00 | 1694023659.13 | 1694023659.13 | CHAN_START   | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000005 |                              |
        2023-09-06 18:07:39.181324+00 | 1694023642.7  | 1694023642.7  | BRIDGE_EXIT  | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 | Announcer/ARI_MOH-00000003;2 | {"bridge_id":"switchboard-34aba842-e9d3-49c7-ba36-45cdf78bb1fb-hold","bridge_technology":"holding_bridge"}
        2023-09-06 18:07:40.514803+00 | 1694023659.13 | 1694023659.13 | ANSWER       | Caller    | 8001    | s     | PJSIP/KvXYRheV-00000005 |                              |
        2023-09-06 18:07:40.631553+00 | 1694023642.7  | 1694023642.7  | BRIDGE_ENTER | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              | {"bridge_id":"d855ac7e-790b-46bc-9b7f-9634ea7081e1","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:40.649264+00 | 1694023659.13 | 1694023659.13 | LINKEDID_END | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000005 |                              |
        2023-09-06 18:07:40.649284+00 | 1694023642.7  | 1694023659.13 | BRIDGE_ENTER | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000005 | PJSIP/9EYlfTvB-00000003      | {"bridge_id":"d855ac7e-790b-46bc-9b7f-9634ea7081e1","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:45.901316+00 | 1694023642.7  | 1694023659.13 | BRIDGE_EXIT  | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000005 | PJSIP/9EYlfTvB-00000003      | {"bridge_id":"d855ac7e-790b-46bc-9b7f-9634ea7081e1","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:45.903738+00 | 1694023642.7  | 1694023659.13 | HANGUP       | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000005 |                              | {"hangupcause":16,"hangupsource":"PJSIP/KvXYRheV-00000005","dialstatus":""}
        2023-09-06 18:07:45.903738+00 | 1694023642.7  | 1694023659.13 | CHAN_END     | Operator  | 8000    | s     | PJSIP/KvXYRheV-00000005 |                              |
        2023-09-06 18:07:45.981824+00 | 1694023642.7  | 1694023642.7  | BRIDGE_EXIT  | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              | {"bridge_id":"d855ac7e-790b-46bc-9b7f-9634ea7081e1","bridge_technology":"simple_bridge"}
        2023-09-06 18:07:45.983346+00 | 1694023642.7  | 1694023642.7  | HANGUP       | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              | {"hangupcause":16,"hangupsource":"PJSIP/KvXYRheV-00000005","dialstatus":""}
        2023-09-06 18:07:45.983346+00 | 1694023642.7  | 1694023642.7  | CHAN_END     | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              |
        2023-09-06 18:07:45.983346+00 | 1694023642.7  | 1694023642.7  | LINKEDID_END | Caller    | 8001    | s     | PJSIP/9EYlfTvB-00000003 |                              |
        '''
    )
    def test_switchboard_call_answered_then_put_in_shared_queue_then_answered(
        self, cels
    ):
        operator_uuid = str(uuid4())
        tenant_uuid = '54eb71f8-1f4b-4ae4-8730-638062fbe521'
        operator_user = mock_user(
            uuid=operator_uuid, tenant_uuid=tenant_uuid, line_ids=[1]
        )
        self.generator.confd = mock_confd_client(
            users=[operator_user],
            lines=[
                mock_line(
                    id=1,
                    tenant_uuid=tenant_uuid,
                    users=[operator_user],
                    protocol='sip',
                    name='KvXYRheV',
                    context='default',
                )
            ],
            contexts=[mock_context(id=1, name='default', tenant_uuid=tenant_uuid)],
        )

        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        assert_that(
            call_logs[0],
            has_properties(
                tenant_uuid=tenant_uuid,
                participants=contains_inanyorder(
                    has_properties(
                        user_uuid=operator_uuid,
                        role='destination',
                        answered=True,
                    ),
                ),
                destination_name='Operator',
                direction='inbound',
                requested_exten='91001',
                date_answer=datetime_close_to(
                    '2023-09-06 18:07:28+0000', delta=timedelta(seconds=1)
                ),
            ),
        )

    @raw_cels(
        '''
       linkedid   |   uniqueid    |        eventtype         | cid_name  |  cid_num  |                exten                 |            context            |                               channame                                |                                                    extra                                                    |           eventtime
    --------------+---------------+--------------------------+-----------+-----------+--------------------------------------+-------------------------------+-----------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------+-------------------------------
    1698084944.29 | 1698084944.29 | CHAN_START               |           |           | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 |                                                                                                             | 2023-10-23 18:15:44.063215+00
    1698084944.29 | 1698084944.30 | CHAN_START               |           |           | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 |                                                                                                             | 2023-10-23 18:15:44.063253+00
    1698084944.29 | 1698084944.30 | WAZO_ORIGINATE_ALL_LINES | +12345678 | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 | {"extra":"user_uuid:81ea4378-1647-4eae-ad83-26178bdc2890,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"} | 2023-10-23 18:15:44.065081+00
    1698084944.29 | 1698084944.30 | APP_START                | +12345678 | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 |                                                                                                             | 2023-10-23 18:15:44.201567+00
    1698084944.29 | 1698084944.31 | CHAN_START               | caller    | 8000      | s                                    | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               |                                                                                                             | 2023-10-23 18:15:44.202871+00
    1698084944.29 | 1698084944.31 | ANSWER                   | caller    | 8000      | 81ea4378-1647-4eae-ad83-26178bdc2890 | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               |                                                                                                             | 2023-10-23 18:15:47.584355+00
    1698084944.29 | 1698084944.30 | ANSWER                   | +12345678 | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 |                                                                                                             | 2023-10-23 18:15:47.584528+00
    1698084944.29 | 1698084944.29 | ANSWER                   | caller    | 8000      | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 |                                                                                                             | 2023-10-23 18:15:47.584696+00
    1698084944.29 | 1698084944.31 | BRIDGE_ENTER             | caller    | 8000      |                                      | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               | {"bridge_id":"02bf1433-a6e4-42b3-8ab7-8ebcd29fc032","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:47.590051+00
    1698084944.29 | 1698084944.30 | BRIDGE_ENTER             | +12345678 | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 | {"bridge_id":"02bf1433-a6e4-42b3-8ab7-8ebcd29fc032","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:47.590842+00
    1698084944.29 | 1698084944.29 | XIVO_OUTCALL             | caller    | 8000      | dial                                 | outcall                       | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 | {"extra":""}                                                                                                | 2023-10-23 18:15:47.784045+00
    1698084944.29 | 1698084944.29 | APP_START                | caller    | 8000      | dial                                 | outcall                       | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 |                                                                                                             | 2023-10-23 18:15:47.815447+00
    1698084944.29 | 1698084947.32 | CHAN_START               | wazo      |           | s                                    | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               |                                                                                                             | 2023-10-23 18:15:47.817025+00
    1698084944.29 | 1698084947.32 | ANSWER                   |           | +12345678 | dial                                 | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               |                                                                                                             | 2023-10-23 18:15:50.531362+00
    1698084944.29 | 1698084947.32 | BRIDGE_ENTER             |           | +12345678 |                                      | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               | {"bridge_id":"c6ebeccf-b34b-43e0-aa1c-d956dae4f13c","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:50.532461+00
    1698084944.29 | 1698084944.29 | BRIDGE_ENTER             | caller    | 8000      | dial                                 | outcall                       | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 | {"bridge_id":"c6ebeccf-b34b-43e0-aa1c-d956dae4f13c","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:50.532966+00
    1698084944.29 | 1698084947.32 | BRIDGE_EXIT              |           | +12345678 |                                      | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               | {"bridge_id":"c6ebeccf-b34b-43e0-aa1c-d956dae4f13c","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:50.590144+00
    1698084944.29 | 1698084944.30 | BRIDGE_EXIT              |           | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 | {"bridge_id":"02bf1433-a6e4-42b3-8ab7-8ebcd29fc032","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:50.590285+00
    1698084944.29 | 1698084947.32 | BRIDGE_ENTER             |           | +12345678 |                                      | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               | {"bridge_id":"02bf1433-a6e4-42b3-8ab7-8ebcd29fc032","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:50.590295+00
    1698084944.29 | 1698084944.29 | BRIDGE_EXIT              | caller    | 8000      | dial                                 | outcall                       | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 | {"bridge_id":"c6ebeccf-b34b-43e0-aa1c-d956dae4f13c","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:50.590523+00
    1698084944.29 | 1698084944.29 | CHAN_END                 | caller    | 8000      | dial                                 | outcall                       | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 |                                                                                                             | 2023-10-23 18:15:50.590719+00
    1698084944.29 | 1698084944.29 | HANGUP                   | caller    | 8000      | dial                                 | outcall                       | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;1 | {"hangupcause":16,"hangupsource":"","dialstatus":"ANSWER"}                                                  | 2023-10-23 18:15:50.590719+00
    1698084944.29 | 1698084944.30 | CHAN_END                 |           | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 |                                                                                                             | 2023-10-23 18:15:50.592553+00
    1698084944.29 | 1698084944.30 | HANGUP                   |           | +12345678 | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-00000008;2 | {"hangupcause":16,"hangupsource":"","dialstatus":"ANSWER"}                                                  | 2023-10-23 18:15:50.592553+00
    1698084944.29 | 1698084947.32 | BRIDGE_EXIT              |           | +12345678 |                                      | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               | {"bridge_id":"02bf1433-a6e4-42b3-8ab7-8ebcd29fc032","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:55.609126+00
    1698084944.29 | 1698084944.31 | BRIDGE_EXIT              | caller    | 8000      |                                      | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               | {"bridge_id":"02bf1433-a6e4-42b3-8ab7-8ebcd29fc032","bridge_technology":"simple_bridge"}                    | 2023-10-23 18:15:55.612634+00
    1698084944.29 | 1698084947.32 | HANGUP                   |           | +12345678 |                                      | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               | {"hangupcause":16,"hangupsource":"PJSIP/rmbmgma2-0000000e","dialstatus":""}                                 | 2023-10-23 18:15:55.614277+00
    1698084944.29 | 1698084947.32 | CHAN_END                 |           | +12345678 |                                      | default-key-4wfgx-from-extern | PJSIP/rmbmgma2-0000000e                                               |                                                                                                             | 2023-10-23 18:15:55.614277+00
    1698084944.29 | 1698084944.31 | CHAN_END                 | caller    | 8000      |                                      | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               |                                                                                                             | 2023-10-23 18:15:55.615004+00
    1698084944.29 | 1698084944.31 | HANGUP                   | caller    | 8000      |                                      | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               | {"hangupcause":16,"hangupsource":"PJSIP/rmbmgma2-0000000e","dialstatus":""}                                 | 2023-10-23 18:15:55.615004+00
    1698084944.29 | 1698084944.31 | LINKEDID_END             | caller    | 8000      |                                      | default-key-4wfgx-internal    | PJSIP/KvXYRheV-0000000d                                               |                                                                                                             | 2023-10-23 18:15:55.615004+00
    '''
    )
    def test_outcall_from_api_all_lines(self, cels):
        """
        an outgoing (trunk) call is triggered through the API,
        the calling user picks up with an SIP line,
        the outgoing call connects and is answered by the callee,
        the calling party hangs up and the call terminates
        """
        user_uuid = '81ea4378-1647-4eae-ad83-26178bdc2890'
        tenant_uuid = '54eb71f8-1f4b-4ae4-8730-638062fbe521'

        caller_user = mock_user(uuid=user_uuid, tenant_uuid=tenant_uuid, line_ids=[1])
        self.generator.confd = mock_confd_client(
            users=[caller_user],
            lines=[
                mock_line(
                    id=1,
                    tenant_uuid=tenant_uuid,
                    users=[caller_user],
                    protocol='sip',
                    name='KvXYRheV',
                    context='default',
                )
            ],
            contexts=[mock_context(id=1, name='default', tenant_uuid=tenant_uuid)],
        )

        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        assert_that(
            call_logs[0],
            has_properties(
                tenant_uuid=tenant_uuid,
                participants=contains_inanyorder(
                    has_properties(
                        user_uuid=user_uuid,
                        role='source',
                    ),
                ),
                direction='outbound',
            ),
        )

    @raw_cels(
        '''
                eventtype         |    uniqueid    |    linkedid    |           eventtime           |   cid_name    |               cid_num                |                exten                 |            context            |                               channame                                |     appname     |                                                                         appdata                                                                         |                                                                   extra
        --------------------------+----------------+----------------+-------------------------------+---------------+--------------------------------------+--------------------------------------+-------------------------------+-----------------------------------------------------------------------+-----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------
        CHAN_START                | 1715113655.622 | 1715113655.622 | 2024-05-07 20:27:35.098091+00 | +12345678910  | +12345678910                         | 1006                                 | default-key-4wfgx-from-extern | PJSIP/2c70p24m-000000a3                                               |                 |                                                                                                                                                         |
        XIVO_INCALL               | 1715113655.622 | 1715113655.622 | 2024-05-07 20:27:35.425316+00 | 0012345678910 | 0012345678910                        | s                                    | did                           | PJSIP/2c70p24m-000000a3                                               | CELGenUserEvent | XIVO_INCALL,54eb71f8-1f4b-4ae4-8730-638062fbe521                                                                                                        | {"extra":"54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        WAZO_CALL_LOG_DESTINATION | 1715113655.622 | 1715113655.622 | 2024-05-07 20:27:35.477246+00 | 0012345678910 | 0012345678910                        | s                                    | group                         | PJSIP/2c70p24m-000000a3                                               | CELGenUserEvent | WAZO_CALL_LOG_DESTINATION,type: group,id: 9,label: supportgroup1                                                                                        | {"extra":"type: group,id: 9,label: supportgroup1"}
        APP_START                 | 1715113655.622 | 1715113655.622 | 2024-05-07 20:27:35.514455+00 | 0012345678910 | 0012345678910                        | s                                    | group                         | PJSIP/2c70p24m-000000a3                                               | Queue           | grp-charlescli-9f16208e-bf72-4d71-be21-48a10377dc15,ir,,,12,,wazo-group-answered                                                                        |
        CHAN_START                | 1715113655.623 | 1715113655.622 | 2024-05-07 20:27:35.521314+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113655.624 | 1715113655.622 | 2024-05-07 20:27:35.521346+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;2 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113655.625 | 1715113655.622 | 2024-05-07 20:27:35.521743+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113655.626 | 1715113655.622 | 2024-05-07 20:27:35.521765+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715113655.624 | 1715113655.622 | 2024-05-07 20:27:35.524748+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        WAZO_ORIGINATE_ALL_LINES  | 1715113655.626 | 1715113655.622 | 2024-05-07 20:27:35.525173+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715113655.624 | 1715113655.622 | 2024-05-07 20:27:35.69435+00  | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;2 | Dial            | Local/9EYlfTvB@wazo_wait_for_registration                                                                                                               |
        CHAN_START                | 1715113655.627 | 1715113655.622 | 2024-05-07 20:27:35.694456+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e1;1                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715113655.628 | 1715113655.622 | 2024-05-07 20:27:35.694484+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e1;2                  |                 |                                                                                                                                                         |
        APP_START                 | 1715113655.626 | 1715113655.622 | 2024-05-07 20:27:35.788284+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;2 | Dial            | PJSIP/rNXlGVeY/sip:tqct5poc@127.0.0.1:60812;transport=WS;x-ast-orig-host=192.0.2.40:0                                                                   |
        CHAN_START                | 1715113655.629 | 1715113655.622 | 2024-05-07 20:27:35.789402+00 | User 2        | 8002                                 | s                                    | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a4                                               |                 |                                                                                                                                                         |
        CHAN_START                | 1715113655.630 | 1715113655.622 | 2024-05-07 20:27:35.829757+00 | User 1        | 8001                                 | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a5                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715113655.623 | 1715113655.622 | 2024-05-07 20:27:39.540275+00 |               | 1006                                 | s                                    | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;1 | AppQueue        | (Outgoing Line)                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113655.623 | 1715113655.622 | 2024-05-07 20:27:39.540275+00 |               | 1006                                 | s                                    | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;1 | AppQueue        | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113655.625 | 1715113655.622 | 2024-05-07 20:27:39.540581+00 | User 2        | 8002                                 | s                                    | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;1 | AppQueue        | (Outgoing Line)                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113655.625 | 1715113655.622 | 2024-05-07 20:27:39.540581+00 | User 2        | 8002                                 | s                                    | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;1 | AppQueue        | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113655.627 | 1715113655.622 | 2024-05-07 20:27:39.544507+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e1;1                  | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113655.627 | 1715113655.622 | 2024-05-07 20:27:39.544507+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e1;1                  | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113655.624 | 1715113655.622 | 2024-05-07 20:27:39.544929+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;2 |                 |                                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715113655.624 | 1715113655.622 | 2024-05-07 20:27:39.544929+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000df;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715113655.626 | 1715113655.622 | 2024-05-07 20:27:39.545776+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;2 |                 |                                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715113655.626 | 1715113655.622 | 2024-05-07 20:27:39.545776+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e0;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715113655.628 | 1715113655.622 | 2024-05-07 20:27:39.549687+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e1;2                  |                 |                                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113655.628 | 1715113655.622 | 2024-05-07 20:27:39.549687+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e1;2                  |                 |                                                                                                                                                         |
        HANGUP                    | 1715113655.629 | 1715113655.622 | 2024-05-07 20:27:39.551886+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a4                                               | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113655.629 | 1715113655.622 | 2024-05-07 20:27:39.551886+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a4                                               | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113655.630 | 1715113655.622 | 2024-05-07 20:27:39.747419+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a5                                               | AppDial2        | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113655.630 | 1715113655.622 | 2024-05-07 20:27:39.747419+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a5                                               | AppDial2        | (Outgoing Line)                                                                                                                                         |
        CHAN_START                | 1715113660.631 | 1715113655.622 | 2024-05-07 20:27:40.540796+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113660.632 | 1715113655.622 | 2024-05-07 20:27:40.540851+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;2 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113660.633 | 1715113655.622 | 2024-05-07 20:27:40.541471+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113660.634 | 1715113655.622 | 2024-05-07 20:27:40.541504+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715113660.632 | 1715113655.622 | 2024-05-07 20:27:40.545855+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        WAZO_ORIGINATE_ALL_LINES  | 1715113660.634 | 1715113655.622 | 2024-05-07 20:27:40.546489+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715113660.632 | 1715113655.622 | 2024-05-07 20:27:40.73014+00  | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;2 | Dial            | Local/9EYlfTvB@wazo_wait_for_registration                                                                                                               |
        CHAN_START                | 1715113660.635 | 1715113655.622 | 2024-05-07 20:27:40.730243+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e4;1                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715113660.636 | 1715113655.622 | 2024-05-07 20:27:40.730269+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e4;2                  |                 |                                                                                                                                                         |
        APP_START                 | 1715113660.634 | 1715113655.622 | 2024-05-07 20:27:40.829037+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;2 | Dial            | PJSIP/rNXlGVeY/sip:tqct5poc@127.0.0.1:60812;transport=WS;x-ast-orig-host=192.0.2.40:0                                                                   |
        CHAN_START                | 1715113660.637 | 1715113655.622 | 2024-05-07 20:27:40.830107+00 | User 2        | 8002                                 | s                                    | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a6                                               |                 |                                                                                                                                                         |
        CHAN_START                | 1715113660.638 | 1715113655.622 | 2024-05-07 20:27:40.866989+00 | User 1        | 8001                                 | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a7                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715113660.631 | 1715113655.622 | 2024-05-07 20:27:44.559996+00 |               | 1006                                 | s                                    | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;1 | AppQueue        | (Outgoing Line)                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113660.631 | 1715113655.622 | 2024-05-07 20:27:44.559996+00 |               | 1006                                 | s                                    | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;1 | AppQueue        | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113660.633 | 1715113655.622 | 2024-05-07 20:27:44.560327+00 | User 2        | 8002                                 | s                                    | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;1 | AppQueue        | (Outgoing Line)                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113660.633 | 1715113655.622 | 2024-05-07 20:27:44.560327+00 | User 2        | 8002                                 | s                                    | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;1 | AppQueue        | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113660.635 | 1715113655.622 | 2024-05-07 20:27:44.563941+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e4;1                  | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113660.635 | 1715113655.622 | 2024-05-07 20:27:44.563941+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e4;1                  | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113660.632 | 1715113655.622 | 2024-05-07 20:27:44.564211+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;2 |                 |                                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715113660.632 | 1715113655.622 | 2024-05-07 20:27:44.564211+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e2;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715113660.634 | 1715113655.622 | 2024-05-07 20:27:44.564912+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;2 |                 |                                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715113660.634 | 1715113655.622 | 2024-05-07 20:27:44.564912+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e3;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715113660.636 | 1715113655.622 | 2024-05-07 20:27:44.568651+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e4;2                  |                 |                                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113660.636 | 1715113655.622 | 2024-05-07 20:27:44.568651+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e4;2                  |                 |                                                                                                                                                         |
        HANGUP                    | 1715113660.637 | 1715113655.622 | 2024-05-07 20:27:44.570786+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a6                                               | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113660.637 | 1715113655.622 | 2024-05-07 20:27:44.570786+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a6                                               | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113660.638 | 1715113655.622 | 2024-05-07 20:27:44.760229+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a7                                               | AppDial2        | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113660.638 | 1715113655.622 | 2024-05-07 20:27:44.760229+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a7                                               | AppDial2        | (Outgoing Line)                                                                                                                                         |
        CHAN_START                | 1715113665.639 | 1715113655.622 | 2024-05-07 20:27:45.560847+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113665.640 | 1715113655.622 | 2024-05-07 20:27:45.561176+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;2 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113665.641 | 1715113655.622 | 2024-05-07 20:27:45.563881+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715113665.642 | 1715113655.622 | 2024-05-07 20:27:45.563975+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715113665.640 | 1715113655.622 | 2024-05-07 20:27:45.576478+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        WAZO_ORIGINATE_ALL_LINES  | 1715113665.642 | 1715113655.622 | 2024-05-07 20:27:45.578161+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715113665.640 | 1715113655.622 | 2024-05-07 20:27:45.796159+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;2 | Dial            | Local/9EYlfTvB@wazo_wait_for_registration                                                                                                               |
        CHAN_START                | 1715113665.643 | 1715113655.622 | 2024-05-07 20:27:45.796267+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e7;1                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715113665.644 | 1715113655.622 | 2024-05-07 20:27:45.796293+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e7;2                  |                 |                                                                                                                                                         |
        APP_START                 | 1715113665.642 | 1715113655.622 | 2024-05-07 20:27:45.887087+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;2 | Dial            | PJSIP/rNXlGVeY/sip:tqct5poc@127.0.0.1:60812;transport=WS;x-ast-orig-host=192.0.2.40:0                                                                   |
        CHAN_START                | 1715113665.645 | 1715113655.622 | 2024-05-07 20:27:45.888116+00 | User 2        | 8002                                 | s                                    | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a8                                               |                 |                                                                                                                                                         |
        CHAN_START                | 1715113665.646 | 1715113655.622 | 2024-05-07 20:27:45.933797+00 | User 1        | 8001                                 | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a9                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715113665.639 | 1715113655.622 | 2024-05-07 20:27:47.582958+00 |               | 1006                                 | s                                    | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;1 | AppQueue        | (Outgoing Line)                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113665.639 | 1715113655.622 | 2024-05-07 20:27:47.582958+00 |               | 1006                                 | s                                    | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;1 | AppQueue        | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113665.641 | 1715113655.622 | 2024-05-07 20:27:47.583264+00 | User 2        | 8002                                 | s                                    | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;1 | AppQueue        | (Outgoing Line)                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113665.641 | 1715113655.622 | 2024-05-07 20:27:47.583264+00 | User 2        | 8002                                 | s                                    | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;1 | AppQueue        | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113665.643 | 1715113655.622 | 2024-05-07 20:27:47.587237+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e7;1                  | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113665.643 | 1715113655.622 | 2024-05-07 20:27:47.587237+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e7;1                  | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113665.640 | 1715113655.622 | 2024-05-07 20:27:47.587571+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;2 |                 |                                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715113665.640 | 1715113655.622 | 2024-05-07 20:27:47.587571+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e5;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715113665.642 | 1715113655.622 | 2024-05-07 20:27:47.588241+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;2 |                 |                                                                                                                                                         | {"hangupcause":0,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715113665.642 | 1715113655.622 | 2024-05-07 20:27:47.588241+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000e6;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715113665.644 | 1715113655.622 | 2024-05-07 20:27:47.592275+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e7;2                  |                 |                                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113665.644 | 1715113655.622 | 2024-05-07 20:27:47.592275+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000e7;2                  |                 |                                                                                                                                                         |
        HANGUP                    | 1715113665.645 | 1715113655.622 | 2024-05-07 20:27:47.594551+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a8                                               | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113665.645 | 1715113655.622 | 2024-05-07 20:27:47.594551+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000a8                                               | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715113655.622 | 1715113655.622 | 2024-05-07 20:27:47.613492+00 | 0012345678910 | 0012345678910                        | s                                    | did                           | PJSIP/2c70p24m-000000a3                                               |                 |                                                                                                                                                         | {"hangupcause":16,"hangupsource":"dialplan/builtin","dialstatus":"NOANSWER"}
        CHAN_END                  | 1715113655.622 | 1715113655.622 | 2024-05-07 20:27:47.613492+00 | 0012345678910 | 0012345678910                        | s                                    | did                           | PJSIP/2c70p24m-000000a3                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715113665.646 | 1715113655.622 | 2024-05-07 20:27:47.775383+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a9                                               | AppDial2        | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715113665.646 | 1715113655.622 | 2024-05-07 20:27:47.775383+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a9                                               | AppDial2        | (Outgoing Line)                                                                                                                                         |
        LINKEDID_END              | 1715113665.646 | 1715113655.622 | 2024-05-07 20:27:47.775383+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000a9                                               | AppDial2        | (Outgoing Line)                                                                                                                                         |
        '''
    )
    def test_incoming_call_to_group_ring_all_no_answer(self, cels):
        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        expected_properties = dict(
            source_name='0012345678910',
            source_exten='0012345678910',
            requested_exten='1006',
            destination_exten='1006',
            destination_name='supportgroup1',
            direction='inbound',
        )

        assert {
            prop: getattr(call_logs[0], prop) for prop in expected_properties
        } == expected_properties

    @raw_cels(
        '''
                 eventtype        |    uniqueid    |    linkedid    |           eventtime           |   cid_name    |               cid_num                |                exten                 |            context            |                               channame                                |     appname     |                                                                         appdata                                                                         |                                                                   extra
        --------------------------+----------------+----------------+-------------------------------+---------------+--------------------------------------+--------------------------------------+-------------------------------+-----------------------------------------------------------------------+-----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------
        CHAN_START                | 1715115875.647 | 1715115875.647 | 2024-05-07 21:04:35.560396+00 | +12345678910  | +12345678910                         | 1005                                 | default-key-4wfgx-from-extern | PJSIP/2c70p24m-000000aa                                               |                 |                                                                                                                                                         |
        XIVO_INCALL               | 1715115875.647 | 1715115875.647 | 2024-05-07 21:04:35.87404+00  | 0012345678910 | 0012345678910                        | s                                    | did                           | PJSIP/2c70p24m-000000aa                                               | CELGenUserEvent | XIVO_INCALL,54eb71f8-1f4b-4ae4-8730-638062fbe521                                                                                                        | {"extra":"54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        WAZO_CALL_LOG_DESTINATION | 1715115875.647 | 1715115875.647 | 2024-05-07 21:04:35.923002+00 | 0012345678910 | 0012345678910                        | s                                    | group                         | PJSIP/2c70p24m-000000aa                                               | CELGenUserEvent | WAZO_CALL_LOG_DESTINATION,type: group,id: 7,label: supportgroup1                                                                                        | {"extra":"type: group,id: 7,label: supportgroup1"}
        ANSWER                    | 1715115875.647 | 1715115875.647 | 2024-05-07 21:04:35.948642+00 | 0012345678910 | 0012345678910                        | pickup                               | xivo-pickup                   | PJSIP/2c70p24m-000000aa                                               | Answer          |                                                                                                                                                         |
        APP_START                 | 1715115875.647 | 1715115875.647 | 2024-05-07 21:04:37.214599+00 | 0012345678910 | 0012345678910                        | s                                    | group                         | PJSIP/2c70p24m-000000aa                                               | Dial            | Local/group-linear@group,45,tTimc                                                                                                                       |
        CHAN_START                | 1715115877.648 | 1715115875.647 | 2024-05-07 21:04:37.215081+00 |               |                                      | group-linear                         | group                         | Local/group-linear@group-000000e8;1                                   |                 |                                                                                                                                                         |
        CHAN_START                | 1715115877.649 | 1715115875.647 | 2024-05-07 21:04:37.215173+00 |               |                                      | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   |                 |                                                                                                                                                         |
        APP_START                 | 1715115877.649 | 1715115875.647 | 2024-05-07 21:04:37.317987+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   | Dial            | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines,5                                                                                            |
        CHAN_START                | 1715115877.650 | 1715115875.647 | 2024-05-07 21:04:37.318092+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715115877.651 | 1715115875.647 | 2024-05-07 21:04:37.318116+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715115877.651 | 1715115875.647 | 2024-05-07 21:04:37.320699+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715115877.651 | 1715115875.647 | 2024-05-07 21:04:37.401959+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;2 | Dial            | Local/9EYlfTvB@wazo_wait_for_registration,5,tTimc                                                                                                       |
        CHAN_START                | 1715115877.652 | 1715115875.647 | 2024-05-07 21:04:37.402062+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ea;1                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715115877.653 | 1715115875.647 | 2024-05-07 21:04:37.402088+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ea;2                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715115877.654 | 1715115875.647 | 2024-05-07 21:04:37.492504+00 | User 1        | 8001                                 | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000ab                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715115877.650 | 1715115875.647 | 2024-05-07 21:04:42.318938+00 |               | group-linear                         | group-linear                         | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;1 | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115877.650 | 1715115875.647 | 2024-05-07 21:04:42.318938+00 |               | group-linear                         | group-linear                         | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;1 | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115877.652 | 1715115875.647 | 2024-05-07 21:04:42.322252+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ea;1                  | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115877.652 | 1715115875.647 | 2024-05-07 21:04:42.322252+00 |               | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ea;1                  | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115877.651 | 1715115875.647 | 2024-05-07 21:04:42.322525+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;2 |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715115877.651 | 1715115875.647 | 2024-05-07 21:04:42.322525+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000e9;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715115877.653 | 1715115875.647 | 2024-05-07 21:04:42.325677+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ea;2                  |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115877.653 | 1715115875.647 | 2024-05-07 21:04:42.325677+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ea;2                  |                 |                                                                                                                                                         |
        HANGUP                    | 1715115877.654 | 1715115875.647 | 2024-05-07 21:04:42.456469+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000ab                                               | AppDial2        | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115877.654 | 1715115875.647 | 2024-05-07 21:04:42.456469+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000ab                                               | AppDial2        | (Outgoing Line)                                                                                                                                         |
        APP_START                 | 1715115877.649 | 1715115875.647 | 2024-05-07 21:04:47.320268+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   | Dial            | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines,5                                                                                            |
        CHAN_START                | 1715115887.655 | 1715115875.647 | 2024-05-07 21:04:47.320696+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715115887.656 | 1715115875.647 | 2024-05-07 21:04:47.320801+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715115887.656 | 1715115875.647 | 2024-05-07 21:04:47.331473+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715115887.656 | 1715115875.647 | 2024-05-07 21:04:47.4891+00   | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;2 | Dial            | PJSIP/rNXlGVeY/sip:tqct5poc@127.0.0.1:60812;transport=WS;x-ast-orig-host=192.0.2.40:0,5,tTimc                                                           |
        CHAN_START                | 1715115887.657 | 1715115875.647 | 2024-05-07 21:04:47.490137+00 | User 2        | 8002                                 | s                                    | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000ac                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715115887.655 | 1715115875.647 | 2024-05-07 21:04:52.322871+00 | User 2        | 8002                                 | group-linear                         | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;1 | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115887.655 | 1715115875.647 | 2024-05-07 21:04:52.322871+00 | User 2        | 8002                                 | group-linear                         | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;1 | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115887.656 | 1715115875.647 | 2024-05-07 21:04:52.326815+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;2 |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715115887.656 | 1715115875.647 | 2024-05-07 21:04:52.326815+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000eb;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715115887.657 | 1715115875.647 | 2024-05-07 21:04:52.329935+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000ac                                               | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115887.657 | 1715115875.647 | 2024-05-07 21:04:52.329935+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000ac                                               | AppDial         | (Outgoing Line)                                                                                                                                         |
        APP_START                 | 1715115877.649 | 1715115875.647 | 2024-05-07 21:04:57.323971+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   | Dial            | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines,5                                                                                            |
        CHAN_START                | 1715115897.658 | 1715115875.647 | 2024-05-07 21:04:57.324252+00 |               |                                      | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715115897.659 | 1715115875.647 | 2024-05-07 21:04:57.32432+00  |               |                                      | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715115897.659 | 1715115875.647 | 2024-05-07 21:04:57.331169+00 | 0012345678910 | 0012345678910                        | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:81ea4378-1647-4eae-ad83-26178bdc2890,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:81ea4378-1647-4eae-ad83-26178bdc2890,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715115897.659 | 1715115875.647 | 2024-05-07 21:04:57.459321+00 | 0012345678910 | 0012345678910                        | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;2 | Dial            | Local/chUXgaRK@wazo_wait_for_registration&PJSIP/ceQsPZwZ/sip:ceQsPZwZ@10.0.4.6:5060,5,tTimc                                                             |
        CHAN_START                | 1715115897.660 | 1715115875.647 | 2024-05-07 21:04:57.45945+00  |               |                                      | chUXgaRK                             | wazo_wait_for_registration    | Local/chUXgaRK@wazo_wait_for_registration-000000ed;1                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715115897.661 | 1715115875.647 | 2024-05-07 21:04:57.459477+00 |               |                                      | chUXgaRK                             | wazo_wait_for_registration    | Local/chUXgaRK@wazo_wait_for_registration-000000ed;2                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715115897.662 | 1715115875.647 | 2024-05-07 21:04:57.461374+00 | User 3        | 8000                                 | s                                    | default-key-4wfgx-internal    | PJSIP/ceQsPZwZ-000000ad                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715115897.658 | 1715115875.647 | 2024-05-07 21:05:02.326161+00 | User 2        | group-linear                         | group-linear                         | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;1 | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115897.658 | 1715115875.647 | 2024-05-07 21:05:02.326161+00 | User 2        | group-linear                         | group-linear                         | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;1 | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115897.660 | 1715115875.647 | 2024-05-07 21:05:02.329159+00 | User 2        | 81ea4378-1647-4eae-ad83-26178bdc2890 | 81ea4378-1647-4eae-ad83-26178bdc2890 | wazo_wait_for_registration    | Local/chUXgaRK@wazo_wait_for_registration-000000ed;1                  | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115897.660 | 1715115875.647 | 2024-05-07 21:05:02.329159+00 | User 2        | 81ea4378-1647-4eae-ad83-26178bdc2890 | 81ea4378-1647-4eae-ad83-26178bdc2890 | wazo_wait_for_registration    | Local/chUXgaRK@wazo_wait_for_registration-000000ed;1                  | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115897.659 | 1715115875.647 | 2024-05-07 21:05:02.329486+00 | 0012345678910 | 0012345678910                        | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;2 |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715115897.659 | 1715115875.647 | 2024-05-07 21:05:02.329486+00 | 0012345678910 | 0012345678910                        | 81ea4378-1647-4eae-ad83-26178bdc2890 | usersharedlines               | Local/81ea4378-1647-4eae-ad83-26178bdc2890@usersharedlines-000000ec;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715115897.661 | 1715115875.647 | 2024-05-07 21:05:02.332805+00 | 0012345678910 | 0012345678910                        | chUXgaRK                             | wazo_wait_for_registration    | Local/chUXgaRK@wazo_wait_for_registration-000000ed;2                  |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115897.661 | 1715115875.647 | 2024-05-07 21:05:02.332805+00 | 0012345678910 | 0012345678910                        | chUXgaRK                             | wazo_wait_for_registration    | Local/chUXgaRK@wazo_wait_for_registration-000000ed;2                  |                 |                                                                                                                                                         |
        HANGUP                    | 1715115897.662 | 1715115875.647 | 2024-05-07 21:05:02.334788+00 | User 3        | 8000                                 | 81ea4378-1647-4eae-ad83-26178bdc2890 | default-key-4wfgx-internal    | PJSIP/ceQsPZwZ-000000ad                                               | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115897.662 | 1715115875.647 | 2024-05-07 21:05:02.334788+00 | User 3        | 8000                                 | 81ea4378-1647-4eae-ad83-26178bdc2890 | default-key-4wfgx-internal    | PJSIP/ceQsPZwZ-000000ad                                               | AppDial         | (Outgoing Line)                                                                                                                                         |
        APP_START                 | 1715115877.649 | 1715115875.647 | 2024-05-07 21:05:07.371696+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   | Dial            | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines,5                                                                                            |
        CHAN_START                | 1715115907.663 | 1715115875.647 | 2024-05-07 21:05:07.371833+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715115907.664 | 1715115875.647 | 2024-05-07 21:05:07.371868+00 |               |                                      | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715115907.664 | 1715115875.647 | 2024-05-07 21:05:07.375369+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715115907.664 | 1715115875.647 | 2024-05-07 21:05:07.478205+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;2 | Dial            | Local/9EYlfTvB@wazo_wait_for_registration,5,tTimc                                                                                                       |
        CHAN_START                | 1715115907.665 | 1715115875.647 | 2024-05-07 21:05:07.478307+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ef;1                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715115907.666 | 1715115875.647 | 2024-05-07 21:05:07.478331+00 |               |                                      | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ef;2                  |                 |                                                                                                                                                         |
        CHAN_START                | 1715115907.667 | 1715115875.647 | 2024-05-07 21:05:07.582863+00 | User 1        | 8001                                 | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000ae                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715115907.663 | 1715115875.647 | 2024-05-07 21:05:12.373277+00 | User 2        | group-linear                         | group-linear                         | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;1 | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115907.663 | 1715115875.647 | 2024-05-07 21:05:12.373277+00 | User 2        | group-linear                         | group-linear                         | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;1 | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115907.665 | 1715115875.647 | 2024-05-07 21:05:12.376721+00 | User 2        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ef;1                  | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115907.665 | 1715115875.647 | 2024-05-07 21:05:12.376721+00 | User 2        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ef;1                  | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115907.664 | 1715115875.647 | 2024-05-07 21:05:12.377034+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;2 |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715115907.664 | 1715115875.647 | 2024-05-07 21:05:12.377034+00 | 0012345678910 | 0012345678910                        | ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6 | usersharedlines               | Local/ad5b78cf-6e15-45c7-9ef3-bec36e07e8d6@usersharedlines-000000ee;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715115907.666 | 1715115875.647 | 2024-05-07 21:05:12.380261+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ef;2                  |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115907.666 | 1715115875.647 | 2024-05-07 21:05:12.380261+00 | 0012345678910 | 0012345678910                        | 9EYlfTvB                             | wazo_wait_for_registration    | Local/9EYlfTvB@wazo_wait_for_registration-000000ef;2                  |                 |                                                                                                                                                         |
        HANGUP                    | 1715115907.667 | 1715115875.647 | 2024-05-07 21:05:12.552314+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000ae                                               | AppDial2        | (Outgoing Line)                                                                                                                                         | {"hangupcause":16,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115907.667 | 1715115875.647 | 2024-05-07 21:05:12.552314+00 | 0012345678910 | 0012345678910                        | s                                    | default-key-4wfgx-internal    | PJSIP/9EYlfTvB-000000ae                                               | AppDial2        | (Outgoing Line)                                                                                                                                         |
        APP_START                 | 1715115877.649 | 1715115875.647 | 2024-05-07 21:05:17.374695+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   | Dial            | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines,5                                                                                            |
        CHAN_START                | 1715115917.668 | 1715115875.647 | 2024-05-07 21:05:17.3751+00   |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;1 |                 |                                                                                                                                                         |
        CHAN_START                | 1715115917.669 | 1715115875.647 | 2024-05-07 21:05:17.375198+00 |               |                                      | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;2 |                 |                                                                                                                                                         |
        WAZO_ORIGINATE_ALL_LINES  | 1715115917.669 | 1715115875.647 | 2024-05-07 21:05:17.385636+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;2 | CELGenUserEvent | WAZO_ORIGINATE_ALL_LINES,user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521                                | {"extra":"user_uuid:31be0853-dde6-48cd-986d-85bc708754a1,tenant_uuid:54eb71f8-1f4b-4ae4-8730-638062fbe521"}
        APP_START                 | 1715115917.669 | 1715115875.647 | 2024-05-07 21:05:17.53409+00  | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;2 | Dial            | PJSIP/rNXlGVeY/sip:tqct5poc@127.0.0.1:60812;transport=WS;x-ast-orig-host=192.0.2.40:0,5,tTimc                                                           |
        CHAN_START                | 1715115917.670 | 1715115875.647 | 2024-05-07 21:05:17.535145+00 | User 2        | 8002                                 | s                                    | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000af                                               |                 |                                                                                                                                                         |
        HANGUP                    | 1715115877.648 | 1715115875.647 | 2024-05-07 21:05:22.226985+00 | User 2        | 8002                                 | s                                    | group                         | Local/group-linear@group-000000e8;1                                   | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115877.648 | 1715115875.647 | 2024-05-07 21:05:22.226985+00 | User 2        | 8002                                 | s                                    | group                         | Local/group-linear@group-000000e8;1                                   | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115917.668 | 1715115875.647 | 2024-05-07 21:05:22.245392+00 | User 2        | 8002                                 | group-linear                         | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;1 | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115917.668 | 1715115875.647 | 2024-05-07 21:05:22.245392+00 | User 2        | 8002                                 | group-linear                         | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;1 | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115877.649 | 1715115875.647 | 2024-05-07 21:05:22.245698+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":"NOANSWER"}
        CHAN_END                  | 1715115877.649 | 1715115875.647 | 2024-05-07 21:05:22.245698+00 | 0012345678910 | 0012345678910                        | group-linear                         | group                         | Local/group-linear@group-000000e8;2                                   |                 |                                                                                                                                                         |
        HANGUP                    | 1715115917.669 | 1715115875.647 | 2024-05-07 21:05:22.246854+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;2 |                 |                                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":"CANCEL"}
        CHAN_END                  | 1715115917.669 | 1715115875.647 | 2024-05-07 21:05:22.246854+00 | 0012345678910 | 0012345678910                        | 31be0853-dde6-48cd-986d-85bc708754a1 | usersharedlines               | Local/31be0853-dde6-48cd-986d-85bc708754a1@usersharedlines-000000f0;2 |                 |                                                                                                                                                         |
        HANGUP                    | 1715115917.670 | 1715115875.647 | 2024-05-07 21:05:22.253566+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000af                                               | AppDial         | (Outgoing Line)                                                                                                                                         | {"hangupcause":26,"hangupsource":"","dialstatus":""}
        CHAN_END                  | 1715115917.670 | 1715115875.647 | 2024-05-07 21:05:22.253566+00 | User 2        | 8002                                 | 31be0853-dde6-48cd-986d-85bc708754a1 | default-key-4wfgx-internal    | PJSIP/rNXlGVeY-000000af                                               | AppDial         | (Outgoing Line)                                                                                                                                         |
        HANGUP                    | 1715115875.647 | 1715115875.647 | 2024-05-07 21:05:24.933556+00 | 0012345678910 | 0012345678910                        | sound                                | forward                       | PJSIP/2c70p24m-000000aa                                               |                 |                                                                                                                                                         | {"hangupcause":16,"hangupsource":"dialplan/builtin","dialstatus":"NOANSWER"}
        CHAN_END                  | 1715115875.647 | 1715115875.647 | 2024-05-07 21:05:24.933556+00 | 0012345678910 | 0012345678910                        | sound                                | forward                       | PJSIP/2c70p24m-000000aa                                               |                 |                                                                                                                                                         |
        LINKEDID_END              | 1715115875.647 | 1715115875.647 | 2024-05-07 21:05:24.933556+00 | 0012345678910 | 0012345678910                        | sound                                | forward                       | PJSIP/2c70p24m-000000aa                                               |                 |                                                                                                                                                         |
        '''
    )
    def test_incoming_call_to_linear_ring_group(self, cels):
        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        expected_properties = dict(
            source_name='0012345678910',
            source_exten='0012345678910',
            requested_exten='1005',
            destination_exten='1005',
            destination_name='supportgroup1',
            direction='inbound',
        )

        assert {
            prop: getattr(call_logs[0], prop) for prop in expected_properties
        } == expected_properties

    @raw_cels(
        '''
        eventtype                      | eventtime                         | cid_name              | cid_num       | cid_ani   | exten     | context       | channame                  | linkedid      | uniqueid          | extra
        --------------------------------+-----------------------------------+-----------------------+---------------+-----------+-----------+---------------+---------------------------+---------------+-------------------+-------------------------------------------------------------------------------------------------------------------------------------------------
        CHAN_START                     | 2022-07-21 09:31:28.178728        | Harry Potter          | 1603          |           | 91800     | mycontext     | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      |
        XIVO_INCALL                    | 2022-07-21 09:31:28.236466        | Harry Potter          | 1603          | 1603      | s         | did           | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"extra":}
        WAZO_CALL_LOG_DESTINATION      | 2022-07-21 09:31:28.73542         | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000000   | 1658410288.0  | 1658410288.0      | {"extra":"type"}
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
        CHAN_START                     | 2022-07-21 09:31:37.178728        | Harry Potter          | 1603          |           | 91800     | mycontext     | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      |
        XIVO_INCALL                    | 2022-07-21 09:31:37.236466        | Harry Potter          | 1603          | 1603      | s         | did           | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      | {"extra":"006a72c4-eb68-481a-808f-33b28ec109c8"}
        WAZO_CALL_LOG_DESTINATION      | 2022-07-21 09:31:37.73542         | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      | {"extra":"type: user,uuid: cb79f29b-f69a-4b93-85c2-49dcce119a9f,name: Harry Potter"}
        APP_START                      | 2022-07-21 09:31:37.758777        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      |
        CHAN_START                     | 2022-07-21 09:31:37.764391        | Harry Potter          | 1603          |           | s         | mycontext     | PJSIP/cul113qn-00000003   | 1658410289.0  | 1658410289.1      |
        ANSWER                         | 2022-07-21 09:31:38.637187        | Harry Potter          | 1603          | 1603      | s         | mycontext     | PJSIP/cul113qn-00000003   | 1658410289.0  | 1658410289.1      |
        ANSWER                         | 2022-07-21 09:31:38.637723        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      |
        BRIDGE_ENTER                   | 2022-07-21 09:31:38.641326        | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000003   | 1658410289.0  | 1658410289.1      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
        BRIDGE_ENTER                   | 2022-07-21 09:31:38.643468        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
        BRIDGE_EXIT                    | 2022-07-21 09:31:39.363285        | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000003   | 1658410289.0  | 1658410289.1      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
        HANGUP                         | 2022-07-21 09:31:39.36417         | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000003   | 1658410289.0  | 1658410289.1      | {"hangupcause":16,"hangupsource":"PJSIP/cul113qn-00000002","dialstatus":""}
        CHAN_END                       | 2022-07-21 09:31:39.36417         | Harry Potter          | 1603          | 1603      |           | mycontext     | PJSIP/cul113qn-00000003   | 1658410289.0  | 1658410289.1      |
        BRIDGE_EXIT                    | 2022-07-21 09:31:39.367518        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      | {"bridge_id":"4a665fad-b8d1-4c47-9b7f-f4b48ee38fed","bridge_technology":"simple_bridge"}
        HANGUP                         | 2022-07-21 09:31:39.373807        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      | {"hangupcause":16,"hangupsource":"PJSIP/cul113qn-00000002","dialstatus":"ANSWER"}
        CHAN_END                       | 2022-07-21 09:31:39.373807        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      |
        LINKEDID_END                   | 2022-07-21 09:31:39.373807        | Harry Potter          | 1603          | 1603      | s         | user          | PJSIP/cul113qn-00000002   | 1658410289.0  | 1658410289.0      |
        '''
    )
    def test_bad_apple(self, cels: list[CEL]):
        """
        CELs contains two similar calls, but first CEL sequence is corrupted(bad extra values) and will fail to process,
        while second CEL sequence will be processed correctly
        """
        tenant_uuid = '006a72c4-eb68-481a-808f-33b28ec109c8'
        user_uuid = 'cb79f29b-f69a-4b93-85c2-49dcce119a9f'
        user_name = 'Harry Potter'
        self.generator.confd = mock_confd_client(
            users=[mock_user(uuid=user_uuid, tenant_uuid=tenant_uuid)]
        )

        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        assert_that(
            call_logs[0],
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
        '''
        eventtype                 |           eventtime           | cid_name | cid_num | cid_ani | cid_dnid | exten  |                           context                            |        channame         |     appname     |                       appdata                       | amaflags |   uniqueid   |   linkedid   | peer |                                    extra
        --------------------------+-------------------------------+----------+---------+---------+----------+--------+--------------------------------------------------------------+-------------------------+-----------------+-----------------------------------------------------+----------+--------------+--------------+------+-----------------------------------------------------------------------------
        CHAN_END                  | 2025-08-11 14:55:10.87219-04  | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        LINKEDID_END              | 2025-08-11 14:55:10.87219-04  | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        CHAN_START                | 2025-08-11 14:54:56.531176-04 | Fern     | 10006   |         |          | 30001  | ctx-pcmdev00de-internal-a25ef16e-faaf-41ad-b1ad-aa2d715b6c05 | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        WAZO_CALL_LOG_DESTINATION | 2025-08-11 14:54:56.752166-04 | Fern     | 10006   | 10006   |          | s      | queue                                                        | PJSIP/yeFKZg6L-00000003 | CELGenUserEvent | WAZO_CALL_LOG_DESTINATION,type: queue,id: 2,label: My Queue Name,tenant_uuid: 82f60c78-fc94-4936-b3fb-7b276c69df9d |        3 |  1754938496.0 | 1754938496.0 |           | {"extra":"type: queue,id: 2,label: My Queue Name,tenant_uuid: 82f60c78-fc94-4936-b3fb-7b276c69df9d"}
        ANSWER                    | 2025-08-11 14:54:57.064198-04 | Fern     | 10006   | 10006   | 30001    | pickup | xivo-pickup                                                  | PJSIP/yeFKZg6L-00000000 | Answer          |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        APP_START                 | 2025-08-11 14:54:58.725743-04 | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 | Queue           | q-11668931,iC,,,,,wazo-queue-answered,,,            |        3 | 1754938496.0 | 1754938496.0 |      |
        HANGUP                    | 2025-08-11 14:55:10.87219-04  | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      | {"hangupcause":16,"hangupsource":"PJSIP/yeFKZg6L-00000000","dialstatus":""}

        '''
    )
    def test_call_to_queue_no_answer(self, cels: list[CEL]):
        call_logs = self.generator.call_logs_from_cel(cels)
        assert call_logs
        assert len(call_logs) == 1

        assert_that(
            call_logs[0],
            has_properties(
                source_name='Fern',
                source_exten='10006',
                requested_exten='30001',
                destination_exten='30001',
                destination_name='My Queue Name',
                direction='internal',
                tenant_uuid='82f60c78-fc94-4936-b3fb-7b276c69df9d',
                destination_details=contains_inanyorder(
                    has_properties(
                        destination_details_key='type',
                        destination_details_value='queue',
                    ),
                    has_properties(
                        destination_details_key='queue_label',
                        destination_details_value='My Queue Name',
                    ),
                    has_properties(
                        destination_details_key='queue_id',
                        destination_details_value='2',
                    ),
                ),
            ),
        )

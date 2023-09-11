# Copyright 2013-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
from dataclasses import dataclass, fields
from datetime import datetime, timedelta

from functools import wraps
import logging

from typing import get_type_hints
from unittest import TestCase
from unittest.mock import MagicMock, Mock, create_autospec
from uuid import uuid4

from hamcrest import (
    assert_that,
    contains_inanyorder,
    has_properties,
)
from requests import HTTPError

# from xivo_dao.alchemy.cel import CEL
from wazo_confd_client import Client as ConfdClient
from wazo_call_logd.cel_interpretor import (
    CalleeCELInterpretor,
    CallerCELInterpretor,
    DispatchCELInterpretor,
    LocalOriginateCELInterpretor,
    parse_eventtime,
)

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

    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            return func(
                self,
                [CEL(id=i, **fields) for i, fields in enumerate(cels)],
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
    """
    Create a mock user dictionary with the given parameters.

    uuid (str): The UUID of the user.
    tenant_uuid (str): The UUID of the tenant.
    line_ids (list[str] | None, optional): The list of line IDs. Defaults to None.
    mobile (str | None, optional): The mobile phone number. Defaults to None.
    userfield (str | None, optional): The user field. Defaults to None.

    Returns (dict[str, any]): The mock user dictionary.
    """
    return mock_dict(
        {
            'uuid': uuid,
            'tenant_uuid': tenant_uuid,
            'lines': [
                {'id': line_id, 'extensions': [], 'name': ''} for line_id in line_ids
            ]
            if line_ids
            else [],
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
    """
    Mocks a line.

    :param id: The line ID.
    :param name: The line name.
    :param protocol: The line protocol.
    :param users: The users associated with the line.
    :param context: The line context.
    :param extensions: The line extensions.
    :param tenant_uuid: The tenant UUID.
    :return: The mocked line.
    """
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
    """
    Mocks a switchboard.

    :param uuid: The switchboard UUID.
    :param name: The switchboard name.
    :return: The mocked switchboard.
    """
    return mock_dict({'uuid': uuid, 'name': name})


def mock_context(id: int, name: str, tenant_uuid: str) -> dict[str, int | str]:
    """
    Mocks a context.

    :param id: The context ID.
    :param name: The context name.
    :param tenant_uuid: The tenant UUID.
    :return: The mocked context.
    """
    return mock_dict({'id': id, 'name': name, 'tenant_uuid': tenant_uuid})


def mock_confd_client(
    lines: list[dict] = None,
    users: list[dict] = None,
    contexts: list[dict] = None,
) -> ConfdClient:
    confd_client = create_autospec(
        ConfdClient, instance=True, lines=Mock(), users=Mock(), contexts=Mock()
    )
    confd_client.lines.list.side_effect = lambda name=None, **kwargs: {
        'items': [line for line in lines if line['name'] == name]
        if lines and name
        else lines
        if lines and not name
        else []
    }
    confd_client.users.get.side_effect = (
        (lambda uuid: next(user for user in users if user['uuid'] == uuid))
        if users is not None
        else HTTPError
    )
    confd_client.contexts.list.side_effect = lambda name=None, **kwargs: {
        'items': [context for context in contexts if context['name'] == name]
        if name and contexts
        else contexts
        if contexts
        else []
    }
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
            [
                LocalOriginateCELInterpretor(),
                DispatchCELInterpretor(
                    CallerCELInterpretor(),
                    CalleeCELInterpretor(),
                ),
            ],
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

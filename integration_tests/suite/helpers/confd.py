# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import TypedDict
from uuid import UUID

import requests


class ConfdClient:
    def __init__(self, host, port):
        self._host = host
        self._port = port

    def url(self, *parts):
        return 'http://{host}:{port}/{path}'.format(
            host=self._host, port=self._port, path='/'.join(parts)
        )

    def is_up(self):
        url = self.url()
        try:
            response = requests.get(url)
            return response.status_code == 404
        except requests.RequestException:
            return False

    def set_users(self, *mock_users):
        url = self.url('_set_response')
        body = {
            'response': 'users',
            'content': {user.uuid(): user.to_dict() for user in mock_users},
        }
        requests.post(url, json=body)

    def set_lines(self, *mock_lines):
        url = self.url('_set_response')
        body = {
            'response': 'lines',
            'content': {line.id_(): line.to_dict() for line in mock_lines},
        }
        requests.post(url, json=body)

    def set_user_lines(self, set_user_lines):
        content = {}
        for user, user_lines in set_user_lines.items():
            content[user] = [user_line.to_dict() for user_line in user_lines]

        url = self.url('_set_response')
        body = {'response': 'user_lines', 'content': content}
        requests.post(url, json=body)

    def set_switchboards(self, *mock_switchboards):
        url = self.url('_set_response')
        body = {
            'response': 'switchboards',
            'content': {
                switchboard.uuid(): switchboard.to_dict()
                for switchboard in mock_switchboards
            },
        }

        requests.post(url, json=body)

    def set_contexts(self, *mock_contexts):
        url = self.url('_set_response')
        body = {
            'response': 'contexts',
            'content': {context.id_(): context.to_dict() for context in mock_contexts},
        }
        requests.post(url, json=body)

    def reset(self):
        url = self.url('_reset')
        requests.post(url)


class UserLineData(TypedDict):
    id: str
    extensions: list[str]
    name: str


class MockUserData(TypedDict):
    uuid: str
    tenant_uuid: str
    lines: list[UserLineData]
    mobile_phone_number: str | None
    userfield: str | None


class MockUser:
    def __init__(self, uuid, tenant_uuid, line_ids=None, mobile=None, userfield=None):
        self._uuid = str(uuid)
        self._tenant_uuid = str(tenant_uuid)
        self._line_ids = line_ids or []
        self._mobile = mobile
        self._userfield = userfield

    def uuid(self):
        return self._uuid

    def to_dict(self) -> MockUserData:
        return {
            'uuid': self._uuid,
            'tenant_uuid': self._tenant_uuid,
            'lines': [
                {'id': line_id, 'extensions': [], 'name': ''}
                for line_id in self._line_ids
            ],
            'mobile_phone_number': self._mobile,
            'userfield': self._userfield,
        }


class LineUserData(TypedDict):
    uuid: str | UUID


class LineExtensionData(TypedDict):
    exten: str
    context: str


class MockLineData(TypedDict):
    id: int
    name: str | None
    protocol: str | None
    users: list[LineUserData] | None
    context: str | None
    extensions: list[LineExtensionData] | None
    tenant_uuid: str | None


class MockLine:
    def __init__(
        self,
        id: int,
        name: str | None = None,
        protocol: str | None = None,
        users: list[LineUserData] | None = None,
        context: str | None = None,
        extensions: list[LineExtensionData] | None = None,
        tenant_uuid: str | UUID | None = None,
    ):
        self._id = id
        self._name = name
        self._protocol = protocol
        self._users = (
            [LineUserData(uuid=str(user['uuid'])) for user in users] if users else []
        )
        self._extensions = extensions or []
        self._context = context
        self._tenant_uuid = tenant_uuid and str(tenant_uuid)

    def id_(self):
        return self._id

    def users(self):
        return self._users

    def to_dict(self) -> MockLineData:
        return {
            'id': self._id,
            'name': self._name,
            'protocol': self._protocol,
            'context': self._context,
            'tenant_uuid': self._tenant_uuid,
            'users': self._users,
            'extensions': self._extensions,
        }


class MockSwitchboardData(TypedDict):
    uuid: str
    name: str | None


class MockSwitchboard:
    def __init__(self, uuid: str | UUID, name: str | None = None):
        self._uuid = str(uuid)
        self._name = name

    def uuid(self):
        return self._uuid

    def to_dict(self) -> MockSwitchboardData:
        return {'uuid': self._uuid, 'name': self._name}


class MockContextData(TypedDict):
    id: int
    name: str
    tenant_uuid: str


class MockContext:
    def __init__(self, id: int, name: str, tenant_uuid: str | UUID):
        self._id = id
        self._name = name
        self._tenant_uuid = str(tenant_uuid)

    def id_(self):
        return self._id

    def to_dict(self) -> MockContextData:
        return {'id': self._id, 'name': self._name, 'tenant_uuid': self._tenant_uuid}

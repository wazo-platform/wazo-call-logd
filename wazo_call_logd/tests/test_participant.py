# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    has_entries,
    none,
)
from mock import Mock
from unittest import TestCase

from ..participant import find_participant


def confd_mock(lines=None):
    lines = lines or []
    confd = Mock()
    confd.lines.list.return_value = {'items': lines}
    confd.users.get.return_value = (
        lines[0]['users'][0] if lines and lines[0].get('users') else None
    )
    return confd


class TestFindParticipant(TestCase):
    def test_find_participants_when_channame_is_not_parsable(self):
        confd = confd_mock()
        channame = 'something'

        result = find_participant(confd, channame)

        assert_that(result, none())

    def test_find_participants_when_no_lines(self):
        confd = confd_mock()
        channame = 'sip/something-suffix'

        result = find_participant(confd, channame)

        assert_that(result, none())

    def test_find_participants_when_line_has_no_user(self):
        lines = [{'id': 12, 'users': []}]
        confd = confd_mock(lines)
        channame = 'sip/something-suffix'

        result = find_participant(confd, channame)

        assert_that(result, none())

    def test_find_participants_when_line_has_user(self):
        user = {
            'uuid': 'user_uuid',
            'tenant_uuid': 'tenant_uuid',
            'userfield': 'user_userfield, toto',
        }
        lines = [{'id': 12, 'users': [user], 'extensions': []}]
        confd = confd_mock(lines)
        channame = 'sip/something-suffix'

        result = find_participant(confd, channame)

        assert_that(
            result,
            has_entries(
                uuid='user_uuid',
                tenant_uuid='tenant_uuid',
                line_id=12,
                tags=['user_userfield', 'toto'],
            ),
        )

# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging
import requests.exceptions
from xivo.asterisk.protocol_interface import protocol_interface_from_channel
from xivo.asterisk.protocol_interface import InvalidChannelError
from wazo_confd_client import Client as ConfdClient
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ParticipantInfo(NamedTuple):
    uuid: str
    tenant_uuid: str
    line_id: int | None
    tags: list[str]
    main_extension: str | None


def get_tags(field: str | None) -> list[str]:
    return (
        [tag.strip() for tag in field.split(',')]
        if field
        else []
    )


def find_participant_by_uuid(confd, user_uuid: str) -> ParticipantInfo | None:
    try:
        user = confd.users.get(user_uuid)
    except requests.exceptions.HTTPError as ex:
        logger.exception("Error retrieving user(user_uuid=%s) from confd", user_uuid)
        return None

    if not user:
        return None

    tags = get_tags(user['userfield'])
    logger.debug(
        'Found participant with user uuid %s, tenant uuid %s',
        user['uuid'],
        user['tenant_uuid'],
    )
    # NOTE(charles): this replicates the behavior of CallLogsGenerator._update_call_participants_with_their_tags
    # of defaulting to first line of user, though this might be erroneous
    line = user['lines'] and user['lines'][0]
    logger.debug("user(user_uuid=%s) has first line: %s", user_uuid, line)
    main_extension = line and ('extensions' in line or None) and (line['extensions'] or None) and line['extensions'][0]
    return ParticipantInfo(
        uuid=user['uuid'],
        tenant_uuid=user['tenant_uuid'],
        line_id=line['id'],
        tags=tags,
        main_extension=main_extension
    )


def find_participant(confd: ConfdClient, channame: str) -> ParticipantInfo | None:
    """
    find and fetch participant information from confd, 
    using channel name or user_uuid as available
    """
    line = None
    main_extension = None
    try:
        protocol, line_name = protocol_interface_from_channel(channame)
    except InvalidChannelError:
        return None

    if protocol == 'Local':
        logger.debug('Ignoring participant %s', channame)
        return None

    logger.debug(
        'Looking up participant with protocol %s and line name "%s"',
        protocol,
        line_name,
    )
    lines = confd.lines.list(name=line_name, recurse=True)['items']
    if not lines:
        return None

    line = lines[0]
    logger.debug('Found participant line id %s', line['id'])
    users = line['users']
    if not users:
        return None

    user_uuid = users[0]['uuid']
        
    extensions = line['extensions']
    if extensions:
        main_extension = extensions[0]

        logger.debug(
            'Found main internal extension %s@%s',
            main_extension['exten'],
            main_extension['context'],
        )

    try:
        user = confd.users.get(user_uuid)
    except requests.exceptions.HTTPError as ex:
        logger.exception("Error retrieving user(user_uuid=%s) from confd", user_uuid)
        return None

    tags = get_tags(user['userfield'])
    logger.debug(
        'Found participant with user uuid %s, tenant uuid %s',
        user['uuid'],
        user['tenant_uuid'],
    )

    return ParticipantInfo(
        uuid=user['uuid'],
        tenant_uuid=user['tenant_uuid'],
        line_id=line and line['id'],
        tags=tags,
        main_extension=main_extension
    )

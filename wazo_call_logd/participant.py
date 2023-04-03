# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging
import requests.exceptions
from xivo.asterisk.protocol_interface import (
    protocol_interface_from_channel,
    InvalidChannelError,
)
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
    return [tag.strip() for tag in field.split(',')] if field else []


def find_participant_by_uuid(
    confd: ConfdClient, user_uuid: str
) -> ParticipantInfo | None:
    try:
        user = confd.users.get(user_uuid)
    except requests.exceptions.HTTPError as ex:
        logger.error(
            "Error retrieving user(user_uuid=%s) from confd: %s", user_uuid, str(ex)
        )
        return None

    tags = get_tags(user['userfield'])
    logger.debug(
        'Found participant with user uuid %s, tenant uuid %s',
        user['uuid'],
        user['tenant_uuid'],
    )

    main_extension = None
    main_line_id = None
    if user['lines']:
        # NOTE(charles): without authoritative information on the line actually used, the main line of the user is provided
        main_line = user['lines'][0]
        main_line_id = main_line['id']
        logger.debug("user(user_uuid=%s) has main line: %s", user_uuid, main_line)
        if main_line["extensions"]:
            main_extension = main_line['extensions'][0]

    return ParticipantInfo(
        uuid=user['uuid'],
        tenant_uuid=user['tenant_uuid'],
        line_id=main_line_id,
        tags=tags,
        main_extension=main_extension,
    )


def find_participant(confd: ConfdClient, channame: str) -> ParticipantInfo | None:
    """
    find and fetch participant information from confd,
    using the channel name
    """
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
    main_extension = None
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
        logger.error(
            "Error retrieving user(user_uuid=%s) from confd: %s", user_uuid, str(ex)
        )
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
        line_id=line['id'],
        tags=tags,
        main_extension=main_extension,
    )

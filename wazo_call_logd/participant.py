# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from xivo.asterisk.protocol_interface import protocol_interface_from_channel
from xivo.asterisk.protocol_interface import InvalidChannelError

logger = logging.getLogger(__name__)


def find_participant(confd, channame):
    # TODO PJSIP clean after migration
    channame = channame.replace('PJSIP', 'SIP')

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
        return

    line = lines[0]
    logger.debug('Found participant line id %s', line['id'])
    users = line['users']
    if not users:
        return

    user = confd.users.get(users[0]['uuid'])
    tags = (
        [tag.strip() for tag in user['userfield'].split(',')]
        if user['userfield']
        else []
    )
    logger.debug(
        'Found participant user uuid %s tenant uuid %s',
        user['uuid'],
        user['tenant_uuid'],
    )

    extensions = line['extensions']
    if extensions:
        main_extension = extensions[0]

        logger.debug(
            'Found main internal extension %s@%s',
            main_extension['exten'],
            main_extension['context'],
        )
    else:
        main_extension = None

    return {
        'uuid': user['uuid'],
        'tenant_uuid': user['tenant_uuid'],
        'line_id': line['id'],
        'tags': tags,
        'main_extension': main_extension,
    }

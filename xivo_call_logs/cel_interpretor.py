# -*- coding: utf-8 -*-

# Copyright (C) 2013-2017 The Wazo Authors  (see the AUTHORS file)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from xivo.asterisk.line_identity import identity_from_channel
from xivo.asterisk.protocol_interface import protocol_interface_from_channel
from xivo.asterisk.protocol_interface import InvalidChannelError
from xivo_dao.resources.cel.event_type import CELEventType
from xivo_dao.alchemy.call_log_participant import CallLogParticipant

logger = logging.getLogger(__name__)


def find_participant(confd, channame, role):
    try:
        protocol, line_name = protocol_interface_from_channel(channame)
    except InvalidChannelError:
        return None

    logger.debug('Looking up participant with protocol %s and line name "%s"', protocol, line_name)
    lines = confd.lines.list(name=line_name)['items']
    if lines:
        line = lines[0]
        logger.debug('Found participant line id %s', line['id'])
        users = line['users']
        if users:
            user = confd.users.get(users[0]['uuid'])
            tags = [tag.strip() for tag in user['userfield'].split(',')] if user['userfield'] else []
            logger.debug('Found participant user uuid %s', user['uuid'])
            participant = CallLogParticipant(role=role,
                                             user_uuid=user['uuid'],
                                             line_id=line['id'],
                                             tags=tags)
            return participant
    return None


class DispatchCELInterpretor(object):

    def __init__(self, caller_cel_interpretor, callee_cel_interpretor):
        self.caller_cel_interpretor = caller_cel_interpretor
        self.callee_cel_interpretor = callee_cel_interpretor

    def interpret_cels(self, cels, call_log):
        caller_cels, callee_cels = self.split_caller_callee_cels(cels)
        call_log = self.caller_cel_interpretor.interpret_cels(caller_cels, call_log)
        call_log = self.callee_cel_interpretor.interpret_cels(callee_cels, call_log)
        return call_log

    def split_caller_callee_cels(self, cels):
        uniqueids = [cel.uniqueid for cel in cels if cel.eventtype == CELEventType.chan_start]
        caller_uniqueid = uniqueids[0] if len(uniqueids) > 0 else None
        callee_uniqueid = uniqueids[1] if len(uniqueids) > 1 else None

        caller_cels = [cel for cel in cels if cel.uniqueid == caller_uniqueid]
        callee_cels = [cel for cel in cels if cel.uniqueid == callee_uniqueid]

        return (caller_cels, callee_cels)

    def can_interpret(self, cels):
        del cels
        return True


class AbstractCELInterpretor(object):

    eventtype_map = {}

    def interpret_cels(self, cels, call_log):
        for cel in cels:
            call_log = self.interpret_cel(cel, call_log)
        return call_log

    def interpret_cel(self, cel, call):
        eventtype = cel.eventtype
        if eventtype in self.eventtype_map:
            interpret_function = self.eventtype_map[eventtype]
            return interpret_function(cel, call)
        else:
            return call


class CallerCELInterpretor(AbstractCELInterpretor):

    def __init__(self, confd):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.app_start: self.interpret_app_start,
            CELEventType.answer: self.interpret_answer,
            CELEventType.bridge_start: self.interpret_bridge_start_or_enter,
            CELEventType.bridge_end: self.interpret_bridge_end_or_exit,
            CELEventType.bridge_enter: self.interpret_bridge_start_or_enter,
            CELEventType.bridge_exit: self.interpret_bridge_end_or_exit,
            CELEventType.xivo_from_s: self.interpret_xivo_from_s,
            CELEventType.xivo_incall: self.interpret_xivo_incall,
            CELEventType.xivo_outcall: self.interpret_xivo_outcall,
        }
        self._confd = confd

    def interpret_chan_start(self, cel, call):
        call.date = cel.eventtime
        call.source_name = cel.cid_name
        call.source_exten = cel.cid_num
        call.destination_exten = cel.exten if cel.exten != 's' else ''
        call.source_line_identity = identity_from_channel(cel.channame)
        participant = find_participant(self._confd, cel.channame, role='source')
        if participant:
            call.participants.append(participant)

        return call

    def interpret_app_start(self, cel, call):
        call.user_field = cel.userfield
        if cel.cid_name != '' and cel.cid_num != '':
            call.source_name = cel.cid_name
            call.source_exten = cel.cid_num

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_name

        return call

    def interpret_bridge_start_or_enter(self, cel, call):
        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = cel.cid_num

        call.communication_start = cel.eventtime
        call.answered = True

        return call

    def interpret_bridge_end_or_exit(self, cel, call):
        call.communication_end = cel.eventtime

        return call

    def interpret_xivo_from_s(self, cel, call):
        call.destination_exten = cel.exten

        return call

    def interpret_xivo_incall(self, cel, call):
        call.direction = 'inbound'

        return call

    def interpret_xivo_outcall(self, cel, call):
        call.direction = 'outbound'

        return call


class CalleeCELInterpretor(AbstractCELInterpretor):
    def __init__(self, confd):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
        }
        self._confd = confd

    def interpret_chan_start(self, cel, call):
        call.destination_line_identity = identity_from_channel(cel.channame)
        participant = find_participant(self._confd, cel.channame, role='destination')
        if participant:
            call.participants.append(participant)

        return call


class LocalOriginateCELInterpretor(object):
    def __init__(self, confd):
        self._confd = confd

    def interpret_cels(self, cels, call):
        uniqueids = [cel.uniqueid for cel in cels if cel.eventtype == 'CHAN_START']
        try:
            local_channel1, local_channel2, source_channel = starting_channels = uniqueids[:3]
        except ValueError:  # in case a CHAN_START is missing...
            return call

        try:
            local_channel1_start = next(cel for cel in cels if cel.uniqueid == local_channel1 and cel.eventtype == 'CHAN_START')
            source_channel_answer = next(cel for cel in cels if cel.uniqueid == source_channel and cel.eventtype == 'ANSWER')
            local_channel2_answer = next(cel for cel in cels if cel.uniqueid == local_channel2 and cel.eventtype == 'ANSWER')
        except StopIteration:
            return call

        call.date = local_channel1_start.eventtime
        call.source_name = source_channel_answer.cid_name
        call.source_exten = source_channel_answer.cid_num
        call.source_line_identity = identity_from_channel(source_channel_answer.channame)
        participant = find_participant(self._confd, source_channel_answer.channame, role='source')
        if participant:
            call.participants.append(participant)
        call.destination_exten = local_channel2_answer.cid_num

        local_channel1_app_start = next((cel for cel in cels if cel.uniqueid == local_channel1 and cel.eventtype == 'APP_START'), None)
        if local_channel1_app_start:
            call.user_field = local_channel1_app_start.userfield

        other_channels_start = [cel for cel in cels if cel.uniqueid not in starting_channels and cel.eventtype == 'CHAN_START']
        non_local_other_channels = [cel.uniqueid for cel in other_channels_start if not cel.channame.lower().startswith('local/')]
        other_channels_bridge_enter = [cel for cel in cels if cel.uniqueid in non_local_other_channels and cel.eventtype == 'BRIDGE_ENTER']
        destination_channel = other_channels_bridge_enter[-1].uniqueid if other_channels_bridge_enter else None

        if destination_channel:
            try:
                # in outgoing calls, destination ANSWER event has more callerid information than START event
                destination_channel_answer = next(cel for cel in cels if cel.uniqueid == destination_channel and cel.eventtype == 'ANSWER')
                # take the last bridge enter/exit to skip local channel optimization
                destination_channel_bridge_enter = next(reversed([cel for cel in cels if cel.uniqueid == destination_channel and cel.eventtype == 'BRIDGE_ENTER']))
                destination_channel_bridge_exit = next(reversed([cel for cel in cels if cel.uniqueid == destination_channel and cel.eventtype == 'BRIDGE_EXIT']))
            except StopIteration:
                return call

            call.destination_name = destination_channel_answer.cid_name
            call.destination_exten = destination_channel_answer.cid_num
            call.destination_line_identity = identity_from_channel(destination_channel_answer.channame)
            participant = find_participant(self._confd, cel.channame, role='destination')
            if participant:
                call.participants.append(participant)
            call.communication_start = destination_channel_bridge_enter.eventtime
            call.communication_end = destination_channel_bridge_exit.eventtime
            call.answered = True

        is_incall = any([True for cel in cels if cel.eventtype == 'XIVO_INCALL'])
        is_outcall = any([True for cel in cels if cel.eventtype == 'XIVO_OUTCALL'])
        if is_incall:
            call.direction = 'incall'
        if is_outcall:
            call.direction = 'outcall'

        return call

    @classmethod
    def can_interpret(cls, cels):
        return (cls.three_channels_minimum(cels) and
                cls.first_two_channels_are_local(cels) and
                cls.first_channel_is_answered_before_any_other_operation(cels))

    @classmethod
    def three_channels_minimum(cls, cels):
        channels = set(cel.uniqueid for cel in cels)
        return len(channels) >= 3

    @classmethod
    def first_two_channels_are_local(cls, cels):
        names = [cel.channame for cel in cels if cel.eventtype == 'CHAN_START']
        return (len(names) >= 2 and
                names[0].lower().startswith('local/') and
                names[1].lower().startswith('local/'))

    @classmethod
    def first_channel_is_answered_before_any_other_operation(cls, cels):
        first_channel_cels = [cel for cel in cels if cel.uniqueid == cels[0].uniqueid]
        return (len(first_channel_cels) >= 2 and
                first_channel_cels[0].eventtype == 'CHAN_START' and
                first_channel_cels[1].eventtype == 'ANSWER')

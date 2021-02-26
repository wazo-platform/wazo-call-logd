# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re
import logging

from xivo.asterisk.line_identity import identity_from_channel
from xivo.asterisk.protocol_interface import protocol_interface_from_channel
from xivo.asterisk.protocol_interface import InvalidChannelError
from xivo_dao.alchemy.call_log_participant import CallLogParticipant

from .database.cel_event_type import CELEventType
from .database.models import Recording


logger = logging.getLogger(__name__)

EXTRA_USER_FWD_REGEX = r'^.*NUM: *(.*?) *, *CONTEXT: *(.*?) *, *NAME: *(.*?) *(?:,|"})'


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


def extract_mixmonitor_extra(extra):
    if not extra:
        logger.debug('missing mixmonitor extra')
        return

    try:
        extra = json.loads(extra)
    except json.decoder.JSONDecodeError:
        logger.debug('invalid mixmonitor extra: "%s"', extra)
        return

    return extra


def is_valid_mixmonitor_start_extra(extra):
    if not extra:
        return False

    if not extra.get('mixmonitor_id', None):
        logger.debug('"mixmonitor_id" not found or invalid in mixmonitor event')
        return False

    if not extra.get('filename', None):
        logger.debug('"filename" not found or invalid in mixmonitor event')
        return False

    return True


def is_valid_mixmonitor_stop_extra(extra):
    if not extra:
        return False

    if not extra.get('mixmonitor_id', None):
        logger.debug('"mixmonitor_id" not found or invalid in mixmonitor event')
        return False

    return True


class DispatchCELInterpretor:
    def __init__(self, caller_cel_interpretor, callee_cel_interpretor):
        self.caller_cel_interpretor = caller_cel_interpretor
        self.callee_cel_interpretor = callee_cel_interpretor

    def interpret_cels(self, cels, call_log):
        caller_cels, callee_cels = self.split_caller_callee_cels(cels)
        call_log = self.caller_cel_interpretor.interpret_cels(caller_cels, call_log)
        call_log = self.callee_cel_interpretor.interpret_cels(callee_cels, call_log)
        return call_log

    def split_caller_callee_cels(self, cels):
        uniqueids = [
            cel.uniqueid for cel in cels if cel.eventtype == CELEventType.chan_start
        ]
        caller_uniqueid = uniqueids[0] if len(uniqueids) > 0 else None
        callee_uniqueids = uniqueids[1:]

        caller_cels = [cel for cel in cels if cel.uniqueid == caller_uniqueid]
        callee_cels = [cel for cel in cels if cel.uniqueid in callee_uniqueids]

        return (caller_cels, callee_cels)

    def can_interpret(self, cels):
        del cels
        return True


class AbstractCELInterpretor:

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
            CELEventType.chan_end: self.interpret_chan_end,
            CELEventType.app_start: self.interpret_app_start,
            CELEventType.answer: self.interpret_answer,
            CELEventType.bridge_start: self.interpret_bridge_start_or_enter,
            CELEventType.bridge_enter: self.interpret_bridge_start_or_enter,
            CELEventType.mixmonitor_start: self.interpret_mixmonitor_start,
            CELEventType.mixmonitor_stop: self.interpret_mixmonitor_stop,
            CELEventType.xivo_from_s: self.interpret_xivo_from_s,
            CELEventType.xivo_incall: self.interpret_xivo_incall,
            CELEventType.xivo_outcall: self.interpret_xivo_outcall,
            CELEventType.xivo_user_fwd: self.interpret_xivo_user_fwd,
        }
        self._confd = confd

    def interpret_chan_start(self, cel, call):
        call.date = cel.eventtime
        call.source_name = cel.cid_name
        call.source_exten = cel.cid_num
        call.requested_exten = cel.exten if cel.exten != 's' else ''
        call.requested_context = cel.context
        call.destination_exten = cel.exten if cel.exten != 's' else ''
        call.source_line_identity = identity_from_channel(cel.channame)
        participant = find_participant(self._confd, cel.channame)
        if participant:
            call.participants.append(
                CallLogParticipant(
                    role='source',
                    user_uuid=participant['uuid'],
                    line_id=participant['line_id'],
                    tags=participant['tags'],
                )
            )
            call.set_tenant_uuid(participant['tenant_uuid'])

            extension = participant['main_extension']
            if extension:
                call.source_internal_exten = extension['exten']
                call.source_internal_context = extension['context']

        return call

    def interpret_chan_end(self, cel, call):
        call.date_end = cel.eventtime
        for recording in call.recordings:
            if not recording.end_time:
                recording.end_time = cel.eventtime
        return call

    def interpret_app_start(self, cel, call):
        call.user_field = cel.userfield
        if cel.cid_name != '':
            call.source_name = cel.cid_name
        if cel.cid_num != '':
            call.source_exten = cel.cid_num

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_num
        if not call.requested_exten:
            call.requested_exten = cel.cid_num

        return call

    def interpret_bridge_start_or_enter(self, cel, call):
        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = cel.cid_num

        call.date_answer = cel.eventtime

        return call

    def interpret_mixmonitor_start(self, cel, call):
        extra = extract_mixmonitor_extra(cel.extra)
        if not is_valid_mixmonitor_start_extra(extra):
            return call

        recording = Recording(
            start_time=cel.eventtime,
            path=extra['filename'],
            mixmonitor_id=extra['mixmonitor_id'],
        )
        call.recordings.append(recording)
        return call

    def interpret_mixmonitor_stop(self, cel, call):
        extra = extract_mixmonitor_extra(cel.extra)
        if not is_valid_mixmonitor_stop_extra(extra):
            return call

        for recording in call.recordings:
            if recording.mixmonitor_id == extra['mixmonitor_id']:
                recording.end_time = cel.eventtime
        return call

    def interpret_xivo_from_s(self, cel, call):
        call.requested_exten = cel.exten
        call.requested_context = cel.context
        call.destination_exten = cel.exten
        return call

    def interpret_xivo_incall(self, cel, call):
        call.direction = 'inbound'

        return call

    def interpret_xivo_outcall(self, cel, call):
        call.direction = 'outbound'

        return call

    def interpret_xivo_user_fwd(self, cel, call):
        if call.interpret_caller_xivo_user_fwd:
            match = re.match(EXTRA_USER_FWD_REGEX, cel.extra)
            if match:
                call.requested_internal_exten = match.group(1)
                call.requested_internal_context = match.group(2)
                call.requested_name = match.group(3)
            call.interpret_caller_xivo_user_fwd = False
        return call


class CalleeCELInterpretor(AbstractCELInterpretor):
    def __init__(self, confd):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.chan_end: self.interpret_chan_end,
            CELEventType.bridge_enter: self.interpret_bridge_enter,
            CELEventType.bridge_start: self.interpret_bridge_enter,
            CELEventType.mixmonitor_start: self.interpret_mixmonitor_start,
            CELEventType.mixmonitor_stop: self.interpret_mixmonitor_stop,
        }
        self._confd = confd

    def interpret_chan_start(self, cel, call):
        call.destination_line_identity = identity_from_channel(cel.channame)

        if call.direction == 'outbound':
            call.destination_name = ''
            call.requested_name = ''
        else:
            call.destination_exten = cel.cid_num
            call.destination_name = cel.cid_name
            if not call.requested_name:
                call.requested_name = cel.cid_name

        participant = find_participant(self._confd, cel.channame)
        if participant:
            participant_model = CallLogParticipant(
                role='destination',
                user_uuid=participant['uuid'],
                line_id=participant['line_id'],
                tags=participant['tags'],
            )
            call.participants.append(participant_model)
            call.participants_by_channame[cel.channame] = participant_model
            call.set_tenant_uuid(participant['tenant_uuid'])

            extension = participant['main_extension']
            if extension:
                call.destination_internal_exten = extension['exten']
                call.destination_internal_context = extension['context']

                if not call.requested_internal_exten:
                    call.requested_internal_exten = extension['exten']
                    call.requested_internal_context = extension['context']

        return call

    def interpret_chan_end(self, cel, call):
        for recording in call.recordings:
            if not recording.end_time:
                recording.end_time = cel.eventtime
        return call

    def interpret_bridge_enter(self, cel, call):
        if call.interpret_callee_bridge_enter:
            if cel.cid_num and cel.cid_num != 's':
                call.destination_exten = cel.cid_num
            call.destination_name = cel.cid_name
            participant = call.participants_by_channame.get(cel.channame)
            if participant:
                participant.answered = True

            call.interpret_callee_bridge_enter = False
        return call

    def interpret_mixmonitor_start(self, cel, call):
        extra = extract_mixmonitor_extra(cel.extra)
        if not is_valid_mixmonitor_start_extra(extra):
            return call

        recording = Recording(
            start_time=cel.eventtime,
            path=extra['filename'],
            mixmonitor_id=extra['mixmonitor_id'],
        )
        call.recordings.append(recording)
        return call

    def interpret_mixmonitor_stop(self, cel, call):
        extra = extract_mixmonitor_extra(cel.extra)
        if not is_valid_mixmonitor_stop_extra(extra):
            return call

        for recording in call.recordings:
            if recording.mixmonitor_id == extra['mixmonitor_id']:
                recording.end_time = cel.eventtime
        return call


class LocalOriginateCELInterpretor:
    def __init__(self, confd):
        self._confd = confd

    def interpret_cels(self, cels, call):
        uniqueids = [cel.uniqueid for cel in cels if cel.eventtype == 'CHAN_START']
        try:
            (
                local_channel1,
                local_channel2,
                source_channel,
            ) = starting_channels = uniqueids[:3]
        except ValueError:  # in case a CHAN_START is missing...
            return call

        try:
            local_channel1_start = next(
                cel
                for cel in cels
                if cel.uniqueid == local_channel1 and cel.eventtype == 'CHAN_START'
            )
            source_channel_answer = next(
                cel
                for cel in cels
                if cel.uniqueid == source_channel and cel.eventtype == 'ANSWER'
            )
            source_channel_end = next(
                cel
                for cel in cels
                if cel.uniqueid == source_channel and cel.eventtype == 'CHAN_END'
            )
            local_channel2_answer = next(
                cel
                for cel in cels
                if cel.uniqueid == local_channel2 and cel.eventtype == 'ANSWER'
            )
        except StopIteration:
            return call

        call.date = local_channel1_start.eventtime
        call.date_end = source_channel_end.eventtime
        call.source_name = source_channel_answer.cid_name
        call.source_exten = source_channel_answer.cid_num
        call.source_line_identity = identity_from_channel(
            source_channel_answer.channame
        )
        participant = find_participant(self._confd, source_channel_answer.channame)
        if participant:
            call.participants.append(
                CallLogParticipant(
                    role='source',
                    user_uuid=participant['uuid'],
                    line_id=participant['line_id'],
                    tags=participant['tags'],
                )
            )
            call.set_tenant_uuid(participant['tenant_uuid'])

        call.destination_exten = local_channel2_answer.cid_num

        local_channel1_app_start = next(
            (
                cel
                for cel in cels
                if cel.uniqueid == local_channel1 and cel.eventtype == 'APP_START'
            ),
            None,
        )
        if local_channel1_app_start:
            call.user_field = local_channel1_app_start.userfield

        other_channels_start = [
            cel
            for cel in cels
            if cel.uniqueid not in starting_channels and cel.eventtype == 'CHAN_START'
        ]
        non_local_other_channels = [
            cel.uniqueid
            for cel in other_channels_start
            if not cel.channame.lower().startswith('local/')
        ]
        other_channels_bridge_enter = [
            cel
            for cel in cels
            if cel.uniqueid in non_local_other_channels
            and cel.eventtype == 'BRIDGE_ENTER'
        ]
        destination_channel = (
            other_channels_bridge_enter[-1].uniqueid
            if other_channels_bridge_enter
            else None
        )

        if destination_channel:
            try:
                # in outgoing calls, destination ANSWER event has more callerid information than START event
                destination_channel_answer = next(
                    cel
                    for cel in cels
                    if cel.uniqueid == destination_channel and cel.eventtype == 'ANSWER'
                )
                # take the last bridge enter/exit to skip local channel optimization
                destination_channel_bridge_enter = next(
                    reversed(
                        [
                            cel
                            for cel in cels
                            if cel.uniqueid == destination_channel
                            and cel.eventtype == 'BRIDGE_ENTER'
                        ]
                    )
                )
            except StopIteration:
                return call

            call.destination_name = destination_channel_answer.cid_name
            call.destination_exten = destination_channel_answer.cid_num
            call.destination_line_identity = identity_from_channel(
                destination_channel_answer.channame
            )
            participant = find_participant(
                self._confd, destination_channel_answer.channame
            )
            if participant:
                call.participants.append(
                    CallLogParticipant(
                        role='destination',
                        user_uuid=participant['uuid'],
                        line_id=participant['line_id'],
                        tags=participant['tags'],
                    )
                )
                call.set_tenant_uuid(participant['tenant_uuid'])
            call.date_answer = destination_channel_bridge_enter.eventtime

        is_incall = any([True for cel in cels if cel.eventtype == 'XIVO_INCALL'])
        is_outcall = any([True for cel in cels if cel.eventtype == 'XIVO_OUTCALL'])
        if is_incall:
            call.direction = 'inbound'
        if is_outcall:
            call.direction = 'outbound'

        return call

    @classmethod
    def can_interpret(cls, cels):
        return (
            cls.three_channels_minimum(cels)
            and cls.first_two_channels_are_local(cels)
            and cls.first_channel_is_answered_before_any_other_operation(cels)
        )

    @classmethod
    def three_channels_minimum(cls, cels):
        channels = set(cel.uniqueid for cel in cels)
        return len(channels) >= 3

    @classmethod
    def first_two_channels_are_local(cls, cels):
        names = [cel.channame for cel in cels if cel.eventtype == 'CHAN_START']
        return (
            len(names) >= 2
            and names[0].lower().startswith('local/')
            and names[1].lower().startswith('local/')
        )

    @classmethod
    def first_channel_is_answered_before_any_other_operation(cls, cels):
        first_channel_cels = [cel for cel in cels if cel.uniqueid == cels[0].uniqueid]
        return (
            len(first_channel_cels) >= 2
            and first_channel_cels[0].eventtype == 'CHAN_START'
            and first_channel_cels[1].eventtype == 'ANSWER'
        )

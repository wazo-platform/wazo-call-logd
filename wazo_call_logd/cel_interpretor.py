# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re
import logging

from xivo.asterisk.line_identity import identity_from_channel

from .database.cel_event_type import CELEventType
from .database.models import CallLogParticipant, Destination, Recording


logger = logging.getLogger(__name__)

EXTRA_USER_FWD_REGEX = r'^.*NUM: *(.*?) *, *CONTEXT: *(.*?) *, *NAME: *(.*?) *(?:,|"})'
WAIT_FOR_MOBILE_REGEX = re.compile(r'^Local/(\S+)@wazo_wait_for_registration-\S+;2$')
MATCHING_MOBILE_PEER_REGEX = re.compile(r'^PJSIP/(\S+)-\S+$')
MEETING_EXTENSION_REGEX = re.compile(r'^wazo-meeting-.*$')


def extract_cel_extra(extra):
    if not extra:
        logger.debug('missing CEL extra')
        return

    try:
        extra = json.loads(extra)
    except json.decoder.JSONDecodeError:
        logger.debug('invalid CEL extra: "%s"', extra)
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
    def __init__(self):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.chan_end: self.interpret_chan_end,
            CELEventType.app_start: self.interpret_app_start,
            CELEventType.answer: self.interpret_answer,
            CELEventType.bridge_start: self.interpret_bridge_start_or_enter,
            CELEventType.bridge_enter: self.interpret_bridge_start_or_enter,
            CELEventType.mixmonitor_start: self.interpret_mixmonitor_start,
            CELEventType.mixmonitor_stop: self.interpret_mixmonitor_stop,
            # CELGenUserEvent
            CELEventType.xivo_from_s: self.interpret_xivo_from_s,
            CELEventType.xivo_incall: self.interpret_xivo_incall,
            CELEventType.xivo_outcall: self.interpret_xivo_outcall,
            CELEventType.xivo_user_fwd: self.interpret_xivo_user_fwd,
            CELEventType.wazo_meeting_name: self.interpret_wazo_meeting_name,
            CELEventType.wazo_conference: self.interpret_wazo_conference,
            CELEventType.wazo_user_missed_call: self.interpret_wazo_user_missed_call,
            CELEventType.wazo_call_log_destination: self.interpret_wazo_call_log_destination,
        }

    def interpret_chan_start(self, cel, call):
        call.date = cel.eventtime
        call.source_name = cel.cid_name
        call.source_internal_name = cel.cid_name
        call.source_exten = call.extension_filter.filter(cel.cid_num)
        call.requested_exten = call.extension_filter.filter(cel.exten)
        call.requested_context = cel.context
        call.destination_exten = call.extension_filter.filter(cel.exten)
        call.source_line_identity = identity_from_channel(cel.channame)
        call.raw_participants[cel.channame].update(role='source')

        return call

    def interpret_chan_end(self, cel, call):
        call.date_end = cel.eventtime
        for recording in call.recordings:
            if not recording.end_time:
                recording.end_time = cel.eventtime

        # Remove unwanted extensions
        call.extension_filter.filter_call(call)

        return call

    def interpret_app_start(self, cel, call):
        call.user_field = cel.userfield
        if cel.cid_name != '':
            call.source_name = cel.cid_name
        if cel.cid_num != '':
            call.source_exten = call.extension_filter.filter(cel.cid_num)

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_num
        if not call.requested_exten:
            call.requested_exten = call.extension_filter.filter(cel.cid_num)

        return call

    def interpret_bridge_start_or_enter(self, cel, call):
        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = call.extension_filter.filter(cel.cid_num)

        call.date_answer = cel.eventtime

        return call

    def interpret_mixmonitor_start(self, cel, call):
        extra = extract_cel_extra(cel.extra)
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
        extra = extract_cel_extra(cel.extra)
        if not is_valid_mixmonitor_stop_extra(extra):
            return call

        for recording in call.recordings:
            if recording.mixmonitor_id == extra['mixmonitor_id']:
                recording.end_time = cel.eventtime
        return call

    def interpret_xivo_from_s(self, cel, call):
        call.requested_exten = call.extension_filter.filter(cel.exten)
        call.requested_context = cel.context
        call.destination_exten = call.extension_filter.filter(cel.exten)
        return call

    def interpret_xivo_incall(self, cel, call):
        call.direction = 'inbound'
        extra = extract_cel_extra(cel.extra)
        if not extra:
            return call

        call.set_tenant_uuid(extra['extra'])
        return call

    def interpret_xivo_outcall(self, cel, call):
        call.direction = 'outbound'

        return call

    def interpret_xivo_user_fwd(self, cel, call):
        if call.interpret_caller_xivo_user_fwd:
            match = re.match(EXTRA_USER_FWD_REGEX, cel.extra)
            if match:
                call.requested_internal_exten = call.extension_filter.filter(
                    match.group(1)
                )
                call.requested_internal_context = match.group(2)
                call.requested_name = match.group(3)
            call.interpret_caller_xivo_user_fwd = False
        return call

    def interpret_wazo_conference(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            return

        _, name = extra['extra'].split('NAME: ', 1)
        call.destination_name = name
        return call

    def interpret_wazo_meeting_name(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            return
        call.destination_name = extra['extra']
        if MEETING_EXTENSION_REGEX.match(call.destination_exten):
            call.extension_filter.add_exten(call.destination_exten)
            # Don't call filter.filter_call() yet, to avoid empty exten during interpret.
            # Let interpret_chan_end do it instead.

        return call

    def interpret_wazo_user_missed_call(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            return

        extra_tokens = extra['extra'].split(',')
        wazo_tenant_uuid = extra_tokens[0].split(': ')[1]
        source_user_uuid = extra_tokens[1].split(': ')[1]
        destination_user_uuid = extra_tokens[2].split(': ')[1]
        destination_exten = extra_tokens[3].split(': ')[1]
        source_name = extra_tokens[4].split(': ')[1]
        destination_name = extra_tokens[5].split(': ')[1]

        if source_user_uuid:
            source_participant = CallLogParticipant(
                role='source',
                user_uuid=source_user_uuid,
                answered=False,
            )
            call.participants.append(source_participant)
            call.source_user_uuid = source_user_uuid
        if destination_user_uuid:
            destination_participant = CallLogParticipant(
                role='destination',
                user_uuid=destination_user_uuid,
                answered=False,
            )
            call.participants.append(destination_participant)
            call.destination_user_uuid = destination_user_uuid

        call.set_tenant_uuid(wazo_tenant_uuid)
        call.destination_exten = destination_exten
        call.source_name = source_name
        call.destination_name = destination_name
        call.source_exten = cel.cid_num
        call.source_line_identity = identity_from_channel(cel.channame)
        return call

    def interpret_wazo_call_log_destination(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            return

        extra_tokens = extra['extra'].split(',')
        extra_dict = dict()
        for token in extra_tokens:
            key = token.split(': ')[0].strip()
            value = token.split(': ')[1].strip()
            extra_dict[key] = value

        if 'type' not in extra_dict.keys():
            logger.debug('required destination type is not found.')
            return

        if extra_dict['type'] == 'conference':
            destination_details = [
                Destination(
                    destination_details_key='type',
                    destination_details_value=extra_dict['type'],
                ),
                Destination(
                    destination_details_key='conference_id',
                    destination_details_value=extra_dict['id'],
                ),
            ]
            call.destination_details = destination_details
        elif extra_dict['type'] == 'user':
            destination_details = [
                Destination(
                    destination_details_key='type',
                    destination_details_value=extra_dict['type'],
                ),
                Destination(
                    destination_details_key='user_uuid',
                    destination_details_value=extra_dict['uuid'],
                ),
                Destination(
                    destination_details_key='user_name',
                    destination_details_value=extra_dict['name'],
                ),
            ]
            call.destination_details = destination_details
        elif extra_dict['type'] == 'meeting':
            destination_details = [
                Destination(
                    destination_details_key='type',
                    destination_details_value=extra_dict['type'],
                ),
                Destination(
                    destination_details_key='meeting_uuid',
                    destination_details_value=extra_dict['uuid'],
                ),
                Destination(
                    destination_details_key='meeting_name',
                    destination_details_value=extra_dict['name'],
                ),
            ]
            call.destination_details = destination_details
        return call


class CalleeCELInterpretor(AbstractCELInterpretor):
    def __init__(self):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.chan_end: self.interpret_chan_end,
            CELEventType.bridge_enter: self.interpret_bridge_enter,
            CELEventType.bridge_start: self.interpret_bridge_enter,
            CELEventType.mixmonitor_start: self.interpret_mixmonitor_start,
            CELEventType.mixmonitor_stop: self.interpret_mixmonitor_stop,
        }

    def interpret_chan_start(self, cel, call):
        call.destination_line_identity = identity_from_channel(cel.channame)
        call.caller_id_by_channels[cel.channame] = (cel.cid_name, cel.cid_num)

        if call.direction == 'outbound':
            call.destination_name = ''
            call.requested_name = ''
        else:
            matches = WAIT_FOR_MOBILE_REGEX.match(cel.channame)
            if matches:
                call.pending_wait_for_mobile_peers.add(matches.group(1))
            elif self._is_a_pending_wait_for_mobile_cel(cel, call):
                call.interpret_callee_bridge_enter = False
                call.destination_exten = cel.cid_num
                call.destination_name = cel.cid_name
                call.destination_internal_exten = cel.cid_num
                call.destination_internal_context = cel.context
            else:
                call.destination_exten = cel.cid_num
                call.destination_name = cel.cid_name
                if not call.requested_name:
                    call.requested_name = cel.cid_name

        call.raw_participants[cel.channame].update(role='destination')

        return call

    def _is_a_pending_wait_for_mobile_cel(self, cel, call):
        if not call.pending_wait_for_mobile_peers:
            return False

        matches = MATCHING_MOBILE_PEER_REGEX.match(cel.channame)
        if not matches:
            return False

        peer = matches.group(1)
        if peer in call.pending_wait_for_mobile_peers:
            call.pending_wait_for_mobile_peers.remove(peer)
            return True

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
            call.raw_participants[cel.channame].update(answered=True)

            call.interpret_callee_bridge_enter = False

        if cel.peer:
            # peer contains multiple entries during adhoc conferences
            for peer in cel.peer.split(','):
                if peer not in call.raw_participants:
                    continue
                call.raw_participants[peer].update(answered=True)
            cid_name, cid_number = call.caller_id_by_channels[cel.channame]
            if cid_name:
                call.destination_name = cid_name
                call.destination_internal_name = cid_name
            if cid_number:
                call.destination_exten = cid_number
                call.destination_internal_exten = cid_number

        return call

    def interpret_mixmonitor_start(self, cel, call):
        extra = extract_cel_extra(cel.extra)
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
        extra = extract_cel_extra(cel.extra)
        if not is_valid_mixmonitor_stop_extra(extra):
            return call

        for recording in call.recordings:
            if recording.mixmonitor_id == extra['mixmonitor_id']:
                recording.end_time = cel.eventtime
        return call


class LocalOriginateCELInterpretor:
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
        call.raw_participants[source_channel_answer.channame].update(role='source')

        call.destination_exten = local_channel2_answer.cid_num

        # Adding all recordings
        for cel in cels:
            if cel.eventtype != CELEventType.mixmonitor_start:
                continue
            extra = extract_cel_extra(cel.extra)
            if not is_valid_mixmonitor_start_extra(extra):
                return call

            recording = Recording(
                start_time=cel.eventtime,
                path=extra['filename'],
                mixmonitor_id=extra['mixmonitor_id'],
            )
            call.recordings.append(recording)

        # Check if any recordings have been stopped manually
        for cel in cels:
            if cel.eventtype != CELEventType.mixmonitor_stop:
                continue
            extra = extract_cel_extra(cel.extra)
            if not is_valid_mixmonitor_stop_extra(extra):
                return call

            for recording in call.recordings:
                if recording.mixmonitor_id == extra['mixmonitor_id']:
                    recording.end_time = cel.eventtime

        # End of recording when not stopped manually
        for recording in call.recordings:
            if not recording.end_time:
                recording.end_time = call.date_end

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
            call.raw_participants[destination_channel_answer.channame].update(
                role='destination'
            )
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

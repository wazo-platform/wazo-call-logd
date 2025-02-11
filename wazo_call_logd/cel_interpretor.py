# Copyright 2022-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import uuid
from datetime import datetime
from typing import Callable, TypedDict

import dateutil
from xivo.asterisk.line_identity import identity_from_channel
from xivo_dao.alchemy.cel import CEL

from .database.cel_event_type import CELEventType
from .database.models import Destination, Recording
from .exceptions import CELInterpretationError
from .raw_call_log import BridgeInfo, RawCallLog

logger = logging.getLogger(__name__)

EXTRA_USER_FWD_REGEX = r'^.*NUM: *(.*?) *, *CONTEXT: *(.*?) *, *NAME: *(.*?) *(?:,|"})'
WAIT_FOR_MOBILE_REGEX = re.compile(r'^Local/(\S+)@wazo_wait_for_registration-\S+;2$')
MATCHING_MOBILE_PEER_REGEX = re.compile(r'^PJSIP/(\S+)-\S+$')
MEETING_EXTENSION_REGEX = re.compile(r'^wazo-meeting-.*$')
KEY_PAIR_SEQ_REGEX = re.compile(r'\s*(\w+):\s*([^,:]+),?')
UUID_REGEX = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}'
)
# The recording path regex must be kept synced with CALL_RECORDING_FILENAME_TEMPLATE
# in wazo-calld and wazo-agid
RECORDING_PATH_REGEX = re.compile(
    rf'/var/lib/wazo/sounds/tenants/({UUID_REGEX.pattern})/monitor/({UUID_REGEX.pattern}).wav'
)


def default_interpretors() -> list[AbstractCELInterpretor]:
    return [
        LocalOriginateCELInterpretor(),
        DispatchCELInterpretor(
            CallerCELInterpretor(),
            CalleeCELInterpretor(),
        ),
    ]


def parse_key_pair_sequence(text: str) -> list[tuple[str, str]]:
    key_pairs = KEY_PAIR_SEQ_REGEX.findall(text)
    return key_pairs


def extract_cel_extra(extra: str | None) -> dict | None:
    if not extra:
        logger.debug('missing CEL extra')
        return

    try:
        extra = json.loads(extra)
    except json.decoder.JSONDecodeError:
        logger.debug('invalid CEL extra: %s', repr(extra))
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


def _extract_user_missed_call_variables(extra):
    extra_tokens = extra['extra'].split(',')
    wazo_tenant_uuid = extra_tokens[0].split(': ')[1]
    source_user_uuid = extra_tokens[1].split(': ')[1]
    destination_user_uuid = extra_tokens[2].split(': ')[1]
    destination_exten = extra_tokens[3].split(': ')[1]
    source_name = urllib.parse.unquote(extra_tokens[4].split(': ')[1])
    destination_name = urllib.parse.unquote(extra_tokens[5].split(': ')[1])

    return (
        wazo_tenant_uuid,
        source_user_uuid,
        destination_user_uuid,
        destination_exten,
        source_name,
        destination_name,
    )


def _extract_call_log_destination_variables(extra: dict) -> dict:
    extra_tokens = extra['extra'].split(',', 2)
    extra_dict = dict()
    for token in extra_tokens:
        key, value = token.split(': ', 1)
        extra_dict[key.strip()] = value.strip()

    return extra_dict


class OriginateAllLinesInfo(TypedDict):
    user_uuid: str
    tenant_uuid: str


def _extract_originate_all_lines_variables(extra: dict) -> OriginateAllLinesInfo | None:
    if 'extra' not in extra:
        logger.error('Missing expected \'extra\' key in CEL extra payload')
        return None
    raw_data = extra['extra']
    key_pairs = parse_key_pair_sequence(raw_data)
    if len(key_pairs) < 2:
        return None
    expected_keys = {'user_uuid', 'tenant_uuid'}
    unexpected_keys = {key for key, _ in key_pairs} - expected_keys
    info = {key: value for key, value in key_pairs if key in expected_keys}
    if unexpected_keys:
        logger.warning('Unexpected keys(%s) in event data payload', unexpected_keys)
    if info.keys() != expected_keys:
        return None
    return info


def _parse_wazo_originate_all_lines_extra(extra: str) -> OriginateAllLinesInfo:
    wrapper = extract_cel_extra(extra)
    if not wrapper:
        raise CELInterpretationError(
            event_name=CELEventType.wazo_originate_all_lines, raw_data=extra
        )
    info = _extract_originate_all_lines_variables(wrapper)
    if not info:
        raise CELInterpretationError(
            event_name=CELEventType.wazo_originate_all_lines, raw_data=extra
        )
    return info


def bridge_info(details: dict) -> BridgeInfo | None:
    expected_keys = {'bridge_id', 'bridge_technology'}
    if not (expected_keys <= set(details)):
        logger.error(
            "Missing expected bridge details: %s(missing %s)",
            details,
            (expected_keys - set(details)),
        )
        return None
    return BridgeInfo(id=details['bridge_id'], technology=details['bridge_technology'])


def parse_eventtime(eventtime: str | datetime) -> datetime:
    if isinstance(eventtime, datetime):
        return eventtime
    else:
        return dateutil.parser.isoparse(eventtime)


EventInterpretor = Callable[[CEL, RawCallLog], RawCallLog]


class AbstractCELInterpretor:
    eventtype_map: dict[str, EventInterpretor] = {}

    def interpret_cels(self, cels: list[CEL], call_log: RawCallLog):
        for cel in cels:
            assert call_log
            call_log = self.interpret_cel(cel, call_log)
        return call_log

    def interpret_cel(self, cel: CEL, call: RawCallLog):
        eventtype = cel.eventtype
        logger.debug("Interpreting CEL event type %s", eventtype)
        if eventtype in self.eventtype_map:
            interpret_function = self.eventtype_map[eventtype]
            return interpret_function(cel, call)
        else:
            logger.debug("Ignoring uninterpretable CEL event type %s", eventtype)
            return call


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

    def can_interpret(self, cels):  # noqa: E261
        return True


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
        call.date = parse_eventtime(cel.eventtime)
        call.source_name = cel.cid_name
        call.source_internal_name = cel.cid_name
        call.source_exten = call.extension_filter.filter(cel.cid_num)
        call.requested_exten = call.extension_filter.filter(cel.exten)
        call.requested_context = cel.context
        call.destination_exten = call.extension_filter.filter(cel.exten)
        call.source_line_identity = identity_from_channel(cel.channame)
        call.raw_participants[cel.channame].update(role='source')
        logger.debug(
            'Setting source line identity info from chan_start event (id=%s)', cel.id
        )
        return call

    def interpret_chan_end(self, cel, call):
        call.date_end = parse_eventtime(cel.eventtime)
        for recording in call.recordings:
            if not recording.end_time:
                recording.end_time = parse_eventtime(cel.eventtime)

        # Remove unwanted extensions
        call.extension_filter.filter_call(call)

        return call

    def interpret_app_start(self, cel, call):
        call.user_field = cel.userfield

        if call.was_forwarded:
            return call

        if cel.cid_name != '':
            logger.debug('Setting source name from app_start event (id=%s)', cel.id)
            call.source_name = cel.cid_name
        if cel.cid_num != '':
            logger.debug('Setting source exten from app_start event (id=%s)', cel.id)
            call.source_exten = call.extension_filter.filter(cel.cid_num)

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_num
        if not call.requested_exten:
            logger.debug(
                'Setting requested_exten from caller answer event (id=%s)', cel.id
            )
            call.requested_exten = call.extension_filter.filter(cel.cid_num)

        return call

    def interpret_bridge_start_or_enter(self, cel: CEL, call):
        extra_dict = extract_cel_extra(cel.extra)
        bridge = extra_dict and bridge_info(extra_dict)
        if not bridge:
            logger.error(
                "Failed to extract expected bridge details from cel(id=%s)", cel.id
            )
        else:
            logger.debug(
                'identified bridge from caller(id=%s, type=%s)',
                bridge.id,
                bridge.technology,
            )
            call.bridges[bridge.id] = bridge
            bridge.channels.add(cel.channame)
            if cel.peer:
                bridge.channels.add(cel.peer)

        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = call.extension_filter.filter(cel.cid_num)

        # accounting for calls to e.g. switchboard,
        # we don't want to consider a call answered when the call is first put on a holding bridge
        if not call.date_answer and (
            (not bridge) or bridge.technology != 'holding_bridge'
        ):
            logger.debug(
                'Identified answer time(%s) from caller(%s) on bridge(id=%s) with peer(%s)',
                cel.eventtime,
                cel.channame,
                bridge.id if bridge else None,
                cel.peer,
            )
            call.date_answer = parse_eventtime(cel.eventtime)

        return call

    def interpret_mixmonitor_start(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not is_valid_mixmonitor_start_extra(extra):
            return call

        recording = Recording(
            start_time=parse_eventtime(cel.eventtime),
            path=extra['filename'],
            mixmonitor_id=extra['mixmonitor_id'],
        )
        if matches := RECORDING_PATH_REGEX.match(extra['filename']):
            recording_uuid_str = matches.group(2)
            recording.uuid = uuid.UUID(recording_uuid_str)
        else:
            recording.uuid = uuid.uuid4()
        call.recordings.append(recording)
        return call

    def interpret_mixmonitor_stop(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not is_valid_mixmonitor_stop_extra(extra):
            return call

        for recording in call.recordings:
            if recording.mixmonitor_id == extra['mixmonitor_id']:
                recording.end_time = parse_eventtime(cel.eventtime)
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

    def interpret_xivo_outcall(self, cel, call: RawCallLog):
        if not call.was_forwarded:
            call.direction = 'outbound'
        else:
            call.destination_details.clear()
            call.destination_exten = call.extension_filter.filter(cel.cid_num)
            call.destination_name = cel.cid_name
            logger.debug('call was forwarded, identified a new external destination')
        return call

    def interpret_xivo_user_fwd(self, cel, call: RawCallLog):
        call.was_forwarded = True
        extra = re.match(EXTRA_USER_FWD_REGEX, cel.extra)

        # Replace destination_exten here because WAZO_USER_MISSED_CALL event
        # doesn't produce the correct destination extension on multiple forwards
        if extra:
            call.destination_exten = call.extension_filter.filter(extra.group(1))

        if call.interpret_caller_xivo_user_fwd:
            if extra:
                call.requested_internal_exten = call.extension_filter.filter(
                    extra.group(1)
                )
                call.requested_internal_context = extra.group(2)
                call.requested_name = extra.group(3)
            call.interpret_caller_xivo_user_fwd = False
        return call

    def interpret_wazo_conference(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            logger.error(
                'Cannot interpret WAZO_CONFERENCE event(cel.id=%s), missing extra data',
                cel.id,
            )
            return call

        _, name = extra['extra'].split('NAME: ', 1)
        call.destination_name = name
        logger.debug(
            'Identified destination name from WAZO_CONFERENCE(id=%s): %s', name, cel.id
        )
        return call

    def interpret_wazo_meeting_name(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            logger.error(
                'Cannot interpret WAZO_MEETING_NAME event(cel.id=%s), missing extra data',
                cel.id,
            )
            return call
        call.destination_name = extra['extra']
        logger.debug(
            'Identified destination name from WAZO_MEETING_NAME(id=%s): %s',
            call.destination_name,
            cel.id,
        )

        if MEETING_EXTENSION_REGEX.match(call.destination_exten):
            call.extension_filter.add_exten(call.destination_exten)
            # Don't call filter.filter_call() yet, to avoid empty exten during interpret.
            # Let interpret_chan_end do it instead.

        return call

    def interpret_wazo_user_missed_call(self, cel, call: RawCallLog):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            logger.error(
                'Cannot interpret WAZO_USER_MISSED_CALL event(cel.id=%s), missing extra data',
                cel.id,
            )
            return call

        (
            wazo_tenant_uuid,
            source_user_uuid,
            destination_user_uuid,
            _,
            source_name,
            destination_name,
        ) = _extract_user_missed_call_variables(extra)

        if source_user_uuid:
            info = {
                "user_uuid": source_user_uuid,
                "answered": False,
                "name": source_name,
                "role": "source",
            }
            call.insert_or_update_participants_info(
                info,
                lambda p: p.get('user_uuid') == source_user_uuid
                and p.get('role') == 'source',
            )

            logger.debug(
                "identified source participant info(user_uuid=%s, user_name=%s)"
                " from WAZO_USER_MISSED_CALL event",
                source_user_uuid,
                source_name,
            )
        if destination_user_uuid:
            info = {
                "user_uuid": destination_user_uuid,
                "answered": False,
                "name": destination_name,
                "role": "destination",
            }
            call.insert_or_update_participants_info(
                info,
                lambda p: p.get('user_uuid') == destination_user_uuid
                and p.get('role') == 'destination',
            )

            logger.debug(
                "identified destination participant info (user_uuid=%s, user_name=%s)"
                " from WAZO_USER_MISSED_CALL event",
                destination_user_uuid,
                destination_name,
            )

        call.set_tenant_uuid(wazo_tenant_uuid)
        call.destination_name = destination_name
        logger.debug(
            'Identified destination ("%s" <%s>) from WAZO_USER_MISSED_CALL(id=%s)',
            call.destination_name,
            call.destination_exten,
            cel.id,
        )
        call.source_name = source_name
        call.source_exten = cel.cid_num
        call.source_line_identity = identity_from_channel(cel.channame)
        return call

    def interpret_wazo_call_log_destination(self, cel, call: RawCallLog):
        extra = extract_cel_extra(cel.extra)
        if not extra:
            return call

        extra_dict = _extract_call_log_destination_variables(extra)
        logger.debug('wazo_call_log_destination payload: %s', extra_dict)

        if 'type' not in extra_dict.keys():
            logger.error('required destination type is not found.')
            return call

        if extra_dict['type'] == 'conference':
            destination_details = {
                'type': extra_dict['type'],
                'conference_id': extra_dict['id'],
            }
        elif extra_dict['type'] == 'user':
            destination_details = {
                'type': extra_dict['type'],
                'user_uuid': extra_dict['uuid'],
                'user_name': extra_dict['name'],
            }
            participant_info = {
                "user_uuid": destination_details['user_uuid'],
                "role": 'destination',
                "name": destination_details['user_name'],
                "requested": (not call.requested_type),
                "tags": [],
            }

            logger.debug(
                "identified destination participant (user_uuid=%s, user_name=%s)"
                " from WAZO_CALL_LOG_DESTINATION",
                destination_details['user_uuid'],
                destination_details['user_name'],
            )
            call.participants_info.append(participant_info)

            call.destination_name = participant_info["name"]
            logger.debug(
                'Setting destination name %s '
                'from WAZO_CALL_LOG_DESTINATION(type=%s)',
                call.destination_name,
                extra_dict['type'],
            )
        elif extra_dict['type'] == 'meeting':
            destination_details = {
                'type': extra_dict['type'],
                'meeting_uuid': extra_dict['uuid'],
                'meeting_name': extra_dict['name'],
            }
        elif extra_dict['type'] == 'group':
            destination_details = {
                'type': extra_dict['type'],
                'group_id': extra_dict['id'],
                'group_label': extra_dict['label'],
            }
            call.destination_name = destination_details['group_label']
            logger.debug(
                'Setting destination name %s '
                'from WAZO_CALL_LOG_DESTINATION(type=%s)',
                call.destination_name,
                extra_dict['type'],
            )
        elif extra_dict['type'] == 'queue':
            destination_details = {
                'type': extra_dict['type'],
                'queue_id': extra_dict['id'],
                'queue_name': extra_dict['name'],
            }
            call.destination_name = destination_details['queue_name']
            logger.debug(
                'Setting destination name %s '
                'from WAZO_CALL_LOG_DESTINATION(type=%s)',
                call.destination_name,
                extra_dict['type'],
            )

        else:
            logger.error('unknown destination type')
            return call

        if not call.requested_type:
            call.requested_type = extra_dict['type']

        call.destination_details = [
            Destination(
                destination_details_key=key,
                destination_details_value=value,
            )
            for key, value in destination_details.items()
        ]
        # we assume information from WAZO_CALL_LOG_DESTINATION
        # is authoritative and should not be overwritten by other events
        logger.debug(
            'setting destination info from WAZO_CALL_LOG_DESTINATION(id=%s) '
            'as authoritative',
            cel.id,
        )
        call.authoritative_destination_info = True
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
                if not call.authoritative_destination_info:
                    call.destination_exten = cel.cid_num
                    call.destination_name = cel.cid_name
                    logger.debug(
                        'Setting destination "%s" <%s> from mobile CHAN_START event(id=%s) '
                        'of channel %s',
                        call.destination_name,
                        call.destination_exten,
                        cel.id,
                        cel.uniqueid,
                    )
                call.destination_internal_exten = cel.cid_num
                call.destination_internal_context = cel.context
            else:
                if not call.authoritative_destination_info:
                    call.destination_exten = cel.cid_num
                    call.destination_name = cel.cid_name
                    logger.debug(
                        'Setting destination "%s" <%s> from CHAN_START event(id=%s) '
                        'of channel %s',
                        cel.cid_name,
                        cel.cid_num,
                        cel.id,
                        cel.uniqueid,
                    )
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
                recording.end_time = parse_eventtime(cel.eventtime)
        return call

    def interpret_bridge_enter(self, cel: CEL, call: RawCallLog):
        extra_dict = extract_cel_extra(cel.extra)
        bridge = bridge_info(extra_dict) if extra_dict else None
        if not bridge:
            logger.error(
                "Failed to extract expected bridge details from bridge_enter cel(id=%s)",
                cel.id,
            )
        else:
            logger.debug(
                'identified bridge (id=%s, type=%s) from callee(%s)',
                bridge.id,
                bridge.technology,
                cel.channame,
            )
            call.bridges[bridge.id] = bridge

        call.raw_participants[cel.channame].update(answered=True)
        # only consider the first bridge_enter for destination identity info
        if call.interpret_callee_bridge_enter and (
            not call.authoritative_destination_info or call.was_forwarded
        ):
            if cel.cid_num and cel.cid_num != 's':
                call.destination_exten = cel.cid_num
            call.destination_name = cel.cid_name

            call.interpret_callee_bridge_enter = False
            logger.debug(
                'interpreting destination_exten(%s), destination_name(%s) '
                ' from callee bridge enter(bridge id=%s) for channel %s',
                cel.cid_num,
                cel.cid_name,
                bridge.id if bridge else None,
                cel.channame,
            )

        if cel.peer:
            logger.debug(
                'callee(%s) entered bridge with peer: %s', cel.channame, cel.peer
            )
            # peer contains multiple entries during adhoc conferences
            peers = [peer for peer in cel.peer.split(',') if peer]
            for peer in peers:
                if bridge:
                    bridge.channels.add(peer)
                if peer not in call.raw_participants:
                    continue
                call.raw_participants[peer].update(answered=True)
            if not call.authoritative_destination_info:
                cid_name, cid_number = call.caller_id_by_channels[cel.channame]
                if cid_name:
                    logger.debug(
                        'Setting destination_name and destination_internal_name '
                        'from channel %s callerid',
                        cel.channame,
                    )
                    call.destination_name = cid_name
                if cid_number:
                    logger.debug(
                        'Setting destination_exten and destination_internal_exten '
                        'from channel %s callerid',
                        cel.channame,
                    )
                    call.destination_exten = cid_number
                    call.destination_internal_exten = cid_number
        else:
            logger.debug('callee(%s) entered bridge with no peer', cel.channame)

        return call

    def interpret_mixmonitor_start(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not is_valid_mixmonitor_start_extra(extra):
            return call

        recording = Recording(
            start_time=parse_eventtime(cel.eventtime),
            path=extra['filename'],
            mixmonitor_id=extra['mixmonitor_id'],
        )
        if matches := RECORDING_PATH_REGEX.match(extra['filename']):
            recording_uuid_str = matches.group(2)
            recording.uuid = uuid.UUID(recording_uuid_str)

        call.recordings.append(recording)
        return call

    def interpret_mixmonitor_stop(self, cel, call):
        extra = extract_cel_extra(cel.extra)
        if not is_valid_mixmonitor_stop_extra(extra):
            return call

        for recording in call.recordings:
            if recording.mixmonitor_id == extra['mixmonitor_id']:
                recording.end_time = parse_eventtime(cel.eventtime)
        return call


class LocalOriginateCELInterpretor:
    def interpret_cels(self, cels, call: RawCallLog):
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

        call.date = parse_eventtime(local_channel1_start.eventtime)
        call.date_end = parse_eventtime(source_channel_end.eventtime)
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
                start_time=parse_eventtime(cel.eventtime),
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
                    recording.end_time = parse_eventtime(cel.eventtime)

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
                # in outgoing calls, destination ANSWER event has more callerid
                # information than START event
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
            call.date_answer = parse_eventtime(
                destination_channel_bridge_enter.eventtime
            )

        is_incall = any([True for cel in cels if cel.eventtype == 'XIVO_INCALL'])
        is_outcall = any([True for cel in cels if cel.eventtype == 'XIVO_OUTCALL'])
        if is_incall:
            call.direction = 'inbound'
        if is_outcall:
            call.direction = 'outbound'

        # extract tenant and user info from WAZO_ORIGINATE_ALL_LINES custom event
        try:
            wazo_originate_all_lines = next(
                cel
                for cel in cels
                if cel.eventtype == CELEventType.wazo_originate_all_lines
            )
        except StopIteration:
            logger.debug(f'No {CELEventType.wazo_originate_all_lines} cel found')
        else:
            logger.info(f'processing {CELEventType.wazo_originate_all_lines} cel entry')
            try:
                info = _parse_wazo_originate_all_lines_extra(
                    wazo_originate_all_lines.extra
                )
            except CELInterpretationError:
                logger.exception(
                    f'Failed to interpret info from {CELEventType.wazo_originate_all_lines}'
                    ' payload for CEL id %d',
                    wazo_originate_all_lines.id,
                )
            else:
                logger.debug(
                    f'tenant identified from {CELEventType.wazo_originate_all_lines}: %s',
                    info['tenant_uuid'],
                )
                call.set_tenant_uuid(info['tenant_uuid'])
                call.raw_participants[wazo_originate_all_lines.channame].update(
                    role='source', requested=False
                )
                participant_info = {
                    'user_uuid': info['user_uuid'],
                    'role': 'source',
                    'requested': (not call.requested_type),
                }
                call.insert_or_update_participants_info(
                    participant_info,
                    lambda p: p.get('user_uuid') == info['user_uuid']
                    and p.get('role') == 'source',
                )
                call.requested_type = 'all_lines'

        return call

    @classmethod
    def can_interpret(cls, cels):
        has_three_channels = cls.three_channels_minimum(cels)
        if not has_three_channels:
            logger.debug(
                f'{cls.__name__} dispatch failed: CELs have less than three channels'
            )
        first_two_channels_local = cls.first_two_channels_are_local(cels)
        if not first_two_channels_local:
            logger.debug(
                f'{cls.__name__} dispatch failed: non-local channel appears in first two channels'
            )

        first_channel_answered_first = (
            cls.first_channel_is_answered_before_any_other_operation(cels)
        )
        if not first_channel_answered_first:
            logger.debug(
                f'{cls.__name__} dispatch failed: first channel is not answered '
                'before other events occur'
            )

        return (
            has_three_channels
            and first_two_channels_local
            and first_channel_answered_first
        )

    @classmethod
    def three_channels_minimum(cls, cels):
        channels = {cel.uniqueid for cel in cels}
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

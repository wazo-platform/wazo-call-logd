# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from collections import namedtuple
from itertools import groupby
from operator import attrgetter
from wazo_call_logd.exceptions import InvalidCallLogException
from wazo_call_logd import raw_call_log
from xivo.asterisk.protocol_interface import protocol_interface_from_channel

from .participant import find_participant
from .database.models import CallLogParticipant


logger = logging.getLogger(__name__)
CallLogsCreation = namedtuple(
    'CallLogsCreation', ('new_call_logs', 'call_logs_to_delete')
)


class CallLogsGenerator:
    def __init__(self, confd, cel_interpretors):
        self.confd = confd
        self._cel_interpretors = cel_interpretors
        self._service_tenant_uuid = None

    def set_default_tenant_uuid(self, token):
        self._service_tenant_uuid = token['metadata']['tenant_uuid']

    def from_cel(self, cels):
        call_logs_to_delete = self.list_call_log_ids(cels)
        new_call_logs = self.call_logs_from_cel(cels)
        return CallLogsCreation(
            new_call_logs=new_call_logs,
            call_logs_to_delete=call_logs_to_delete,
        )

    def call_logs_from_cel(self, cels):
        result = []
        for _, cels_by_call_iter in self._group_cels_by_linkedid(cels):
            cels_by_call = list(cels_by_call_iter)

            call_log = raw_call_log.RawCallLog()
            call_log.cel_ids = [cel.id for cel in cels_by_call]

            interpretor = self._get_interpretor(cels_by_call)
            logger.debug('interpreting cels using %s', interpretor.__class__.__name__)
            call_log = interpretor.interpret_cels(cels_by_call, call_log)

            self._remove_duplicate_participants(call_log)
            self._fetch_participants(self.confd, call_log)
            self._ensure_tenant_uuid_is_set(call_log)
            self._fill_extensions_from_participants(call_log)
            self._remove_incomplete_recordings(call_log)

            try:
                result.append(call_log.to_call_log())
            except InvalidCallLogException as e:
                logger.debug('Invalid call log detected: %s', e)

        return result

    def list_call_log_ids(self, cels):
        return set(cel.call_log_id for cel in cels if cel.call_log_id)

    def _group_cels_by_linkedid(self, cels):
        cels = sorted(cels, key=attrgetter('linkedid'))
        return groupby(cels, key=attrgetter('linkedid'))

    def _get_interpretor(self, cels):
        for interpretor in self._cel_interpretors:
            if interpretor.can_interpret(cels):
                return interpretor

        raise RuntimeError(
            'Could not find suitable interpretor in {}'.format(self._cel_interpretors)
        )

    def _remove_duplicate_participants(self, call_log):
        channel_names = call_log.raw_participants.keys()
        channel_names = sorted(channel_names)
        for _, line_channel_names in groupby(
            channel_names, protocol_interface_from_channel
        ):
            duplicate_channel_names = tuple(line_channel_names)[:-1]
            for duplicate_channel_name in duplicate_channel_names:
                call_log.raw_participants.pop(duplicate_channel_name, None)

    def _fetch_participants(self, confd, call_log):
        call_log.participants = []
        for channel_name, raw_attributes in call_log.raw_participants.items():
            confd_participant = find_participant(confd, channel_name)
            if not confd_participant:
                continue
            raw_attributes.update(**confd_participant)
            answered = {}
            if 'answered' in raw_attributes:
                answered['answered'] = raw_attributes['answered']
            participant_model = CallLogParticipant(
                user_uuid=confd_participant['uuid'],
                line_id=confd_participant['line_id'],
                tags=confd_participant['tags'],
                role=raw_attributes['role'],
                **answered,
            )
            call_log.participants.append(participant_model)

    def _ensure_tenant_uuid_is_set(self, call_log):
        tenant_uuids = {
            raw_participant['tenant_uuid']
            for raw_participant in call_log.raw_participants.values()
            if raw_participant.get('tenant_uuid')
        }
        for tenant_uuid in tenant_uuids:
            call_log.set_tenant_uuid(tenant_uuid)

        if not call_log.tenant_uuid:
            # NOTE(sileht): requested_context
            if call_log.requested_context:
                contexts = self.confd.contexts.list(name=call_log.requested_context)[
                    'items'
                ]
                if contexts:
                    call_log.set_tenant_uuid(contexts[0]['tenant_uuid'])
                    return

            logger.debug(
                "call log of cels `%s` is not attached to a "
                "tenant_uuid, fallback to service tenant %s",
                call_log.cel_ids,
                self._service_tenant_uuid,
            )
            call_log.set_tenant_uuid(self._service_tenant_uuid)

    def _fill_extensions_from_participants(self, call_log):
        source_participants = (
            participant
            for participant in call_log.raw_participants.values()
            if participant['role'] == 'source'
        )
        for source_participant in source_participants:
            extension = source_participant.get('main_extension')
            if not extension:
                continue
            if not (
                call_log.source_internal_exten and call_log.source_internal_context
            ):
                call_log.source_internal_exten = extension['exten']
                call_log.source_internal_context = extension['context']

        destination_participants = (
            participant
            for participant in call_log.raw_participants.values()
            if participant['role'] == 'destination'
        )
        for destination_participant in destination_participants:
            extension = destination_participant.get('main_extension')
            if not extension:
                continue

            if not (
                call_log.destination_internal_exten
                and call_log.destination_internal_context
            ):
                call_log.destination_internal_exten = extension['exten']
                call_log.destination_internal_context = extension['context']

            if not (
                call_log.requested_internal_exten
                and call_log.requested_internal_context
            ):
                call_log.requested_internal_exten = extension['exten']
                call_log.requested_internal_context = extension['context']

    def _remove_incomplete_recordings(self, call_log):
        new_recordings = []
        for recording in call_log.recordings:
            if recording.start_time is None or recording.end_time is None:
                logger.debug('Incomplete recording information')
                continue
            new_recordings.append(recording)
        call_log.recordings = new_recordings

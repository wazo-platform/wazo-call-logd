# Copyright 2022-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging
from collections import namedtuple
from itertools import groupby
from operator import attrgetter
from typing import Iterator, Tuple

from wazo_confd_client import Client as ConfdClient
from xivo.asterisk.protocol_interface import protocol_interface_from_channel
from xivo_dao.alchemy.cel import CEL

from wazo_call_logd.database.cel_event_type import CELEventType
from wazo_call_logd.exceptions import InvalidCallLogException
from wazo_call_logd.raw_call_log import RawCallLog

from .database.models import CallLog, CallLogParticipant
from .participant import ParticipantInfo, find_participant, find_participant_by_uuid

logger = logging.getLogger(__name__)


CallLogsCreation = namedtuple(
    'CallLogsCreation', ('new_call_logs', 'call_logs_to_delete')
)


class _ParticipantsProcessor:
    def __init__(self, confd_client: ConfdClient):
        self.confd: ConfdClient = confd_client
        self.confd_participants: dict[str, ParticipantInfo] = {}

    def __call__(self, call_log: RawCallLog) -> RawCallLog:
        self._fetch_participants(call_log)
        return call_log

    def _fetch_participant_from_channel(self, channel: str) -> ParticipantInfo | None:
        confd_participant = find_participant(self.confd, channel)
        if not confd_participant:
            logger.debug("No participant found for channel %s", channel)
            return
        if confd_participant.uuid in self.confd_participants:
            logger.info(
                "Same user participant connected through multiple lines: (user_uuid=%s, line_id=%s)",
                confd_participant.uuid,
                confd_participant.line_id,
            )
        self.confd_participants[confd_participant.uuid] = confd_participant
        logger.debug(
            "Updated confd participants cache with user %s", confd_participant.uuid
        )
        return confd_participant

    def _fetch_participant_from_user_uuid(
        self, user_uuid: str
    ) -> ParticipantInfo | None:
        confd_participant = self.confd_participants.get(user_uuid)
        if not confd_participant:
            confd_participant = find_participant_by_uuid(self.confd, user_uuid)
            if not confd_participant:
                logger.error("No user found for user_uuid %s", user_uuid)
                return
            self.confd_participants[user_uuid] = confd_participant
            logger.debug("Updated confd participants cache with user %s", user_uuid)
        return confd_participant

    def _compute_participants_from_channels(
        self, call_log: RawCallLog
    ) -> list[CallLogParticipant]:
        connected_participants = []
        for channel_name, raw_attributes in call_log.raw_participants.items():
            confd_participant = self._fetch_participant_from_channel(channel_name)
            if not confd_participant:
                continue
            raw_attributes.update(**confd_participant._asdict())

            participant = CallLogParticipant(user_uuid=confd_participant.uuid)
            participant.line_id = confd_participant.line_id
            participant.tags = confd_participant.tags
            participant.role = raw_attributes['role']
            if 'answered' in raw_attributes:
                participant.answered = raw_attributes["answered"]
            connected_participants.append(participant)
        return connected_participants

    def _fetch_participants(self, call_log: RawCallLog):
        connected_participants = self._compute_participants_from_channels(call_log)

        # participant information from CEL interpretation can augment participants extracted from channels
        # and fill in unreachable participants with no corresponding channel
        unreached_participants = []
        users_from_cel = (
            str(participant_info["user_uuid"])
            for participant_info in call_log.participants_info
            if "user_uuid" in participant_info
        )
        users_from_channels = (str(p.user_uuid) for p in connected_participants)
        user_uuids = set(users_from_cel).union(users_from_channels)
        for user_uuid in user_uuids:
            user_connected_participants = [
                p for p in connected_participants if str(p.user_uuid) == user_uuid
            ]
            user_participants_info = [
                p
                for p in call_log.participants_info
                if "user_uuid" in p and p["user_uuid"] == user_uuid
            ]
            logger.debug(
                "Identified user participant %s(from CEL: %d, from channels: %d)",
                user_uuid,
                len(user_participants_info),
                len(user_connected_participants),
            )

            if not user_connected_participants:
                # case of unreachable users with no matching channels
                confd_participant = self._fetch_participant_from_user_uuid(user_uuid)
                if not confd_participant:
                    continue
                participant = CallLogParticipant(
                    user_uuid=confd_participant.uuid,
                    line_id=confd_participant.line_id,
                    tags=confd_participant.tags,
                    answered=False,
                    role=user_participants_info[-1]["role"],
                )
                unreached_participants.append(participant)
            elif len(user_connected_participants) == len(user_participants_info):
                # simple cases where user mentions from CELs correspond one-to-one to opened channels
                for participant_info, participant in zip(
                    user_participants_info, user_connected_participants
                ):
                    if "answered" in participant_info and participant.answered is None:
                        participant.answered = participant_info["answered"]
            else:
                # tricky cases where cel-based user mentions do not correspond one-to-one with opened channels
                # such as the same user being sometimes unreachable and sometimes reachable in the same call
                logger.debug("Uncorrelated participants info for user %s", user_uuid)

        call_log.participants = connected_participants + unreached_participants


class CallLogsGenerator:
    def __init__(self, confd, cel_interpretors):
        self.confd: ConfdClient = confd
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

    def call_logs_from_cel(self, cels: list[CEL]) -> list[CallLog]:
        result = []
        for linkedids, cels_by_call in self._group_cels_by_shared_channels(cels):
            logger.debug(
                'interpreting %d cels from correlated linkedids(%s)',
                len(cels_by_call),
                linkedids,
            )

            terminated_links = set(
                cel.linkedid
                for cel in cels_by_call
                if cel.eventtype == CELEventType.linkedid_end
            )

            if linkedids != terminated_links:
                unterminated_links = linkedids - terminated_links
                logger.debug(
                    "Skipping correlated cel sequence with incomplete linkedid sequences (%s)",
                    ", ".join(unterminated_links),
                )
                continue

            call_log = RawCallLog()
            call_log.cel_ids = [cel.id for cel in cels_by_call]

            interpretor = self._get_interpretor(cels_by_call)
            logger.debug('interpreting cels using %s', interpretor.__class__.__name__)
            call_log = interpretor.interpret_cels(cels_by_call, call_log)

            self._remove_duplicate_participants(call_log)
            self._fetch_participants(call_log)
            self._ensure_tenant_uuid_is_set(call_log)
            self._fill_extensions_from_participants(call_log)
            self._remove_incomplete_recordings(call_log)

            try:
                result.append(call_log.to_call_log())
            except InvalidCallLogException as e:
                logger.error('Invalid call log detected: %s', e)

        return result

    def list_call_log_ids(self, cels):
        return {cel.call_log_id for cel in cels if cel.call_log_id}

    def _group_cels_by_linkedid(self, cels):
        cels = sorted(cels, key=attrgetter('linkedid'))
        return groupby(cels, key=attrgetter('linkedid'))

    def _group_cels_by_shared_channels(
        self, cels: list[CEL]
    ) -> Iterator[Tuple[set[str], list[CEL]]]:
        cels = sorted(cels, key=attrgetter('linkedid'))
        linkedid_sequences = [
            (linkedid, list(cels))
            for linkedid, cels in groupby(cels, key=attrgetter('linkedid'))
        ]

        # identify linkedid-based cel sequences that share uniqueids(i.e. channels)
        # this correlation is transitive, i.e. if a channel is shared between sequence a and b, and between b and c,
        # then a and c are also correlated
        correlation_groups: list[(set[str], set[str], list[CEL])] = []
        for linkedid, cels in linkedid_sequences:
            uniqueids = set(cel.uniqueid for cel in cels)
            correlated_sequences = False
            for (
                correlated_uniqueids,
                correlated_linkedids,
                correlated_cels,
            ) in correlation_groups:
                # correlation identified if any channel in this cel sequence are also in other sequences in the group
                if uniqueids & correlated_uniqueids:
                    correlated_cels.extend(cels)  # add cels to correlation group
                    correlated_uniqueids.update(
                        uniqueids
                    )  # expand the correlation group to the channels of this sequence
                    correlated_sequences = True
                    correlated_linkedids.add(linkedid)
            if not correlated_sequences:
                # if no correlation found, create a new correlation group
                correlation_groups.append((uniqueids, {linkedid}, list(cels)))

        yield from (
            (linkedids, sorted(cels, key=attrgetter('eventtime')))
            for (uniqueids, linkedids, cels) in correlation_groups
        )

    def _get_interpretor(self, cels):
        for interpretor in self._cel_interpretors:
            if interpretor.can_interpret(cels):
                return interpretor

        raise RuntimeError(
            f'Could not find suitable interpretor in {self._cel_interpretors}'
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

    def _fetch_participants(self, call_log: RawCallLog):
        participant_processor = _ParticipantsProcessor(self.confd)
        return participant_processor(call_log)

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

    def _remove_incomplete_recordings(self, call_log: RawCallLog):
        new_recordings = []
        for recording in call_log.recordings:
            if recording.start_time is None or recording.end_time is None:
                logger.debug('Incomplete recording information')
                continue
            new_recordings.append(recording)
        call_log.recordings = new_recordings

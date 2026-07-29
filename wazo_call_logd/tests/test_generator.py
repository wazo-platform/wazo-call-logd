# Copyright 2013-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import itertools
from collections import defaultdict
from datetime import datetime
from unittest import TestCase
from unittest.mock import ANY, Mock, create_autospec, patch

import requests.exceptions
from hamcrest import (
    all_of,
    anything,
    assert_that,
    calling,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_length,
    has_properties,
    has_property,
    is_,
    none,
    raises,
)
from xivo_dao.alchemy.cel import CEL

from wazo_call_logd.database.cel_event_type import CELEventType
from wazo_call_logd.database.models import Destination, Recording
from wazo_call_logd.exceptions import InvalidCallLogException
from wazo_call_logd.generator import (
    CallLogsGenerator,
    _group_cels_by_shared_channels,
    _ParticipantsProcessor,
)
from wazo_call_logd.raw_call_log import RawCallLog


def mock_call():
    return create_autospec(
        RawCallLog,
        instance=True,
        raw_participants={},
        recordings=[],
        participants=[],
        participants_info=[],
        date_answer=None,
        reached_voicemail=False,
    )


class TestCallLogsGenerator(TestCase):
    def setUp(self):
        self.interpretor = Mock()
        self.confd_client = Mock()
        self.generator = CallLogsGenerator(self.confd_client, [self.interpretor])

    def test_from_cel(self):
        self.generator.call_logs_from_cel = Mock()
        self.generator.list_call_log_ids = Mock()
        expected_calls = self.generator.call_logs_from_cel.return_value = Mock()
        expected_to_delete = self.generator.list_call_log_ids.return_value = Mock()
        cels = Mock()

        result = self.generator.from_cel(cels)

        self.generator.call_logs_from_cel.assert_called_once_with(cels)
        assert_that(
            result,
            all_of(
                has_property('new_call_logs', expected_calls),
                has_property('call_logs_to_delete', expected_to_delete),
            ),
        )

    def test_call_logs_from_cel_no_cels(self):
        cels = []

        result = self.generator.call_logs_from_cel(cels)

        assert_that(result, equal_to([]))

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_call_logs_from_cel_one_call(self, raw_call_log_constructor):
        linkedid = '9328742934'
        cels = self._generate_cels_for_call(linkedid)
        call = mock_call()
        self.interpretor.interpret_cels.return_value = call
        raw_call_log_constructor.return_value = call
        expected_call = call.to_call_log.return_value

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_called_once_with(cels, call)
        assert_that(result, contains_exactly(expected_call))

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_call_logs_from_cel_two_calls(self, raw_call_log_constructor):
        cels_1 = self._generate_cels_for_call('9328742934')
        cels_2 = self._generate_cels_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1 = mock_call()
        call_2 = mock_call()
        self.interpretor.interpret_cels.side_effect = [call_1, call_2]
        raw_call_log_constructor.side_effect = [call_1, call_2]
        expected_call_1 = call_1.to_call_log.return_value
        expected_call_2 = call_2.to_call_log.return_value

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_any_call(cels_1, ANY)
        self.interpretor.interpret_cels.assert_any_call(cels_2, ANY)
        assert_that(result, contains_inanyorder(expected_call_1, expected_call_2))

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_call_logs_from_cel_two_calls_one_valid_one_invalid(
        self, raw_call_log_constructor
    ):
        cels_1 = self._generate_cels_for_call('9328742934')
        cels_2 = self._generate_cels_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1 = mock_call()
        call_2 = mock_call()
        self.interpretor.interpret_cels.side_effect = [call_1, call_2]
        raw_call_log_constructor.side_effect = [call_1, call_2]
        expected_call_1 = call_1.to_call_log.return_value
        call_2.to_call_log.side_effect = InvalidCallLogException()

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_any_call(cels_1, ANY)
        self.interpretor.interpret_cels.assert_any_call(cels_2, ANY)
        assert_that(result, contains_exactly(expected_call_1))

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_call_logs_from_cels_incomplete_call(self, raw_call_log_constructor):
        cels = self._generate_cels_for_incomplete_call('9328742934')
        raw_call_log_constructor.side_effect = AssertionError

        result = self.generator.call_logs_from_cel(cels)
        assert_that(result, empty())

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_call_logs_from_cels_multiple_calls_one_incomplete(
        self, raw_call_log_constructor
    ):
        cels_1 = self._generate_cels_for_incomplete_call('9328742934')
        cels_2 = self._generate_cels_for_call('9328742935')
        cels = cels_1 + cels_2
        call_1 = mock_call()
        self.interpretor.interpret_cels.side_effect = lambda cels, call: call
        raw_call_log_constructor.side_effect = [call_1]
        expected_call_1 = call_1.to_call_log.return_value

        result = self.generator.call_logs_from_cel(cels)
        self.interpretor.interpret_cels.assert_any_call(cels_2, ANY)

        assert_that(result, contains_exactly(expected_call_1))

    def test_list_call_log_ids(self):
        cel_1, cel_2 = Mock(call_log_id=1), Mock(call_log_id=1)
        cel_3, cel_4 = Mock(call_log_id=2), Mock(call_log_id=None)
        cels = [cel_1, cel_2, cel_3, cel_4]

        result = self.generator.list_call_log_ids(cels)

        assert_that(result, contains_inanyorder(1, 2))

    def test_given_interpretors_can_interpret_then_use_first_interpretor(self):
        interpretor_true_1 = Mock()
        interpretor_true_2 = Mock()
        interpretor_false = Mock()
        interpretor_true_1.can_interpret.return_value = True
        interpretor_true_2.can_interpret.return_value = True
        interpretor_false.can_interpret.return_value = False
        interpretor_true_1.interpret_cels.return_value = mock_call()
        interpretor_true_2.interpret_cels.return_value = mock_call()
        generator = CallLogsGenerator(
            self.confd_client,
            [
                interpretor_false,
                interpretor_true_1,
                interpretor_true_2,
                interpretor_false,
            ],
        )
        cels = self._generate_cels_for_call('545783248')

        generator.call_logs_from_cel(cels)

        interpretor_true_1.interpret_cels.assert_called_once_with(cels, ANY)
        assert_that(interpretor_true_2.interpret_cels.called, is_(False))
        assert_that(interpretor_false.interpret_cels.called, is_(False))

    def test_given_no_interpretor_can_interpret_then_raise(self):
        interpretor = Mock()
        interpretor.can_interpret.return_value = False
        generator = CallLogsGenerator(self.confd_client, [interpretor])
        cels = self._generate_cels_for_call('545783248')

        assert_that(
            calling(generator.call_logs_from_cel).with_args(cels), raises(RuntimeError)
        )

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_cels_from_correlated_linkedids_grouped(self, call_log_constructor):
        sequence_1 = self._generate_cels_for_call('123456789.0')
        sequence_2 = self._generate_cels_for_call('123456789.1')
        sequence_2[0].uniqueid = sequence_1[0].uniqueid

        call_log_constructor.return_value.reached_voicemail = False
        self.interpretor.interpret_cels.side_effect = lambda cels, call: call
        call_logs = self.generator.call_logs_from_cel(sequence_1 + sequence_2)
        assert call_logs
        self.interpretor.interpret_cels.assert_any_call(
            sorted(sequence_1 + sequence_2, key=lambda cel: cel.eventtime), ANY
        )

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_cels_from_uncorrelated_linkedids_not_grouped(self, call_log_constructor):
        sequence_1 = self._generate_cels_for_call('123456789.0')
        sequence_2 = self._generate_cels_for_call('123456789.1')

        call_log_constructor.return_value.reached_voicemail = False
        self.interpretor.interpret_cels.side_effect = lambda cels, call: call
        call_logs = self.generator.call_logs_from_cel(sequence_1 + sequence_2)
        assert call_logs
        self.interpretor.interpret_cels.assert_any_call(sequence_1, ANY)
        self.interpretor.interpret_cels.assert_any_call(sequence_2, ANY)
        assert_that(call_logs, has_length(2))

    def _generate_cels_for_call(self, linked_id: str, cel_count=3):
        result = []
        for i in range(cel_count - 1):
            result.append(
                create_autospec(
                    CEL,
                    instance=True,
                    linkedid=linked_id,
                    eventtime=f'2023-05-31 00:00:0{i}.000000+00',
                )
            )
        result.append(
            create_autospec(
                CEL,
                instance=True,
                linkedid=linked_id,
                eventtype=CELEventType.linkedid_end,
                eventtime=f'2023-05-31 00:00:0{i}.000000+00',
            )
        )
        return result

    def _generate_cels_for_incomplete_call(self, linked_id: str, cel_count=3):
        result = []
        for i in range(cel_count):
            result.append(
                create_autospec(
                    CEL,
                    instance=True,
                    linkedid=linked_id,
                    eventtime=f'2023-05-31 00:00:0{i}.000000+00',
                )
            )
        return result


def mock_data_dict(**kwargs):
    d = defaultdict(lambda: None)
    d.update(**kwargs)
    return d


class TestParticipantsProcessor(TestCase):
    def setUp(self):
        self.confd = Mock()
        self.processor = _ParticipantsProcessor(self.confd)

    def test_participants_missing_from_confd(self):
        raw_call_log = mock_call()
        raw_call_log.raw_participants = {"channel/id": {}}
        raw_call_log.participants_info = [
            {"user_uuid": "some-user-uuid", "answered": True}
        ]
        self.confd.users.get.side_effect = requests.exceptions.HTTPError()
        call_log = self.processor(raw_call_log)
        assert_that(self.confd.mock_calls, contains_exactly(anything()))
        assert_that(call_log.participants, is_(empty()))

    def test_participant_identified_from_channel(self):
        call_log = mock_call()
        channel_name = "PJSIP/rgcZLNGE-00000028"
        call_log.raw_participants[channel_name] = {
            "role": "destination",
            "requested": True,
        }
        call_log.participants_info = [
            {
                "user_uuid": "some-user-uuid",
                "answered": True,
                "role": "destination",
                "requested": True,
            }
        ]

        confd_user = mock_data_dict(
            uuid="some-user-uuid", lines=[mock_data_dict(name="rgcZLNGE", id=1)]
        )
        confd_line = mock_data_dict(name="rgcZLNGE", id=1, users=[confd_user])
        self.confd.users.get.return_value = confd_user
        self.confd.lines.list.return_value = {"items": [confd_line]}
        call_log = self.processor(call_log)
        assert_that(
            self.confd.users.get.mock_calls, has_length(1)
        )  # verify cache effectiveness
        assert_that(
            call_log.participants,
            contains_exactly(
                has_properties(
                    answered=True,
                    user_uuid="some-user-uuid",
                    role="destination",
                    requested=True,
                )
            ),
        )


class TestGroupCelsBySharedChannels(TestCase):
    def _generate_cel_sequence(self, linked_id: str, uniqueid_generator, cel_count=3):
        cels = []
        for i in range(cel_count):
            cels.append(
                create_autospec(
                    CEL,
                    instance=True,
                    linkedid=linked_id,
                    uniqueid=uniqueid_generator(),
                    eventtime=f'2023-05-31 00:00:0{i}.000000+00',
                )
            )
        return cels

    def test_group_correlated_cels(self):
        linkedid_1 = '123456789.0'

        uniqueid_cycle = itertools.cycle(
            linkedid_1.replace('.0', f'.{i}') for i in range(5)
        )
        cel_sequence_1 = self._generate_cel_sequence(
            linkedid_1, lambda: next(uniqueid_cycle), cel_count=10
        )
        linkedid_2 = '123456789.5'
        # uniqueids sequence for this linkedid overlap first sequence over the first 3 elements
        uniqueid_cycle_2 = itertools.cycle(
            linkedid_1.replace('.0', f'.{i + 3}') for i in range(5)
        )
        cel_sequence_2 = self._generate_cel_sequence(
            linkedid_2, lambda: next(uniqueid_cycle_2), cel_count=10
        )
        assert {cel.uniqueid for cel in cel_sequence_1} & {
            cel.uniqueid for cel in cel_sequence_2
        }

        groups = list(_group_cels_by_shared_channels(cel_sequence_1 + cel_sequence_2))

        assert_that(groups, has_length(1))

        assert_that(
            groups,
            contains_exactly(
                contains_exactly(
                    contains_inanyorder(linkedid_1, linkedid_2),
                    contains_exactly(
                        *sorted(
                            cel_sequence_1 + cel_sequence_2,
                            key=lambda cel: cel.eventtime,
                        )
                    ),
                )
            ),
        )

    def test_uncorrelated_cels(self):
        linkedid_1 = '123456789.0'
        uniqueids = (linkedid_1.replace('.0', f'.{i}') for i in itertools.count(0))

        cel_sequence_1 = self._generate_cel_sequence(
            linkedid_1, lambda: next(uniqueids), cel_count=10
        )
        linkedid_2 = '123456789.11'
        # uniqueids sequence for this linkedid overlap first sequence over the first 3 elements
        cel_sequence_2 = self._generate_cel_sequence(
            linkedid_2, lambda: next(uniqueids), cel_count=10
        )
        assert {cel.uniqueid for cel in cel_sequence_1}.isdisjoint(
            cel.uniqueid for cel in cel_sequence_2
        )

        groups = list(_group_cels_by_shared_channels(cel_sequence_1 + cel_sequence_2))

        assert_that(groups, has_length(2))

        assert_that(
            groups,
            contains_inanyorder(
                contains_exactly(
                    contains_inanyorder(linkedid_1),
                    contains_exactly(
                        *sorted(
                            cel_sequence_1,
                            key=lambda cel: cel.eventtime,
                        )
                    ),
                ),
                contains_exactly(
                    contains_inanyorder(linkedid_2),
                    contains_exactly(
                        *sorted(
                            cel_sequence_2,
                            key=lambda cel: cel.eventtime,
                        )
                    ),
                ),
            ),
        )

    def test_correlated_and_uncorrelated_cels(self):
        linkedid_1 = '123456789.0'
        uniqueids = (linkedid_1.replace('.0', f'.{i}') for i in itertools.count(0))

        cel_sequence_1 = self._generate_cel_sequence(
            linkedid_1, lambda: next(uniqueids), cel_count=10
        )
        linkedid_2 = '123456789.11'
        # uniqueids sequence for this linkedid overlap first sequence over the first 3 elements
        cel_sequence_2 = self._generate_cel_sequence(
            linkedid_2, lambda: next(uniqueids), cel_count=10
        )
        assert {cel.uniqueid for cel in cel_sequence_1}.isdisjoint(
            cel.uniqueid for cel in cel_sequence_2
        )

        linkedid_3 = '123456789.21'
        uniqueids = itertools.chain(
            (cel.uniqueid for cel in itertools.islice(cel_sequence_2, 5, None)),
            uniqueids,
        )
        cel_sequence_3 = self._generate_cel_sequence(
            linkedid_3, lambda: next(uniqueids), cel_count=10
        )
        assert {cel.uniqueid for cel in cel_sequence_1}.isdisjoint(
            cel.uniqueid for cel in cel_sequence_3
        )
        assert {cel.uniqueid for cel in cel_sequence_2}.intersection(
            cel.uniqueid for cel in cel_sequence_3
        )

        groups = list(
            _group_cels_by_shared_channels(
                cel_sequence_1 + cel_sequence_2 + cel_sequence_3
            )
        )

        assert_that(groups, has_length(2))

        assert_that(
            groups,
            contains_inanyorder(
                contains_exactly(
                    contains_inanyorder(linkedid_1),
                    contains_exactly(
                        *sorted(
                            cel_sequence_1,
                            key=lambda cel: cel.eventtime,
                        )
                    ),
                ),
                contains_exactly(
                    contains_inanyorder(linkedid_2, linkedid_3),
                    contains_exactly(
                        *sorted(
                            cel_sequence_2 + cel_sequence_3,
                            key=lambda cel: cel.eventtime,
                        )
                    ),
                ),
            ),
        )


class TestFillExtensionsFromParticipants(TestCase):
    def setUp(self):
        self.generator = CallLogsGenerator(Mock(), [Mock()])

    def _make_participant(self, exten, context, answered=False):
        return {
            'role': 'destination',
            'answered': answered,
            'main_extension': {'exten': exten, 'context': context},
        }

    def test_destination_internal_uses_answered_participant(self):
        call_log = RawCallLog()
        call_log.raw_participants = {
            'chan1': self._make_participant('101', 'default', answered=False),
            'chan2': self._make_participant('102', 'default', answered=True),
        }

        self.generator._fill_extensions_from_participants(call_log)

        assert_that(call_log.destination_internal_exten, equal_to('102'))
        assert_that(call_log.destination_internal_context, equal_to('default'))

    def test_destination_internal_falls_back_to_first_when_unanswered(self):
        call_log = RawCallLog()
        call_log.raw_participants = {
            'chan1': self._make_participant('101', 'default', answered=False),
            'chan2': self._make_participant('102', 'default', answered=False),
        }

        self.generator._fill_extensions_from_participants(call_log)

        assert_that(call_log.destination_internal_exten, equal_to('101'))
        assert_that(call_log.destination_internal_context, equal_to('default'))

    def test_destination_internal_not_set_when_no_main_extension(self):
        call_log = RawCallLog()
        call_log.raw_participants = {
            'chan1': {'role': 'destination', 'answered': True},
        }

        self.generator._fill_extensions_from_participants(call_log)

        assert_that(call_log.destination_internal_exten, none())
        assert_that(call_log.destination_internal_context, none())


class TestResolveVoicemailDestination(TestCase):
    TENANT_UUID = '54eb71f8-1f4b-4ae4-8730-638062fbe521'
    USER_UUID = 'cb79f29b-f69a-4b93-85c2-49dcce119a9f'

    def setUp(self):
        self.confd = Mock()
        self.generator = CallLogsGenerator(self.confd, [Mock()])

    def _user_destination(self):
        return [
            Destination(
                destination_details_key='type', destination_details_value='user'
            ),
            Destination(
                destination_details_key='user_uuid',
                destination_details_value=self.USER_UUID,
            ),
        ]

    def _voicemail_call_log(self):
        call_log = RawCallLog()
        call_log.set_tenant_uuid(self.TENANT_UUID)
        call_log.reached_voicemail = True
        call_log.voicemail_number = '1006'
        call_log.voicemail_context = 'default'
        call_log.destination_details = self._user_destination()
        return call_log

    def test_unanswered_voicemail_supersedes_destination_details(self):
        self.confd.voicemails.list.return_value = {
            'items': [{'id': 7, 'name': 'Harry VM'}]
        }
        call_log = self._voicemail_call_log()

        self.generator._resolve_voicemail_destination(call_log, {})

        assert_that(
            call_log.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='voicemail',
                ),
                has_properties(
                    destination_details_key='voicemail_id',
                    destination_details_value='7',
                ),
                has_properties(
                    destination_details_key='voicemail_name',
                    destination_details_value='Harry VM',
                ),
            ),
        )

    def test_confd_failure_keeps_interpreted_destination_details(self):
        # confd unreachable: keep the interpreted user destination_details
        # instead of overwriting the only user attribution with a bare entry.
        self.confd.voicemails.list.side_effect = requests.exceptions.ConnectionError(
            'confd unreachable'
        )
        call_log = self._voicemail_call_log()

        self.generator._resolve_voicemail_destination(call_log, {})

        assert_that(
            call_log.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='user',
                ),
                has_properties(
                    destination_details_key='user_uuid',
                    destination_details_value=self.USER_UUID,
                ),
            ),
        )

    def test_unknown_mailbox_keeps_interpreted_destination_details(self):
        # confd reachable but the mailbox is unknown: same preservation.
        self.confd.voicemails.list.return_value = {'items': []}
        call_log = self._voicemail_call_log()

        self.generator._resolve_voicemail_destination(call_log, {})

        assert_that(
            call_log.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='user',
                ),
                has_properties(
                    destination_details_key='user_uuid',
                    destination_details_value=self.USER_UUID,
                ),
            ),
        )

    def test_cache_collapses_repeated_lookups_into_one_confd_call(self):
        # A batch of call logs hitting the same mailbox must issue a single
        # confd request, not one per call log.
        self.confd.voicemails.list.return_value = {
            'items': [{'id': 7, 'name': 'Harry VM'}]
        }
        cache: dict = {}

        for _ in range(3):
            self.generator._resolve_voicemail_destination(
                self._voicemail_call_log(), cache
            )

        self.confd.voicemails.list.assert_called_once()

    def test_transient_confd_failure_is_not_cached(self):
        # A request failure must not poison the cache: a later call to the same
        # mailbox retries confd.
        self.confd.voicemails.list.side_effect = [
            requests.exceptions.ConnectionError('confd unreachable'),
            {'items': [{'id': 7, 'name': 'Harry VM'}]},
        ]
        cache: dict = {}

        first = self._voicemail_call_log()
        self.generator._resolve_voicemail_destination(first, cache)
        second = self._voicemail_call_log()
        self.generator._resolve_voicemail_destination(second, cache)

        assert_that(self.confd.voicemails.list.call_count, equal_to(2))
        assert_that(
            second.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='voicemail',
                ),
                has_properties(
                    destination_details_key='voicemail_id',
                    destination_details_value='7',
                ),
                has_properties(
                    destination_details_key='voicemail_name',
                    destination_details_value='Harry VM',
                ),
            ),
        )

    def test_answered_call_keeps_interpreted_destination_details(self):
        # A call that reached voicemail but was ultimately answered (voicemail
        # escape then operator) has computed call_status 'answered', so its
        # interpreted destination_details must be preserved, not overwritten.
        call_log = self._voicemail_call_log()
        call_log.date_answer = datetime.fromisoformat('2024-05-07 20:01:05+00:00')

        self.generator._resolve_voicemail_destination(call_log, {})

        self.confd.voicemails.list.assert_not_called()
        assert_that(
            call_log.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='user',
                ),
                has_properties(
                    destination_details_key='user_uuid',
                    destination_details_value=self.USER_UUID,
                ),
            ),
        )


class TestRemoveRecordingsForUnansweredCalls(TestCase):
    def setUp(self):
        self.generator = CallLogsGenerator(Mock(), [Mock()])

    def _recording(self):
        return Recording(
            start_time=datetime.fromisoformat('2021-01-01 00:00:00+00:00'),
            end_time=datetime.fromisoformat('2021-01-01 00:00:05+00:00'),
        )

    def test_recordings_dropped_when_call_was_not_answered(self):
        call_log = RawCallLog()
        call_log.date_answer = None
        call_log.raw_participants = {
            'SIP/caller-00000001': {'role': 'source', 'answered': False},
            'SIP/callee-00000002': {'role': 'destination', 'answered': False},
        }
        call_log.recordings = [self._recording()]

        self.generator._remove_recordings_for_unanswered_calls(call_log)

        assert_that(call_log.recordings, empty())

    def test_recordings_kept_when_call_was_answered(self):
        call_log = RawCallLog()
        call_log.date_answer = datetime.fromisoformat('2021-01-01 00:00:01+00:00')
        recording = self._recording()
        call_log.recordings = [recording]

        self.generator._remove_recordings_for_unanswered_calls(call_log)

        assert_that(call_log.recordings, contains_exactly(recording))

    def test_recordings_kept_when_a_participant_answered_without_date_answer(self):
        # Some bridged scenarios (e.g. a mobile callee answering without a caller
        # ANSWER cel) leave date_answer None even though the call was answered.
        call_log = RawCallLog()
        call_log.date_answer = None
        call_log.raw_participants = {
            'SIP/callee-00000002': {'role': 'destination', 'answered': True},
        }
        recording = self._recording()
        call_log.recordings = [recording]

        self.generator._remove_recordings_for_unanswered_calls(call_log)

        assert_that(call_log.recordings, contains_exactly(recording))

# Copyright 2013-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import itertools
from collections import defaultdict
from unittest import TestCase
from unittest.mock import ANY, Mock, create_autospec, patch

import requests.exceptions
from hamcrest import (
    all_of,
    anything,
    assert_that,
    calling,
    contains,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_length,
    has_properties,
    has_property,
    is_,
    raises,
)
from xivo_dao.alchemy.cel import CEL

from wazo_call_logd.database.cel_event_type import CELEventType
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
        assert_that(self.confd.mock_calls, contains(anything()))
        assert_that(call_log.participants, is_(empty()))

    def test_participant_identified_from_channel(self):
        call_log = mock_call()
        channel_name = "PJSIP/rgcZLNGE-00000028"
        call_log.raw_participants[channel_name] = {"role": "destination"}
        call_log.participants_info = [
            {"user_uuid": "some-user-uuid", "answered": True, "role": "destination"}
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
                    answered=True, user_uuid="some-user-uuid", role="destination"
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

# Copyright 2013-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from unittest import TestCase
from unittest.mock import ANY, Mock, patch, create_autospec

from hamcrest import (
    all_of,
    assert_that,
    calling,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    has_property,
    is_,
    raises,
)
from wazo_call_logd.raw_call_log import RawCallLog
from wazo_call_logd.generator import CallLogsGenerator
from wazo_call_logd.exceptions import InvalidCallLogException


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
        cels = self._generate_cel_for_call([linkedid])
        call = mock_call()
        self.interpretor.interpret_cels.return_value = call
        raw_call_log_constructor.return_value = call
        expected_call = call.to_call_log.return_value

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_called_once_with(cels, call)
        assert_that(result, contains_exactly(expected_call))

    @patch('wazo_call_logd.generator.RawCallLog')
    def test_call_logs_from_cel_two_calls(self, raw_call_log_constructor):
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
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
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
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
        cels = self._generate_cel_for_call(['545783248'])

        generator.call_logs_from_cel(cels)

        interpretor_true_1.interpret_cels.assert_called_once_with(cels, ANY)
        assert_that(interpretor_true_2.interpret_cels.called, is_(False))
        assert_that(interpretor_false.interpret_cels.called, is_(False))

    def test_given_no_interpretor_can_interpret_then_raise(self):
        interpretor = Mock()
        interpretor.can_interpret.return_value = False
        generator = CallLogsGenerator(self.confd_client, [interpretor])
        cels = self._generate_cel_for_call(['545783248'])

        assert_that(
            calling(generator.call_logs_from_cel).with_args(cels), raises(RuntimeError)
        )

    def _generate_cel_for_call(self, linked_id, cel_count=3):
        result = []
        for _ in range(cel_count):
            result.append(Mock(linkedid=linked_id))

        return result

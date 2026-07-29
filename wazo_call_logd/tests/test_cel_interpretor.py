# Copyright 2013-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import urllib.parse
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock, create_autospec, sentinel

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_properties,
    none,
    not_none,
    same_instance,
)
from pytest import raises

from wazo_call_logd.exceptions import CELInterpretationError, InvalidCallLogException

from ..cel_interpretor import (
    AbstractCELInterpretor,
    CalleeCELInterpretor,
    CallerCELInterpretor,
    DispatchCELInterpretor,
    LocalOriginateCELInterpretor,
    _extract_user_missed_call_variables,
    _parse_wazo_originate_all_lines_extra,
    bridge_info,
    extract_cel_extra,
    extract_key_value_pairs_as_dict,
    is_valid_mixmonitor_start_extra,
    is_valid_mixmonitor_stop_extra,
    parse_key_pair_sequence,
)
from ..database.cel_event_type import CELEventType
from ..database.models import Recording
from ..raw_call_log import RawCallLog


class TestExtractUserMissedCallVariables(TestCase):
    def setUp(self):
        self.wazo_tenant_uuid = '2c34c282-433e-4bb8-8d56-fec14ff7e1e9'
        self.source_user_uuid = ''
        self.destination_user_uuid = 'de77813f-3a09-4558-ac14-d9c829e95818'
        self.destination_exten = '1006'
        self.source_name = '"TREMBLAY, François" <5551234567>'
        self.destination_name = 'Karl'

        self.valid_separators = [',', ', ']

    def test_uriencoded_field(self):
        encoded_source_name = urllib.parse.quote(self.source_name)
        encoded_destination_name = urllib.parse.quote(self.destination_name)

        for separator in self.valid_separators:
            extra_string = separator.join(
                [
                    f'wazo_tenant_uuid: {self.wazo_tenant_uuid}',
                    f'source_user_uuid: {self.source_user_uuid}',
                    f'destination_user_uuid: {self.destination_user_uuid}',
                    f'destination_exten: {self.destination_exten}',
                    f'source_name: {encoded_source_name}',
                    f'destination_name: {encoded_destination_name}',
                ]
            )
            extra = {'extra': extra_string}

            result = _extract_user_missed_call_variables(extra)

            assert_that(
                result,
                contains_exactly(
                    self.wazo_tenant_uuid,
                    self.source_user_uuid,
                    self.destination_user_uuid,
                    self.destination_exten,
                    self.source_name,
                    self.destination_name,
                ),
            )

    def test_pre_uriencoded_field(self):
        # CEL generated before the upgrade can still be deserialized
        old_source_name = (
            '"TREMBLAY François" <5551234567>'  # Commas were not supported
        )
        extra_string = ','.join(
            [
                f'wazo_tenant_uuid: {self.wazo_tenant_uuid}',
                f'source_user_uuid: {self.source_user_uuid}',
                f'destination_user_uuid: {self.destination_user_uuid}',
                f'destination_exten: {self.destination_exten}',
                f'source_name: {old_source_name}',
                f'destination_name: {self.destination_name}',
            ]
        )
        extra = {'extra': extra_string}

        result = _extract_user_missed_call_variables(extra)

        assert_that(
            result,
            contains_exactly(
                self.wazo_tenant_uuid,
                self.source_user_uuid,
                self.destination_user_uuid,
                self.destination_exten,
                old_source_name,
                self.destination_name,
            ),
        )


class TestExtractCELExtra:
    def test_valid_extra(self):
        extra = '{"key": "value", "key2": "value2"}'
        result = extract_cel_extra(extra)
        assert_that(result, has_entries(key='value', key2='value2'))

    def test_invalid_json(self):
        extra = '{"key": "value"'
        result = extract_cel_extra(extra)
        assert_that(result, none())

    def test_missing_extra(self):
        extra = None
        result = extract_cel_extra(extra)
        assert_that(result, none())


class TestParseOriginateAllLinesExtra:
    def test_valid_payloads(self):
        user_uuid = 'some-uuid-value'
        tenant_uuid = 'another-uuid-value'

        valid_extras = [
            f'{{"extra": "user_uuid:{user_uuid},tenant_uuid:{tenant_uuid}"}}',
            f'{{"extra": "user_uuid:{user_uuid}, tenant_uuid:{tenant_uuid}"}}',
            f'{{"extra": "user_uuid: {user_uuid}, tenant_uuid: {tenant_uuid}"}}',
            f'{{"extra": "user_uuid: {user_uuid}, tenant_uuid: {tenant_uuid}, whatsthis:"}}',
        ]
        for extra in valid_extras:
            info = _parse_wazo_originate_all_lines_extra(extra)
            assert_that(info, not_none())
            assert_that(
                info, has_entries({'user_uuid': user_uuid, 'tenant_uuid': tenant_uuid})
            )

    def test_invalid_payload(self):
        invalid_extras = [
            '{"extra": "user_uuid:some-uuid;tenant_uuid:some-uuid"}',
            '{"extra": "user_uuid:some-uuid tenant_uuid:some-uuid"}',
            '{"extra": "user_uuid:some-uuid tenant_uuid:some-uuid"}',
        ]
        for extra in invalid_extras:
            with raises(CELInterpretationError):
                _parse_wazo_originate_all_lines_extra(extra)

    def test_invalid_json(self):
        invalid_extras = [
            '{"extra: "user_uuid:some-uuid;tenant_uuid:some-uuid"}',
            '{"extra": "user_uuid:some-uuid tenant_uuid:some-uuid"',
            '"user_uuid:some-uuid tenant_uuid:some-uuid"',
        ]
        for extra in invalid_extras:
            with raises(CELInterpretationError):
                _parse_wazo_originate_all_lines_extra(extra)


class TestIsValidMixmonitorStartExtra:
    def test_valid_extra(self):
        extra = {'filename': '/tmp/foo.wav', 'mixmonitor_id': '0x01'}
        is_valid = is_valid_mixmonitor_start_extra(extra)
        assert_that(is_valid)

    def test_missing_extra(self):
        extra = None
        is_valid = is_valid_mixmonitor_start_extra(extra)
        assert_that(not is_valid)

    def test_missing_filename(self):
        extra = {'mixmonitor_id': '0x01'}
        is_valid = is_valid_mixmonitor_start_extra(extra)
        assert_that(not is_valid)

    def test_missing_mixmonitor_id(self):
        extra = {'filename': '/tmp/foo.wav'}
        is_valid = is_valid_mixmonitor_start_extra(extra)
        assert_that(not is_valid)


class TestIsValidMixmonitorStopExtra:
    def test_valid_extra(self):
        extra = {'mixmonitor_id': '0x01'}
        is_valid = is_valid_mixmonitor_stop_extra(extra)
        assert_that(is_valid)

    def test_missing_extra(self):
        extra = None
        is_valid = is_valid_mixmonitor_stop_extra(extra)
        assert_that(not is_valid)

    def test_missing_mixmonitor_id(self):
        extra = {'filename': '/tmp/foo.wav'}
        is_valid = is_valid_mixmonitor_stop_extra(extra)
        assert_that(not is_valid)


class TestBridgeInfo(TestCase):
    def test_simple_bridge(self):
        details = {'bridge_id': 'some-uuid', 'bridge_technology': 'simple_bridge'}
        bridge = bridge_info(details)
        assert_that(
            bridge,
            has_properties(id='some-uuid', technology='simple_bridge'),
        )

    def test_missing_attribute_returns_none(self):
        details = {'bridge_technology': 'simple_bridge'}
        assert_that(bridge_info(details), none())

        details = {'bridge_id': 'some-uuid'}
        assert_that(bridge_info(details), none())

    def test_extra_attributes_ignored(self):
        details = {
            'bridge_id': 'some-uuid',
            'bridge_technology': 'simple_bridge',
            'extra_attribute': 'irrelevant_value',
        }
        bridge = bridge_info(details)
        assert_that(
            bridge,
            has_properties(id='some-uuid', technology='simple_bridge'),
        )


class TestCELDispatcher(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = Mock()
        self.callee_cel_interpretor = Mock()
        self.cel_dispatcher = DispatchCELInterpretor(
            self.caller_cel_interpretor, self.callee_cel_interpretor
        )

    def test_split_caller_callee_cels_no_cels(self):
        cels = []

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(result, contains_exactly(contains_exactly(), contains_exactly()))

    def test_split_caller_callee_cels_1_uniqueid(self):
        cels = cel_1, cel_2 = [
            Mock(uniqueid=1, eventtype='CHAN_START'),
            Mock(uniqueid=1, eventtype='APP_START'),
        ]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(
            result, contains_exactly(contains_exactly(cel_1, cel_2), contains_exactly())
        )

    def test_split_caller_callee_cels_2_uniqueids(self):
        cels = cel_1, cel_2, cel_3, cel_4 = [
            Mock(uniqueid=1, eventtype='CHAN_START'),
            Mock(uniqueid=2, eventtype='CHAN_START'),
            Mock(uniqueid=1, eventtype='APP_START'),
            Mock(uniqueid=2, eventtype='ANSWER'),
        ]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(
            result,
            contains_exactly(
                contains_exactly(cel_1, cel_3), contains_exactly(cel_2, cel_4)
            ),
        )

    def test_split_caller_callee_cels_3_uniqueids(self):
        cels = cel_1, cel_2, cel_3 = [
            Mock(uniqueid=1, eventtype='CHAN_START'),
            Mock(uniqueid=2, eventtype='CHAN_START'),
            Mock(uniqueid=3, eventtype='CHAN_START'),
        ]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(
            result,
            contains_exactly(contains_exactly(cel_1), contains_exactly(cel_2, cel_3)),
        )


class TestAbstractCELInterpretor(TestCase):
    def setUp(self):
        class ConcreteCELInterpretor(AbstractCELInterpretor):
            def __init__(self):
                self.eventtype_map = {
                    CELEventType.chan_start: self.chan_start,
                    CELEventType.hangup: self.hangup,
                }

            chan_start = Mock()
            hangup = Mock()

        self.cel_interpretor = ConcreteCELInterpretor()

    def test_interpret_cels(self):
        cels = cel_1, cel_2, cel_3 = [Mock(id=34), Mock(id=35), Mock(id=36)]
        calls = sentinel.call_1, sentinel.call_2, sentinel.call_3, sentinel.call_4
        self.cel_interpretor.interpret_cel = Mock(side_effect=calls[1:])

        result = self.cel_interpretor.interpret_cels(cels, sentinel.call_1)

        self.cel_interpretor.interpret_cel.assert_any_call(cel_1, sentinel.call_1)
        self.cel_interpretor.interpret_cel.assert_any_call(cel_2, sentinel.call_2)
        self.cel_interpretor.interpret_cel.assert_any_call(cel_3, sentinel.call_3)
        assert_that(result, same_instance(sentinel.call_4))

    def test_interpret_cel_known_events(self):
        self._assert_that_interpret_cel_calls(
            self.cel_interpretor.chan_start, CELEventType.chan_start
        )
        self._assert_that_interpret_cel_calls(
            self.cel_interpretor.hangup, CELEventType.hangup
        )

    def test_interpret_cel_unknown_events(self):
        cel = Mock(eventtype=CELEventType.answer)

        result = self.cel_interpretor.interpret_cel(cel, sentinel.call)

        assert_that(result, same_instance(sentinel.call))
        assert_that(self.cel_interpretor.chan_start.call_count, equal_to(0))
        assert_that(self.cel_interpretor.hangup.call_count, equal_to(0))

    def _assert_that_interpret_cel_calls(self, function, eventtype):
        cel = Mock(eventtype=eventtype)
        call = Mock(RawCallLog)
        new_call = Mock(RawCallLog)
        function.return_value = new_call

        result = self.cel_interpretor.interpret_cel(cel, call)

        function.assert_called_once_with(cel, call)
        assert_that(result, equal_to(new_call))


class TestCallerCELInterpretor(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = CallerCELInterpretor()
        self.call = create_autospec(
            RawCallLog(),
            instance=True,
            interpret_caller_xivo_user_fwd=True,
            extension_filter=Mock(filter=lambda x: x),
            participants=[],
            participants_info=[],
            bridges={},
        )

    def test_interpret_cel_unknown_or_ignored_event(self):
        cel = Mock(eventtype='unknown_or_ignored_eventtype')
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_cel(cel, call)

        assert_that(result, equal_to(call))

    def test_interpret_xivo_user_fwd_regexp(self):
        cel = Mock(
            eventtype='XIVO_USER_FWD',
            extra='{"extra":"NUM:100,CONTEXT:internal,NAME:Bob Marley"}',
        )

        result = self.caller_cel_interpretor.interpret_xivo_user_fwd(cel, self.call)

        assert_that(result.requested_name, equal_to('Bob Marley'))
        assert_that(result.requested_internal_exten, equal_to('100'))
        assert_that(result.requested_internal_context, equal_to('internal'))

    def test_interpret_xivo_user_fwd_regexp_with_space(self):
        cel = Mock(
            eventtype='XIVO_USER_FWD',
            extra='{"extra":" NUM: 100 , CONTEXT: internal , NAME: Bob Marley "}',
        )

        result = self.caller_cel_interpretor.interpret_xivo_user_fwd(cel, self.call)

        assert_that(result.requested_name, equal_to('Bob Marley'))
        assert_that(result.requested_internal_exten, equal_to('100'))
        assert_that(result.requested_internal_context, equal_to('internal'))

    def test_interpret_xivo_user_fwd_regexp_with_value_before(self):
        cel = Mock(
            eventtype='XIVO_USER_FWD',
            extra='{"extra":"BEFORE:value,NUM:100,CONTEXT:internal,NAME:Bob Marley"}',
        )

        result = self.caller_cel_interpretor.interpret_xivo_user_fwd(cel, self.call)

        assert_that(result.requested_name, equal_to('Bob Marley'))
        assert_that(result.requested_internal_exten, equal_to('100'))
        assert_that(result.requested_internal_context, equal_to('internal'))

    def test_interpret_xivo_user_fwd_regexp_with_value_after(self):
        cel = Mock(
            eventtype='XIVO_USER_FWD',
            extra='{"extra":"NUM:100,CONTEXT:internal,NAME:Bob Marley,AFTER:value"}',
        )

        result = self.caller_cel_interpretor.interpret_xivo_user_fwd(cel, self.call)

        assert_that(result.requested_name, equal_to('Bob Marley'))
        assert_that(result.requested_internal_exten, equal_to('100'))
        assert_that(result.requested_internal_context, equal_to('internal'))

    def test_interpret_wazo_internal_call_has_destination_details(self):
        cel = Mock(
            eventtype='WAZO_CALL_LOG_DESTINATION',
            extra='{"extra":"type: user,uuid: c3f297bd-93e1-46f6-a309-79b320acb7fb,'
            'name: Willy Wonka"}',
        )

        result = self.caller_cel_interpretor.interpret_wazo_call_log_destination(
            cel, self.call
        )

        assert_that(
            result.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='user',
                ),
                has_properties(
                    destination_details_key='user_uuid',
                    destination_details_value='c3f297bd-93e1-46f6-a309-79b320acb7fb',
                ),
                has_properties(
                    destination_details_key='user_name',
                    destination_details_value='Willy Wonka',
                ),
            ),
        )

    def test_interpret_wazo_internal_call_has_requested_user_tag(self):
        cel = Mock(
            eventtype='WAZO_CALL_LOG_DESTINATION',
            extra='{"extra":"type: user,uuid: c3f297bd-93e1-46f6-a309-79b320acb7fb,'
            'name: Willy Wonka"}',
        )

        self.call.requested_type = None
        result = self.caller_cel_interpretor.interpret_wazo_call_log_destination(
            cel, self.call
        )

        assert_that(result.participants_info[0]['requested'], True)

    def test_interpret_wazo_incoming_call_has_destination_details(self):
        cel = Mock(
            eventtype='WAZO_CALL_LOG_DESTINATION',
            extra='{"extra":"type: user,uuid: cb79f29b-f69a-4b93-85c2-49dcce119a9f,'
            'name: Harry Potter"}',
        )

        result = self.caller_cel_interpretor.interpret_wazo_call_log_destination(
            cel, self.call
        )

        assert_that(
            result.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='user',
                ),
                has_properties(
                    destination_details_key='user_uuid',
                    destination_details_value='cb79f29b-f69a-4b93-85c2-49dcce119a9f',
                ),
                has_properties(
                    destination_details_key='user_name',
                    destination_details_value='Harry Potter',
                ),
            ),
        )

    def test_interpret_wazo_meeting_has_destination_details(self):
        cel = Mock(
            eventtype='WAZO_CALL_LOG_DESTINATION',
            extra='{"extra":"type: meeting,uuid: 9195757f-c381-4f38-b684-98fef848f48b,'
            'name: Meeting with Harry Potter"}',
        )

        result = self.caller_cel_interpretor.interpret_wazo_call_log_destination(
            cel, self.call
        )

        assert_that(
            result.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='meeting',
                ),
                has_properties(
                    destination_details_key='meeting_uuid',
                    destination_details_value='9195757f-c381-4f38-b684-98fef848f48b',
                ),
                has_properties(
                    destination_details_key='meeting_name',
                    destination_details_value='Meeting with Harry Potter',
                ),
            ),
        )

    def test_interpret_wazo_conference_has_destination_details(self):
        cel = Mock(
            eventtype='WAZO_CALL_LOG_DESTINATION',
            extra='{"extra":"type: conference,id: 1"}',
        )

        result = self.caller_cel_interpretor.interpret_wazo_call_log_destination(
            cel, self.call
        )

        assert_that(
            result.destination_details,
            contains_inanyorder(
                has_properties(
                    destination_details_key='type',
                    destination_details_value='conference',
                ),
                has_properties(
                    destination_details_key='conference_id',
                    destination_details_value='1',
                ),
            ),
        )

    def test_interpret_bridge_start_or_enter_identifies_bridge(self):
        cel = Mock(
            eventtype='BRIDGE_ENTER',
            extra='{"bridge_id": "some-uuid", "bridge_technology":"simple_bridge"}',
            channame='protocol/line-1',
            peer='protocol/line-2',
        )
        result = self.caller_cel_interpretor.interpret_bridge_start_or_enter(
            cel, self.call
        )
        assert_that(
            result,
            has_properties(
                bridges=has_entries(
                    {
                        'some-uuid': has_properties(
                            id='some-uuid',
                            technology='simple_bridge',
                            channels=contains_inanyorder(
                                'protocol/line-1', 'protocol/line-2'
                            ),
                        )
                    }
                )
            ),
        )


class TestParseKeyPairSequence(TestCase):
    def test_extraction(self):
        """Test parsing various key-value pair formats."""
        samples = [
            (
                'key1: value1,key2: value2,key3: value3',
                [('key1', 'value1'), ('key2', 'value2'), ('key3', 'value3')],
            ),
            (
                'user_uuid: some-uuid-value,tenant_uuid: another-uuid-value',
                [
                    ('user_uuid', 'some-uuid-value'),
                    ('tenant_uuid', 'another-uuid-value'),
                ],
            ),
            ('key: value', [('key', 'value')]),
            ('', []),
            ('no colons here', []),
            (
                'type: meeting,uuid: 8018307b-d5b6-4d70-9267-ca5cf708c342,name: Meeting A,B, other: foobar',
                [
                    ('type', 'meeting'),
                    ('uuid', '8018307b-d5b6-4d70-9267-ca5cf708c342'),
                    ('name', 'Meeting A,B'),
                    ('other', 'foobar'),
                ],
            ),
            (
                'type: meeting,uuid: 8018307b-d5b6-4d70-9267-ca5cf708c342,name: Meeting: AB,last: foobaz',
                [
                    ('type', 'meeting'),
                    ('uuid', '8018307b-d5b6-4d70-9267-ca5cf708c342'),
                    ('name', 'Meeting: AB'),
                    ('last', 'foobaz'),
                ],
            ),
        ]

        for text, expected in samples:
            result = parse_key_pair_sequence(text)
            assert_that(result, equal_to(expected), f'Failed for {text}')


class TestExtractCallLogDestinationVariables(TestCase):
    def test_extraction(self):
        samples = [
            (
                {
                    'extra': 'type: user,uuid: 0890d326-d4a4-47d0-894b-16201ae1d911,name: Alice'
                },
                {
                    'type': 'user',
                    'uuid': '0890d326-d4a4-47d0-894b-16201ae1d911',
                    'name': 'Alice',
                },
            ),
            (
                {
                    'extra': 'type: meeting,uuid: 8018307b-d5b6-4d70-9267-ca5cf708c342,name: Meeting A,B'
                },
                {
                    'type': 'meeting',
                    'uuid': '8018307b-d5b6-4d70-9267-ca5cf708c342',
                    'name': 'Meeting A,B',
                },
            ),
            (
                {
                    "extra": "type: meeting,uuid: e2ff6005-ea3f-4e67-a760-45d20e8a8a16,name: Test meeting"
                },
                {
                    'type': 'meeting',
                    'uuid': 'e2ff6005-ea3f-4e67-a760-45d20e8a8a16',
                    'name': 'Test meeting',
                },
            ),
            (
                {
                    'extra': 'type: meeting,uuid: 8018307b-d5b6-4d70-9267-ca5cf708c342,name: Meeting: AB'
                },
                {
                    'type': 'meeting',
                    'uuid': '8018307b-d5b6-4d70-9267-ca5cf708c342',
                    'name': 'Meeting: AB',
                },
            ),
            (
                {
                    'extra': 'type: group,id: 7,name: grp-tenant-9fa27e38-907a-4345-a5b5-6f63b250bcf0'
                },
                {
                    'type': 'group',
                    'id': '7',
                    'name': 'grp-tenant-9fa27e38-907a-4345-a5b5-6f63b250bcf0',
                },
            ),
            (
                {
                    'extra': 'type: queue,id: 2,label: My Queue Name,tenant_uuid: 82f60c78-fc94-4936-b3fb-7b276c69df9d'
                },
                {
                    'type': 'queue',
                    'id': '2',
                    'label': 'My Queue Name',
                    'tenant_uuid': '82f60c78-fc94-4936-b3fb-7b276c69df9d',
                },
            ),
        ]

        for extra, expected in samples:
            result = extract_key_value_pairs_as_dict(extra)
            assert_that(result, equal_to(expected), f'Failed for {extra}')

        with raises(InvalidCallLogException):
            extract_key_value_pairs_as_dict({'extra': 'not a valid extra'})


class TestCalleeCELInterpretor(TestCase):
    def setUp(self):
        self.interpretor = CalleeCELInterpretor()

    def test_interpret_chan_end_uses_latest_event_time(self):
        call_start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        non_answering_mobile_chan_end = datetime(
            2026, 1, 1, 10, 0, 1, tzinfo=timezone.utc
        )
        real_callee_chan_end = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        recording = Recording(start_time=call_start)
        call = RawCallLog()
        call.recordings = [recording]

        self.interpretor.interpret_chan_end(
            Mock(eventtime=non_answering_mobile_chan_end), call
        )
        self.interpretor.interpret_chan_end(Mock(eventtime=real_callee_chan_end), call)

        assert_that(recording.end_time, equal_to(real_callee_chan_end))

    def test_interpret_chan_end_does_not_override_mixmonitor_stop(self):
        call_start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mixmonitor_stop_time = datetime(2026, 1, 1, 10, 3, 0, tzinfo=timezone.utc)
        chan_end_time = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        recording = Recording(mixmonitor_id='0x01', start_time=call_start)
        call = RawCallLog()
        call.recordings = [recording]

        self.interpretor.interpret_mixmonitor_stop(
            Mock(extra='{"mixmonitor_id": "0x01"}', eventtime=mixmonitor_stop_time),
            call,
        )
        self.interpretor.interpret_chan_end(Mock(eventtime=chan_end_time), call)

        assert_that(recording.end_time, equal_to(mixmonitor_stop_time))

    def test_interpret_app_start_voicemail_sets_reached_voicemail(self):
        # A VoiceMail() on the callee channel (e.g. blind transfer to voicemail)
        # must be detected, since it is dispatched to the callee interpretor.
        cel = Mock(
            eventtype=CELEventType.app_start,
            appname='VoiceMail',
            appdata='1006@default,u',
        )
        call = RawCallLog()

        self.interpretor.interpret_cel(cel, call)

        assert_that(call.reached_voicemail, equal_to(True))
        assert_that(call.voicemail_number, equal_to('1006'))
        assert_that(call.voicemail_context, equal_to('default'))

    def test_interpret_app_start_voicemailmain_not_a_redirection(self):
        cel = Mock(
            eventtype=CELEventType.app_start,
            appname='VoiceMailMain',
            appdata='1006@default',
        )
        call = RawCallLog()

        self.interpretor.interpret_cel(cel, call)

        assert_that(call.reached_voicemail, equal_to(False))

    def test_interpret_app_start_multi_mailbox_uses_first(self):
        # A custom dialplan may pass Asterisk's "&"-separated multi-mailbox
        # syntax; the CDR is attributed to the first mailbox, not a garbage
        # context.
        cel = Mock(
            eventtype=CELEventType.app_start,
            appname='VoiceMail',
            appdata='1001@default&1002@other,u',
        )
        call = RawCallLog()

        self.interpretor.interpret_cel(cel, call)

        assert_that(call.reached_voicemail, equal_to(True))
        assert_that(call.voicemail_number, equal_to('1001'))
        assert_that(call.voicemail_context, equal_to('default'))


class TestLocalOriginateCELInterpretor(TestCase):
    def setUp(self):
        self.interpretor = LocalOriginateCELInterpretor()

    def _cel(self, eventtype, uniqueid, **kwargs):
        when = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        defaults = {
            'eventtype': eventtype,
            'uniqueid': uniqueid,
            'eventtime': when,
            'cid_name': '',
            'cid_num': '',
            'channame': f'PJSIP/{uniqueid}-00000001',
        }
        defaults.update(kwargs)
        return Mock(**defaults)

    def test_originated_call_to_voicemail_sets_reached_voicemail(self):
        # A click-to-call/API-originated call (local channel pair + source +
        # destination) that ends in voicemail runs VoiceMail() on one of its
        # channels; it must be detected like the caller/callee paths.
        cels = [
            self._cel('CHAN_START', 'local1', channame='Local/1@a-00000001;1'),
            self._cel('CHAN_START', 'local2', channame='Local/1@a-00000001;2'),
            self._cel('CHAN_START', 'source', cid_name='Bob', cid_num='1006'),
            self._cel('ANSWER', 'source', cid_name='Bob', cid_num='1006'),
            self._cel('ANSWER', 'local2', cid_num='1006'),
            self._cel(
                'APP_START', 'dest', appname='VoiceMail', appdata='1006@default,u'
            ),
            self._cel('CHAN_END', 'source'),
        ]
        call = RawCallLog()

        self.interpretor.interpret_cels(cels, call)

        assert_that(call.reached_voicemail, equal_to(True))
        assert_that(call.voicemail_number, equal_to('1006'))
        assert_that(call.voicemail_context, equal_to('default'))
        # no destination answered, so the call stays unanswered (voicemail)
        assert_that(call.date_answer, equal_to(None))

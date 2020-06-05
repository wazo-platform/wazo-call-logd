# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from hamcrest import has_properties

from .helpers.base import raw_cels, RawCelIntegrationTest


class TestCallFromMobile(RawCelIntegrationTest):
    @raw_cels(
        '''\
eventtype    | eventtime                  | cid_name         |   cid_num | exten     | context     | channame                           |      uniqueid |      linkedid
LINKEDID_END | 2017-01-03 12:11:19.520075 |                  | **9742309 |           | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
CHAN_END     | 2017-01-03 12:11:19.518633 |                  | **9742309 |           | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
HANGUP       | 2017-01-03 12:11:19.517049 |                  | **9742309 |           | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
BRIDGE_EXIT  | 2017-01-03 12:11:19.515043 |                  | **9742309 |           | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
CHAN_END     | 2017-01-03 12:11:19.514251 | Charliez Chaplin |       103 |           | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
HANGUP       | 2017-01-03 12:11:19.51256  | Charliez Chaplin |       103 |           | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
BRIDGE_EXIT  | 2017-01-03 12:11:19.494428 | Charliez Chaplin |       103 |           | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
CHAN_END     | 2017-01-03 12:11:17.278862 | Charliez Chaplin |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
HANGUP       | 2017-01-03 12:11:17.275369 | Charliez Chaplin |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
CHAN_END     | 2017-01-03 12:11:17.270667 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
HANGUP       | 2017-01-03 12:11:17.265634 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
BRIDGE_EXIT  | 2017-01-03 12:11:17.260383 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
BRIDGE_ENTER | 2017-01-03 12:11:17.256134 | Charliez Chaplin |       103 |           | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
BRIDGE_EXIT  | 2017-01-03 12:11:17.253204 | Charliez Chaplin |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
BRIDGE_EXIT  | 2017-01-03 12:11:17.249432 | Charliez Chaplin |       103 |           | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
BRIDGE_ENTER | 2017-01-03 12:11:17.244022 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
BRIDGE_ENTER | 2017-01-03 12:11:17.225257 | Charliez Chaplin |       103 |           | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
ANSWER       | 2017-01-03 12:11:16.957521 | Charliez Chaplin |       103 | s         | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
CHAN_START   | 2017-01-03 12:11:14.173125 | Charliez Chaplin |       103 | s         | default     | SIP/rku3uo-00000009                | 1483463474.23 | 1483463468.20
APP_START    | 2017-01-03 12:11:14.124641 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
BRIDGE_ENTER | 2017-01-03 12:11:13.431518 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
BRIDGE_ENTER | 2017-01-03 12:11:13.423447 |                  | **9742309 |           | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
ANSWER       | 2017-01-03 12:11:13.418892 |                  |           | **9742309 | default     | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
ANSWER       | 2017-01-03 12:11:13.405255 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
ANSWER       | 2017-01-03 12:11:13.354536 |                  | **9742309 | dial      | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
CHAN_START   | 2017-01-03 12:11:08.823609 |                  |           | s         | from-extern | SIP/dev_32-00000008                | 1483463468.22 | 1483463468.20
APP_START    | 2017-01-03 12:11:08.818175 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
XIVO_OUTCALL | 2017-01-03 12:11:08.812805 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
CHAN_START   | 2017-01-03 12:11:08.80159  |                  |           | **9742309 | default     | Local/**9742309@default-00000005;2 | 1483463468.21 | 1483463468.20
CHAN_START   | 2017-01-03 12:11:08.574072 |                  |           | **9742309 | default     | Local/**9742309@default-00000005;1 | 1483463468.20 | 1483463468.20
        '''
    )
    def test_answered_internal_calls(self):
        self._assert_last_call_log_matches(
            '1483463468.20',
            has_properties(
                date=datetime.fromisoformat('2017-01-03 12:11:08.574072+00:00'),
                date_answer=datetime.fromisoformat('2017-01-03 12:11:17.256134+00:00'),
                date_end=datetime.fromisoformat('2017-01-03 12:11:19.518633+00:00'),
                source_exten='**9742309',
                destination_exten='103',
                destination_name='Charliez Chaplin',
                source_line_identity='sip/dev_32',
                destination_line_identity='sip/rku3uo',
            ),
        )

    @raw_cels(
        '''\
eventtype    | eventtime                  | cid_name         |   cid_num | exten     | context     | channame                           |      uniqueid |      linkedid
LINKEDID_END | 2017-01-03 12:12:45.925395 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000006;1 | 1483463556.24 | 1483463556.24
CHAN_END     | 2017-01-03 12:12:45.863506 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000006;1 | 1483463556.24 | 1483463556.24
HANGUP       | 2017-01-03 12:12:45.856138 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000006;1 | 1483463556.24 | 1483463556.24
CHAN_END     | 2017-01-03 12:12:45.852772 | Charliez Chaplin |       103 | s         | default     | SIP/rku3uo-0000000b                | 1483463562.27 | 1483463556.24
HANGUP       | 2017-01-03 12:12:45.849804 | Charliez Chaplin |       103 | s         | default     | SIP/rku3uo-0000000b                | 1483463562.27 | 1483463556.24
CHAN_END     | 2017-01-03 12:12:45.837273 | Charliez Chaplin |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
HANGUP       | 2017-01-03 12:12:45.834283 | Charliez Chaplin |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
BRIDGE_EXIT  | 2017-01-03 12:12:45.83286  | Charliez Chaplin |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
CHAN_END     | 2017-01-03 12:12:45.830542 |                  | **9742309 |           | from-extern | SIP/dev_32-0000000a                | 1483463556.26 | 1483463556.24
HANGUP       | 2017-01-03 12:12:45.827259 |                  | **9742309 |           | from-extern | SIP/dev_32-0000000a                | 1483463556.26 | 1483463556.24
BRIDGE_EXIT  | 2017-01-03 12:12:45.800451 |                  | **9742309 |           | from-extern | SIP/dev_32-0000000a                | 1483463556.26 | 1483463556.24
CHAN_START   | 2017-01-03 12:12:42.117621 | Charliez Chaplin |       103 | s         | default     | SIP/rku3uo-0000000b                | 1483463562.27 | 1483463556.24
APP_START    | 2017-01-03 12:12:42.104034 | **9742309        | **9742309 | s         | user        | Local/**9742309@default-00000006;1 | 1483463556.24 | 1483463556.24
BRIDGE_ENTER | 2017-01-03 12:12:41.86174  | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
BRIDGE_ENTER | 2017-01-03 12:12:41.859801 |                  | **9742309 |           | from-extern | SIP/dev_32-0000000a                | 1483463556.26 | 1483463556.24
ANSWER       | 2017-01-03 12:12:41.856908 |                  |           | **9742309 | default     | Local/**9742309@default-00000006;1 | 1483463556.24 | 1483463556.24
ANSWER       | 2017-01-03 12:12:41.854647 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
ANSWER       | 2017-01-03 12:12:41.820153 |                  | **9742309 | dial      | from-extern | SIP/dev_32-0000000a                | 1483463556.26 | 1483463556.24
CHAN_START   | 2017-01-03 12:12:36.833287 |                  |           | s         | from-extern | SIP/dev_32-0000000a                | 1483463556.26 | 1483463556.24
APP_START    | 2017-01-03 12:12:36.829893 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
XIVO_OUTCALL | 2017-01-03 12:12:36.794943 | 103              |       103 | dial      | outcall     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
CHAN_START   | 2017-01-03 12:12:36.779439 |                  |           | **9742309 | default     | Local/**9742309@default-00000006;2 | 1483463556.25 | 1483463556.24
CHAN_START   | 2017-01-03 12:12:36.702755 |                  |           | **9742309 | default     | Local/**9742309@default-00000006;1 | 1483463556.24 | 1483463556.24
    '''
    )
    def test_non_answered_call(self):
        self._assert_last_call_log_matches(
            '1483463556.24',
            has_properties(
                date=datetime.fromisoformat('2017-01-03 12:12:36.702755+00:00'),
                date_answer=None,
                date_end=datetime.fromisoformat('2017-01-03 12:12:45.830542+00:00'),
                source_exten='**9742309',
                destination_exten='103',
                source_line_identity='sip/dev_32',
            ),
        )

    @raw_cels(
        '''\
        eventtype    | eventtime                  | cid_name  | cid_num   | exten     | context     | channame                           |      uniqueid |      linkedid
        LINKEDID_END | 2017-01-03 12:14:03.860335 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        CHAN_END     | 2017-01-03 12:14:03.856841 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        HANGUP       | 2017-01-03 12:14:03.855403 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        BRIDGE_EXIT  | 2017-01-03 12:14:03.852642 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        CHAN_END     | 2017-01-03 12:14:03.851136 |           | **101     |           | from-extern | SIP/dev_32-0000000d                | 1483463635.31 | 1483463631.28
        HANGUP       | 2017-01-03 12:14:03.849594 |           | **101     |           | from-extern | SIP/dev_32-0000000d                | 1483463635.31 | 1483463631.28
        BRIDGE_EXIT  | 2017-01-03 12:14:03.812899 |           | **101     |           | from-extern | SIP/dev_32-0000000d                | 1483463635.31 | 1483463631.28
        CHAN_END     | 2017-01-03 12:13:56.24602  | **9742309 | **9742309 | dial      | outcall     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        HANGUP       | 2017-01-03 12:13:56.244172 | **9742309 | **9742309 | dial      | outcall     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        CHAN_END     | 2017-01-03 12:13:56.233073 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        HANGUP       | 2017-01-03 12:13:56.229305 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        BRIDGE_EXIT  | 2017-01-03 12:13:56.224343 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        BRIDGE_ENTER | 2017-01-03 12:13:56.222543 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        BRIDGE_EXIT  | 2017-01-03 12:13:56.220438 | **9742309 | **9742309 | dial      | outcall     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        BRIDGE_EXIT  | 2017-01-03 12:13:56.206731 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        BRIDGE_ENTER | 2017-01-03 12:13:55.979142 | **9742309 | **9742309 | dial      | outcall     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        BRIDGE_ENTER | 2017-01-03 12:13:55.977583 |           | **101     |           | from-extern | SIP/dev_32-0000000d                | 1483463635.31 | 1483463631.28
        ANSWER       | 2017-01-03 12:13:55.963168 |           | **101     | dial      | from-extern | SIP/dev_32-0000000d                | 1483463635.31 | 1483463631.28
        CHAN_START   | 2017-01-03 12:13:55.82841  |           |           | s         | from-extern | SIP/dev_32-0000000d                | 1483463635.31 | 1483463631.28
        APP_START    | 2017-01-03 12:13:55.824672 | **9742309 | **9742309 | dial      | outcall     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        XIVO_OUTCALL | 2017-01-03 12:13:55.774422 | **9742309 | **9742309 | dial      | outcall     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        BRIDGE_ENTER | 2017-01-03 12:13:55.751543 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        BRIDGE_ENTER | 2017-01-03 12:13:55.713432 |           | **9742309 |           | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        ANSWER       | 2017-01-03 12:13:55.70967  |           |           | **9742309 | default     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
        ANSWER       | 2017-01-03 12:13:55.708058 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        ANSWER       | 2017-01-03 12:13:55.674715 |           | **9742309 | dial      | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        CHAN_START   | 2017-01-03 12:13:51.626849 |           |           | s         | from-extern | SIP/dev_32-0000000c                | 1483463631.30 | 1483463631.28
        APP_START    | 2017-01-03 12:13:51.623976 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        XIVO_OUTCALL | 2017-01-03 12:13:51.563675 | **101     | **101     | dial      | outcall     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        CHAN_START   | 2017-01-03 12:13:51.537507 |           |           | **9742309 | default     | Local/**9742309@default-00000007;2 | 1483463631.29 | 1483463631.28
        CHAN_START   | 2017-01-03 12:13:51.476828 |           |           | **9742309 | default     | Local/**9742309@default-00000007;1 | 1483463631.28 | 1483463631.28
    '''
    )
    def test_answered_outgoing_calls(self):
        self._assert_last_call_log_matches(
            '1483463631.28',
            has_properties(
                date=datetime.fromisoformat('2017-01-03 12:13:51.476828+00:00'),
                date_answer=datetime.fromisoformat('2017-01-03 12:13:55.977583+00:00'),
                date_end=datetime.fromisoformat('2017-01-03 12:14:03.856841+00:00'),
                source_exten='**9742309',
                destination_exten='**101',
                source_line_identity='sip/dev_32',
                destination_line_identity='sip/dev_32',
            ),
        )

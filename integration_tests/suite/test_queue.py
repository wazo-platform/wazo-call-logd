# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import has_properties

from .helpers.base import RawCelIntegrationTest, raw_cels


class TestCallToQueue(RawCelIntegrationTest):
    @raw_cels(
        '''
        eventtype                 |           eventtime           | cid_name | cid_num | cid_ani | cid_dnid | exten  |                           context                            |        channame         |     appname     |                       appdata                       | amaflags |   uniqueid   |   linkedid   | peer |                                    extra
        --------------------------+-------------------------------+----------+---------+---------+----------+--------+--------------------------------------------------------------+-------------------------+-----------------+-----------------------------------------------------+----------+--------------+--------------+------+-----------------------------------------------------------------------------
        CHAN_START                | 2025-08-11 14:54:56.531176-04 | Fern     | 10006   |         |          | 30001  | ctx-pcmdev00de-internal-a25ef16e-faaf-41ad-b1ad-aa2d715b6c05 | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        WAZO_CALL_LOG_DESTINATION | 2025-08-11 14:54:56.752166-04 | Fern     | 10006   | 10006   |          | s      | queue                                                        | PJSIP/yeFKZg6L-00000003 | CELGenUserEvent | WAZO_CALL_LOG_DESTINATION,type: queue,id: 2,label: My Queue Name,tenant_uuid: 82f60c78-fc94-4936-b3fb-7b276c69df9d |        3 |  1754938496.0 | 1754938496.0 |           | {"extra":"type: queue,id: 2,label: My Queue Name,tenant_uuid: 82f60c78-fc94-4936-b3fb-7b276c69df9d"}
        ANSWER                    | 2025-08-11 14:54:57.064198-04 | Fern     | 10006   | 10006   | 30001    | pickup | xivo-pickup                                                  | PJSIP/yeFKZg6L-00000000 | Answer          |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        APP_START                 | 2025-08-11 14:54:58.725743-04 | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 | Queue           | q-11668931,iC,,,,,wazo-queue-answered,,,            |        3 | 1754938496.0 | 1754938496.0 |      |
        HANGUP                    | 2025-08-11 14:55:10.87219-04  | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      | {"hangupcause":16,"hangupsource":"PJSIP/yeFKZg6L-00000000","dialstatus":""}
        CHAN_END                  | 2025-08-11 14:55:10.87219-04  | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |
        LINKEDID_END              | 2025-08-11 14:55:10.87219-04  | Fern     | 10006   | 10006   | 30001    | s      | queue                                                        | PJSIP/yeFKZg6L-00000000 |                 |                                                     |        3 | 1754938496.0 | 1754938496.0 |      |

        '''
    )
    def test_call_to_queue_no_members(self):
        self._assert_last_call_log_matches(
            '1754938496.0',
            has_properties(
                source_name='Fern',
                source_exten='10006',
                requested_exten='30001',
                destination_exten='30001',
                destination_name='My Queue Name',
                destination_participant=None,
            ),
        )

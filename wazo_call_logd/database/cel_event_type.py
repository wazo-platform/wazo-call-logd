# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class CELEventType(object):
    answer = 'ANSWER'
    app_end = 'APP_END'
    app_start = 'APP_START'
    attended_transfer = 'ATTENDEDTRANSFER'
    blind_transfer = 'BLINDTRANSFER'
    bridge_end = 'BRIDGE_END'  # removed in asterisk 12
    bridge_start = 'BRIDGE_START'  # removed in asterisk 12
    bridge_enter = 'BRIDGE_ENTER'
    bridge_exit = 'BRIDGE_EXIT'
    chan_start = 'CHAN_START'
    chan_end = 'CHAN_END'
    forward = 'FORWARD'
    hangup = 'HANGUP'
    linkedid_end = 'LINKEDID_END'
    mixmonitor_start = 'MIXMONITOR_START'
    mixmonitor_stop = 'MIXMONITOR_STOP'
    pickup = 'PICKUP'
    transfer = 'TRANSFER'  # removed in asterisk 12

    # CELGenUserEvent
    wazo_meeting_name = 'WAZO_MEETING_NAME'
    xivo_from_s = 'XIVO_FROM_S'
    xivo_incall = 'XIVO_INCALL'
    xivo_outcall = 'XIVO_OUTCALL'
    xivo_user_fwd = 'XIVO_USER_FWD'

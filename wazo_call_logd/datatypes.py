# Copyright 2023-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Type definitions and data wrappers
"""

from enum import Enum
from typing import Literal

CallDirection = Literal['internal', 'inbound', 'outbound']
OrderDirection = Literal['asc', 'desc']


class CallStatus(Enum):
    ANSWERED = 'answered'
    BLOCKED = 'blocked'
    UNKNOWN = 'unknown'

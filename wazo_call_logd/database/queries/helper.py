# Copyright 2021-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager

from ..helpers import wait_is_ready
from .base import BaseDAO


class HelperDAO(BaseDAO):
    @contextmanager
    def db_ready(self):
        with self.new_session() as session:
            connection = session.connection()
            wait_is_ready(connection)
            yield

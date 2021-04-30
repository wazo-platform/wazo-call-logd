# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
from .base import BaseDAO
from ..database import wait_is_ready


class HelperDAO(BaseDAO):
    @contextmanager
    def db_ready(self):
        with self.new_session() as session:
            wait_is_ready(session)
            yield

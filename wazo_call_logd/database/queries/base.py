# Copyright 2020-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import exc
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.orm import scoped_session

from wazo_call_logd.exceptions import DatabaseServiceUnavailable


class BaseDAO:
    def __init__(self, Session: scoped_session):
        self._Session = Session

    @contextmanager
    def new_session(self) -> Iterator[BaseSession]:
        session = self._Session()
        try:
            yield session
            session.commit()
        except exc.OperationalError:
            session.rollback()
            raise DatabaseServiceUnavailable()
        except BaseException:
            session.rollback()
            raise
        finally:
            self._Session.remove()

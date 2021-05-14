# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


def new_db_session(db_uri):
    _Session = scoped_session(sessionmaker())
    engine = create_engine(db_uri, pool_pre_ping=True)
    _Session.configure(bind=engine)
    return _Session


@retry(
    stop=stop_after_attempt(60 * 5),
    wait=wait_fixed(1),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def wait_is_ready(connection):
    try:
        # Try to create session to check if DB is awake
        connection.execute('SELECT 1')
    except Exception as e:
        logger.warning('fail to connect to the database: %s', e)
        raise

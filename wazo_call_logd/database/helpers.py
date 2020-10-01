# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker


def new_db_session(db_uri):
    _Session = scoped_session(sessionmaker())
    engine = create_engine(db_uri, pool_pre_ping=True)
    _Session.configure(bind=engine)
    return _Session

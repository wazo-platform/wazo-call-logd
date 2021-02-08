# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    timedelta as td,
    timezone as tz,
)
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Text,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import UUIDType, generic_repr

Base = declarative_base()


@generic_repr
class Recording(Base):

    __tablename__ = 'call_logd_recording'

    uuid = Column(
        UUIDType(),
        server_default=text('uuid_generate_v4()'),
        primary_key=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    path = Column(Text)
    call_log_id = Column(Integer(), nullable=False)

    @property
    def filename(self):
        offset = self.start_time.utcoffset() or td(seconds=0)
        date_utc = (self.start_time - offset).replace(tzinfo=tz.utc)
        utc_start = date_utc.strftime('%Y-%m-%dT%H:%M:%SUTC')
        return '{start}-{cdr_id}-{uuid}.wav'.format(
            start=utc_start,
            cdr_id=self.call_log_id,
            uuid=self.uuid,
        )

    def __init__(self, mixmonitor_id=None, *args, **kwargs):
        # NOTE(fblackburn): Used to track recording on generation
        self.mixmonitor_id = mixmonitor_id
        super().__init__(*args, **kwargs)

    @property
    def deleted(self):
        return self.path is None

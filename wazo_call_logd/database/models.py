# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    timedelta as td,
    timezone as tz,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, CheckConstraint, ForeignKey, Index
from sqlalchemy.sql import case, select, text
from sqlalchemy.types import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy_utils import UUIDType, generic_repr

from xivo_dao.helpers.uuid import new_uuid

Base = declarative_base()


@generic_repr
class CallLog(Base):

    __tablename__ = 'call_logd_call_log'

    id = Column(Integer, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), nullable=False)
    date_answer = Column(DateTime(timezone=True))
    date_end = Column(DateTime(timezone=True))
    tenant_uuid = Column(UUIDType, nullable=False)
    source_name = Column(String(255))
    source_exten = Column(String(255))
    source_internal_exten = Column(Text)
    source_internal_context = Column(Text)
    source_line_identity = Column(String(255))
    requested_name = Column(Text)
    requested_exten = Column(String(255))
    requested_context = Column(String(255))
    requested_internal_exten = Column(Text)
    requested_internal_context = Column(Text)
    destination_name = Column(String(255))
    destination_exten = Column(String(255))
    destination_internal_exten = Column(Text)
    destination_internal_context = Column(Text)
    destination_line_identity = Column(String(255))
    direction = Column(String(255))
    user_field = Column(String(255))

    participants = relationship('CallLogParticipant', cascade='all,delete-orphan')
    participant_user_uuids = association_proxy('participants', 'user_uuid')

    source_participant = relationship(
        'CallLogParticipant',
        primaryjoin='''and_(
            CallLogParticipant.call_log_id == CallLog.id,
            CallLogParticipant.role == 'source'
        )''',
        viewonly=True,
        uselist=False,
    )
    source_user_uuid = association_proxy('source_participant', 'user_uuid')
    source_line_id = association_proxy('source_participant', 'line_id')

    destination_participant = relationship(
        'CallLogParticipant',
        primaryjoin='''and_(
            CallLogParticipant.call_log_id == CallLog.id,
            CallLogParticipant.role == 'destination'
        )''',
        order_by='desc(CallLogParticipant.answered)',
        viewonly=True,
        uselist=False,
    )
    destination_user_uuid = association_proxy('destination_participant', 'user_uuid')
    destination_line_id = association_proxy('destination_participant', 'line_id')

    cel_ids = []

    __table_args__ = (
        CheckConstraint(
            direction.in_(['inbound', 'internal', 'outbound']),
            name='call_logd_call_log_direction_check',
        ),
    )


class CallLogParticipant(Base):

    __tablename__ = 'call_logd_call_log_participant'
    __table_args__ = (
        Index('call_logd_call_log_participant__idx__user_uuid', 'user_uuid'),
    )

    uuid = Column(UUIDType, default=new_uuid, primary_key=True)
    call_log_id = Column(
        Integer,
        ForeignKey(
            'call_logd_call_log.id',
            name='call_logd_call_log_participant_call_log_id_fkey',
            ondelete='CASCADE',
        )
    )
    user_uuid = Column(UUIDType, nullable=False)
    line_id = Column(Integer)
    role = Column(
        Enum(
            'source',
            'destination',
            name='call_logd_call_log_participant_role',
        ),
        nullable=False,
    )
    tags = Column(ARRAY(String(128)), nullable=False, server_default='{}')
    answered = Column(Boolean, nullable=False, server_default='false')

    call_log = relationship(
        'CallLog',
        primaryjoin='CallLog.id == CallLogParticipant.call_log_id',
        uselist=False,
    )

    @hybrid_property
    def peer_exten(self):
        if self.role == 'source':
            return self.call_log.requested_exten
        else:
            return self.call_log.source_exten

    @peer_exten.expression
    def peer_exten(cls):
        return case(
            [
                (
                    cls.role == 'source',
                    select([CallLog.requested_exten]).where(
                        cls.call_log_id == CallLog.id
                    ).as_scalar()
                )
            ],
            else_=select([CallLog.source_exten]).where(
                cls.call_log_id == CallLog.id
            ).as_scalar()
        )


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
        utc_start = date_utc.strftime('%Y-%m-%dT%H_%M_%SUTC')
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

# Copyright 2021-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import timedelta as td
from datetime import timezone as tz

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from sqlalchemy.schema import CheckConstraint, Column, ForeignKey, Index
from sqlalchemy.sql import and_, case, select, text
from sqlalchemy.types import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy_utils import UUIDType, generic_repr

Base = declarative_base()


@generic_repr
class Tenant(Base):
    __tablename__ = 'call_logd_tenant'

    uuid = Column(UUIDType, primary_key=True)


@generic_repr
class CallLog(Base):
    __tablename__ = 'call_logd_call_log'

    id = Column(Integer, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), nullable=False)
    date_answer = Column(DateTime(timezone=True))
    date_end = Column(DateTime(timezone=True))
    tenant_uuid = Column(
        UUIDType,
        ForeignKey(
            'call_logd_tenant.uuid',
            name='call_logd_call_log_tenant_uuid_fkey',
            ondelete='CASCADE',
        ),
        nullable=False,
    )
    source_name = Column(String(255))
    source_exten = Column(String(255))
    source_internal_name = Column(Text)
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
    conversation_id = Column(String(255))

    recordings = relationship(
        'Recording',
        order_by='Recording.start_time',
        cascade='all,delete-orphan',
    )
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

    destination_details = relationship(
        'Destination',
        primaryjoin='''and_(
            Destination.call_log_id == CallLog.id,
        )''',
        uselist=True,
        cascade='all,delete-orphan',
        passive_deletes=True,
        lazy='subquery',
    )

    @property
    def destination_details_dict(self):
        return {
            row.destination_details_key: row.destination_details_value
            for row in self.destination_details
        }

    destination_participant = relationship(
        'CallLogParticipant',
        primaryjoin='''and_(
            CallLogParticipant.call_log_id == CallLog.id,
            CallLogParticipant.role == 'destination'
        )''',
        order_by='desc(CallLogParticipant.answered), desc(CallLogParticipant.user_uuid)',
        viewonly=True,
        uselist=False,
    )
    destination_user_uuid = association_proxy('destination_participant', 'user_uuid')
    destination_line_id = association_proxy('destination_participant', 'line_id')

    cel_ids = []

    __table_args__ = (
        Index('call_logd_call_log__idx__conversation_id', 'conversation_id'),
        CheckConstraint(
            direction.in_(['inbound', 'internal', 'outbound']),
            name='call_logd_call_log_direction_check',
        ),
    )

    @hybrid_property
    def requested_user_uuid(self):
        for participant in self.participants:
            if participant.requested:
                return participant.user_uuid
        return None

    @requested_user_uuid.expression
    def requested_user_uuid(cls):
        return (
            select([CallLogParticipant.user_uuid])
            .where(
                and_(
                    CallLogParticipant.requested.is_(True),
                    CallLogParticipant.call_log_id == cls.id,
                )
            )
            .as_scalar()
        )


@generic_repr
class Destination(Base):
    __tablename__ = 'call_logd_call_log_destination'

    uuid = Column(
        UUIDType,
        server_default=text('uuid_generate_v4()'),
        primary_key=True,
    )

    call_log_id = Column(
        Integer,
        ForeignKey(
            'call_logd_call_log.id',
            name='call_logd_call_log_destination_call_log_id_fkey',
            ondelete='CASCADE',
        ),
    )

    destination_details_key = Column(String(32), nullable=False)
    destination_details_value = Column(String(255), nullable=False)

    __table_args__ = (
        Index('call_logd_call_log_destination__idx__uuid', 'uuid'),
        Index('call_logd_call_log_destination__idx__call_log_id', 'call_log_id'),
        CheckConstraint(
            destination_details_key.in_(
                [
                    'type',
                    'user_uuid',
                    'user_name',
                    'meeting_uuid',
                    'meeting_name',
                    'conference_id',
                    'group_label',
                    'group_id',
                    'queue_name',
                    'queue_id',
                ]
            ),
            name='call_logd_call_log_destination_details_key_check',
        ),
    )


@generic_repr
class CallLogParticipant(Base):
    __tablename__ = 'call_logd_call_log_participant'
    __table_args__ = (
        Index('call_logd_call_log_participant__idx__user_uuid', 'user_uuid'),
        Index('call_logd_call_log_participant__idx__call_log_id', 'call_log_id'),
    )

    uuid = Column(
        UUIDType,
        server_default=text('uuid_generate_v4()'),
        primary_key=True,
    )
    call_log_id = Column(
        Integer,
        ForeignKey(
            'call_logd_call_log.id',
            name='call_logd_call_log_participant_call_log_id_fkey',
            ondelete='CASCADE',
        ),
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
    tags = Column(
        MutableList.as_mutable(ARRAY(String(128))), nullable=False, server_default='{}'
    )
    answered = Column(Boolean, nullable=False, server_default='false')
    requested = Column(Boolean, nullable=False, server_default='false')

    call_log = relationship('CallLog', uselist=False, viewonly=True)

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
                    select([CallLog.requested_exten])
                    .where(cls.call_log_id == CallLog.id)
                    .as_scalar(),
                )
            ],
            else_=select([CallLog.source_exten])
            .where(cls.call_log_id == CallLog.id)
            .as_scalar(),
        )


@generic_repr
class Recording(Base):
    __tablename__ = 'call_logd_recording'
    __table_args__ = (Index('call_logd_recording__idx__call_log_id', 'call_log_id'),)

    uuid = Column(
        UUIDType(),
        server_default=text('uuid_generate_v4()'),
        primary_key=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    path = Column(Text)
    call_log_id = Column(
        Integer(),
        ForeignKey(
            'call_logd_call_log.id',
            name='call_logd_recording_call_log_id_fkey',
            ondelete='CASCADE',
        ),
        nullable=False,
    )
    conversation_id = association_proxy('call_log', 'conversation_id')

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

    call_log = relationship(CallLog, uselist=False, viewonly=True)


@generic_repr
class Retention(Base):
    __tablename__ = 'call_logd_retention'

    tenant_uuid = Column(
        UUIDType,
        ForeignKey(
            'call_logd_tenant.uuid',
            name='call_logd_call_log_tenant_uuid_fkey',
            ondelete='CASCADE',
        ),
        primary_key=True,
    )
    cdr_days = Column(Integer)
    export_days = Column(Integer)
    recording_days = Column(Integer)

    def __init__(self, *args, **kwargs):
        # NOTE(fblackburn): Declare used properties
        self.default_cdr_days = None
        self.default_recording_days = None
        super().__init__(*args, **kwargs)


@generic_repr
class Config(Base):
    __tablename__ = 'call_logd_config'

    id = Column(Integer, primary_key=True)
    retention_cdr_days = Column(Integer)
    retention_cdr_days_from_file = Column(Boolean)
    retention_export_days = Column(Integer)
    retention_export_days_from_file = Column(Boolean)
    retention_recording_days = Column(Integer)
    retention_recording_days_from_file = Column(Boolean)


@generic_repr
class Export(Base):
    __tablename__ = 'call_logd_export'

    uuid = Column(
        UUIDType,
        server_default=text('uuid_generate_v4()'),
        primary_key=True,
    )
    tenant_uuid = Column(
        UUIDType,
        ForeignKey(
            'call_logd_tenant.uuid',
            name='call_logd_call_log_tenant_uuid_fkey',
            ondelete='CASCADE',
        ),
        nullable=False,
    )
    user_uuid = Column(UUIDType, nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False)
    path = Column(Text)

    @property
    def filename(self):
        offset = self.requested_at.utcoffset() or td(seconds=0)
        date_utc = (self.requested_at - offset).replace(tzinfo=tz.utc)
        formatted_date_utc = date_utc.strftime('%Y-%m-%dT%H_%M_%SUTC')
        return '{formatted_date_utc}-{uuid}.zip'.format(
            formatted_date_utc=formatted_date_utc,
            uuid=self.uuid,
        )

    __table_args__ = (
        Index('call_logd_export__idx__user_uuid', 'user_uuid'),
        CheckConstraint(
            status.in_(['pending', 'processing', 'finished', 'deleted', 'error']),
            name='call_logd_export_status_check',
        ),
    )

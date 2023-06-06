# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import threading
from functools import partial

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo import plugin_helpers
from xivo.status import StatusAggregator, TokenStatus
from xivo.token_renewer import TokenRenewer

from wazo_call_logd import celery
from wazo_call_logd.cel_interpretor import (
    CalleeCELInterpretor,
    CallerCELInterpretor,
    DispatchCELInterpretor,
    LocalOriginateCELInterpretor,
)
from wazo_call_logd.generator import CallLogsGenerator
from wazo_call_logd.manager import CallLogsManager
from wazo_call_logd.writer import CallLogsWriter

from .auth import init_master_tenant
from .bus import BusConsumer, BusPublisher
from .database.helpers import new_db_session
from .database.queries import DAO
from .http_server import HTTPServer, api, app

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, config):
        self.config = config
        self._stopping_thread = None
        DBSession = new_db_session(config['db_uri'])
        CELDBSession = new_db_session(config['cel_db_uri'])
        self.dao = DAO(DBSession, CELDBSession)
        writer = CallLogsWriter(self.dao)

        # NOTE(afournier): it is important to load the tasks before configuring the Celery app
        self.celery_task_manager = plugin_helpers.load(
            namespace='wazo_call_logd.celery_tasks',
            names=config['enabled_celery_tasks'],
            dependencies={
                'config': self.config,
                'dao': self.dao,
                'app': celery.app,
            },
        )
        celery.configure(config)
        self._celery_process = celery.spawn_workers(config)

        auth_client = AuthClient(**config['auth'])
        confd_client = ConfdClient(**config['confd'])
        generator = CallLogsGenerator(
            confd_client,
            [
                LocalOriginateCELInterpretor(),
                DispatchCELInterpretor(
                    CallerCELInterpretor(),
                    CalleeCELInterpretor(),
                ),
            ],
        )
        self.token_renewer = TokenRenewer(auth_client)
        self.token_renewer.subscribe_to_token_change(confd_client.set_token)
        self.token_renewer.subscribe_to_next_token_details_change(
            generator.set_default_tenant_uuid
        )

        self.bus_publisher = BusPublisher.from_config(config['uuid'], config['bus'])
        self.bus_consumer = BusConsumer.from_config(config['bus'])
        self.manager = CallLogsManager(self.dao, generator, writer, self.bus_publisher)

        self._bus_subscribe()

        self.http_server = HTTPServer(config)
        if not app.config['auth'].get('master_tenant_uuid'):
            self.token_renewer.subscribe_to_next_token_details_change(
                init_master_tenant
            )

        self.status_aggregator = StatusAggregator()
        self.token_status = TokenStatus()
        plugin_helpers.load(
            namespace='wazo_call_logd.plugins',
            names=config['enabled_plugins'],
            dependencies={
                'api': api,
                'config': config,
                'dao': self.dao,
                'token_renewer': self.token_renewer,
                'status_aggregator': self.status_aggregator,
                'bus_publisher': self.bus_publisher,
                'bus_consumer': self.bus_consumer,
            },
        )

    def run(self):
        logger.info('Starting wazo-call-logd')
        signal.signal(signal.SIGTERM, partial(_signal_handler, self))
        signal.signal(signal.SIGINT, partial(_signal_handler, self))
        self.token_renewer.subscribe_to_token_change(
            self.token_status.token_change_callback
        )
        self.status_aggregator.add_provider(self.bus_consumer.provide_status)
        self.status_aggregator.add_provider(self.token_status.provide_status)
        self.status_aggregator.add_provider(celery.provide_status)
        self._update_db_from_config_file()

        try:
            with self.bus_consumer:
                with self.token_renewer:
                    self.http_server.run()
        finally:
            logger.info('Stopping wazo-call-logd...')
            self._celery_process.terminate()
            self._celery_process.join()
            if self._stopping_thread:
                self._stopping_thread.join()

    def stop(self, reason):
        logger.warning('Stopping wazo-call-logd: %s', reason)
        self._stopping_thread = threading.Thread(
            target=self.http_server.stop, name=reason
        )
        self._stopping_thread.start()

    def _update_db_from_config_file(self):
        with self.dao.helper.db_ready():
            config = self.dao.config.find_or_create()
            cdr_days = self.config['retention']['cdr_days']
            if cdr_days is not None:
                config.retention_cdr_days = cdr_days
                config.retention_cdr_days_from_file = True
            else:
                config.retention_cdr_days_from_file = False
            export_days = self.config['retention']['export_days']
            if export_days is not None:
                config.retention_export_days = export_days
                config.retention_export_days_from_file = True
            else:
                config.retention_export_days_from_file = False
            recording_days = self.config['retention']['recording_days']
            if recording_days is not None:
                config.retention_recording_days = recording_days
                config.retention_recording_days_from_file = True
            else:
                config.retention_recording_days_from_file = False
            self.dao.config.update(config)

    def _bus_subscribe(self):
        self.bus_consumer.subscribe('CEL', self._handle_linked_id_end)

    def _handle_linked_id_end(self, payload):
        if payload['EventName'] != 'LINKEDID_END':
            return

        linked_id = payload['LinkedID']
        try:
            self.manager.generate_from_linked_id(linked_id)
        except Exception:
            logger.exception(
                'Failed to genereate call log for linked id=\"%s\"', linked_id
            )


def _signal_handler(controller, signum, frame):
    controller.stop(reason=signal.Signals(signum).name)

# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import smtplib

from celery import Task
from collections import namedtuple
from email import utils as email_utils
from email.message import EmailMessage
from wazo_auth_client import Client as AuthClient
from zipfile import ZipFile, ZIP_DEFLATED

from wazo_call_logd.email import TemplateFormatter

from .exceptions import (
    RecordingMediaFSPermissionException,
    RecordingMediaFSNotFoundException,
)

logger = logging.getLogger(__name__)

export_recording_task = None

EmailDestination = namedtuple('EmailDestination', ['name', 'address'])


class Plugin:
    def load(self, dependencies):
        global export_recording_task
        app = dependencies['app']
        config = dependencies['config']
        dao = dependencies['dao']

        @app.task(base=RecordingExportTask, bind=True)
        def _export_recording_task(
            task,
            task_uuid,
            recordings,
            output_dir,
            tenant_uuid,
            email,
            connection_info,
        ):
            task._run(
                config,
                dao,
                task_uuid,
                recordings,
                output_dir,
                tenant_uuid,
                email,
                connection_info,
            )

        export_recording_task = _export_recording_task


class RecordingExportTask(Task):
    def _run(
        self,
        config,
        dao,
        task_uuid,
        recordings,
        output_dir,
        tenant_uuid,
        email,
        connection_info,
    ):
        export = dao.export.get(task_uuid, [tenant_uuid])
        export.status = 'processing'
        dao.export.update(export)
        filename = f'{task_uuid}.zip'
        fullpath = os.path.join(output_dir, filename)
        with ZipFile(fullpath, mode='w', compression=ZIP_DEFLATED) as zip_file:
            for recording in recordings:
                try:
                    archive_name = os.path.join(
                        str(recording['call_log_id']), recording['filename']
                    )
                    zip_file.write(recording['path'], arcname=archive_name)
                except PermissionError:
                    logger.error('Permission denied: "%s"', recording['path'])
                    export.status = 'error'
                    dao.export.update(export)
                    raise RecordingMediaFSPermissionException(
                        recording['uuid'],
                        recording['path'],
                    )
                except FileNotFoundError:
                    logger.error('Recording file not found: "%s"', recording['path'])
                    export.status = 'error'
                    dao.export.update(export)
                    raise RecordingMediaFSNotFoundException(
                        recording['uuid'],
                        recording['path'],
                    )

        export.path = fullpath
        export.status = 'finished'
        dao.export.update(export)
        if email:
            self._send_email(
                task_uuid, 'Wazo user', email, config, connection_info
            )

    def _send_email(
        self,
        task_uuid,
        destination_name,
        destination_address,
        config,
        connection_info,
    ):
        smtp_config = config['smtp']
        export_config = config['exports']
        host = smtp_config.get('host')
        port = smtp_config.get('port')
        timeout = smtp_config.get('timeout')
        email_from_name = export_config.get('from_name')
        email_from_address = export_config.get('from_address')
        email_from = EmailDestination(email_from_name, email_from_address)
        email_destination = EmailDestination(destination_name, destination_address)
        smtp_username = smtp_config.get('username')
        smtp_password = smtp_config.get('password')
        smtp_starttls = smtp_config.get('starttls')

        subject = export_config.get('subject')

        message = EmailMessage()
        message['From'] = email_utils.formataddr(email_from)
        message['Subject'] = subject
        message['To'] = email_utils.formataddr(email_destination)

        auth_config = dict(config['auth'])
        auth_config.update(
            {
                'username': export_config['service_id'],
                'password': export_config['service_key'],
            }
        )
        auth_client = AuthClient(**auth_config)
        token_uuid = auth_client.token.new(expiration=config['email_token_expiration'])['token']

        template_formatter = TemplateFormatter(config)
        context = {
            'export_uuid': task_uuid,
            'token': token_uuid,
            **connection_info,
        }
        message.set_content(template_formatter.format_export_email(context))

        with smtplib.SMTP(host, port=port, timeout=timeout) as smtp_server:
            if smtp_starttls:
                smtp_server.starttls()
            smtp_server.login(smtp_username, smtp_password)
            smtp_server.send_message(message)

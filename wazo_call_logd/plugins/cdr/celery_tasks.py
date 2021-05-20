# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import smtplib

from collections import namedtuple
from email import utils as email_utils
from email.message import EmailMessage
from zipfile import ZipFile, ZIP_BZIP2

from wazo_call_logd.celery import LoadableTask
from .exceptions import RecordingMediaFSPermissionException, RecordingMediaFSNotFoundException

logger = logging.getLogger(__name__)

export_recording_task = None

EmailDestination = namedtuple('EmailDestination', ['name', 'address'])


class RecordingExportTask(LoadableTask):
    def load(self, dependencies):
        super().load(dependencies)
        global export_recording_task
        self._app = dependencies['app']
        self._config = dependencies['config']
        export_recording_task = self._app.register_task(self)
        logger.debug('registered instance: %s', self)

    def run(self, task_uuid, recordings, output_dir, tenant_uuid, destination_email):
        export = self._dao.export.get_by_uuid(task_uuid, [tenant_uuid])
        filename = f'{task_uuid}.zip'
        fullpath = os.path.join(output_dir, filename)
        with ZipFile(fullpath, mode='w', compression=ZIP_BZIP2) as zip_file:
            for recording in recordings:
                try:
                    zip_file.write(recording['path'], arcname=recording['filename'])
                except PermissionError:
                    logger.error('Permission denied: "%s"', recording['path'])
                    raise RecordingMediaFSPermissionException(recording['uuid'], recording['path'])
                except FileNotFoundError:
                    logger.error('Recording file not found: "%s"', recording['path'])
                    raise RecordingMediaFSNotFoundException(recording['uuid'], recording['path'])
        export.path = fullpath
        export.done = True
        self._dao.export.update(export)
        self.send_email(task_uuid, 'Wazo user', destination_email)

    def send_email(self, task_uuid, destination_name, destination_address):
        email_config = self._config['email']
        host = email_config.get('host')
        port = email_config.get('port')
        timeout = email_config.get('timeout')
        email_from_name = email_config.get('from_name')
        email_from_address = email_config.get('from_address')
        email_from = EmailDestination(email_from_name, email_from_address)
        email_destination = EmailDestination(destination_name, destination_address)
        smtp_username = email_config.get('username')
        smtp_password = email_config.get('password')

        subject = email_config.get('subject')

        message = EmailMessage()
        message['From'] = email_utils.formataddr(email_from)
        message['Subject'] = subject
        message['To'] = email_utils.formataddr(email_destination)

        # Get auth token for user
        message.set_content('test')

        with smtplib.SMTP(host, port=port, timeout=timeout) as smtp_server:
            smtp_server.starttls()
            smtp_server.login(smtp_username, smtp_password)
            smtp_server.send_message(message)

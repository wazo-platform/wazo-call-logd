import logging
import os

from zipfile import ZipFile, ZIP_BZIP2

from wazo_call_logd.celery import LoadableTask
from .exceptions import RecordingMediaFSPermissionException, RecordingMediaFSNotFoundException

logger = logging.getLogger(__name__)

export_recording_task = None


class RecordingExportTask(LoadableTask):
    def load(self, dependencies):
        super().load(dependencies)
        global export_recording_task
        app = dependencies['app']
        export_recording_task = app.register_task(self)
        logger.debug('registered instance: %s', self)

    def run(self, task_uuid, recordings, output_dir, tenant_uuid):
        export = self._dao.export.get_by_uuid(task_uuid, [tenant_uuid])
        filename = f'{task_uuid}.zip'
        fullpath = os.path.join(output_dir, filename)
        zip_file = ZipFile(fullpath, mode='w', compression=ZIP_BZIP2)
        for recording in recordings:
            try:
                zip_file.write(recording['path'], arcname=recording['filename'])
            except PermissionError:
                logger.error('Permission denied: "%s"', recording['path'])
                raise RecordingMediaFSPermissionException(recording['uuid'], recording['path'])
            except FileNotFoundError:
                logger.error('Recording file not found: "%s"', recording['path'])
                raise RecordingMediaFSNotFoundException(recording['uuid'], recording['path'])
        zip_file.close()
        export.path = fullpath
        export.done = True
        self._dao.export.update(export)

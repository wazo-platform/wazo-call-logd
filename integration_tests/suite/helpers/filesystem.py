# Copyright 2021-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
from functools import wraps

FILE_USER = 'wazo-call-logd'
FILE_GROUP = 'wazo-call-logd'


class FileSystemClient:
    def __init__(self, execute, service_name=None, root=False):
        self.execute = execute
        self.service_name = service_name
        self.root = root

    def create_file(self, path, content='content', mode='666', root=False):
        # FIXME: use Filesystem from wazo-test-helpers
        command = ['sh', '-c', f'head -c -1 <<EOF > {path}\n{content}\nEOF']
        self.execute(command, service_name=self.service_name)
        command = ['chmod', mode, path]
        self.execute(command, service_name=self.service_name)
        if not root and not self.root:
            command = ['chown', f'{FILE_USER}:{FILE_GROUP}', path]
            self.execute(command, service_name=self.service_name)

    def remove_file(self, path):
        command = ['rm', '-f', f'{path}']
        self.execute(command, service_name=self.service_name)

    def path_exists(self, path):
        command = ['ls', path]
        result = self.execute(
            command,
            service_name=self.service_name,
            return_attr='returncode',
        )
        return result == 0


@contextmanager
def file_fixture(filesystem: FileSystemClient, path, **file_kwargs):
    filesystem.create_file(path, **file_kwargs)
    try:
        yield
    finally:
        filesystem.remove_file(path)


def file_(path, service_name=None, **file_kwargs):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            filesystem = FileSystemClient(self.docker_exec, service_name=service_name)
            with file_fixture(filesystem, path, **file_kwargs):
                return func(self, *args, **kwargs)

        return wrapped_function

    return _decorate

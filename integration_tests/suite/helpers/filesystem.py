# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

FILE_USER = 'wazo-call-logd'
FILE_GROUP = 'wazo-call-logd'


class FileSystemClient:
    def __init__(self, execute):
        self.execute = execute

    def create_file(self, path, content='content', mode='666', root=False):
        command = ['sh', '-c', f'echo -n {content} > {path}']
        self.execute(command)
        command = ['chmod', mode, path]
        self.execute(command)
        if not root:
            command = ['chown', f'{FILE_USER}:{FILE_GROUP}', path]
        self.execute(command)

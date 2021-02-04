# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class FileSystemClient:
    def __init__(self, execute):
        self.execute = execute

    def create_file(self, path, content='content', mode='666'):
        command = ['sh', '-c', f'echo -n {content} > {path}']
        self.execute(command)
        command = ['chmod', mode, path]
        self.execute(command)

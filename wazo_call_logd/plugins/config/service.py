# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class ConfigService:
    def __init__(self, config):
        self._config = dict(config)

    def get(self):
        return self._config

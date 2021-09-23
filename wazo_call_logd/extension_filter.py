# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

logger = logging.getLogger(__name__)

DEFAULT_HIDDEN_EXTENSIONS = ('s',)


class ExtensionFilter:
    def __init__(self, default_extensions=DEFAULT_HIDDEN_EXTENSIONS):
        self._extensions = set(default_extensions)

    def add_exten(self, exten):
        logger.debug('New filtered extension: "%s"', exten)
        self._extensions.add(exten)

    def filter(self, exten):
        return '' if exten in self._extensions else exten

    def filter_call(self, call):
        call.source_exten = self.filter(call.source_exten)
        call.source_internal_exten = self.filter(call.source_internal_exten)
        call.requested_exten = self.filter(call.requested_exten)
        call.requested_internal_exten = self.filter(call.requested_internal_exten)
        call.destination_exten = self.filter(call.destination_exten)
        call.destination_internal_exten = self.filter(call.destination_internal_exten)
        return call

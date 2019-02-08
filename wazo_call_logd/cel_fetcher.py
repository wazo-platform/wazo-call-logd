# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_dao.resources.cel import dao as cel_dao


class CELFetcher(object):

    def fetch_last_unprocessed(self, cel_count=None, older=None):
        return cel_dao.find_last_unprocessed(cel_count, older)

    def fetch_from_linked_id(self, linked_id):
        return cel_dao.find_from_linked_id(linked_id)

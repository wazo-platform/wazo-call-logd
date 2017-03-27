# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests


class CallLogdClient(object):

    def __init__(self, host, port):
        self._host = host
        self._port = port

    def url(self, *parts):
        return 'https://{host}:{port}/1.0/{path}'.format(host=self._host,
                                                         port=self._port,
                                                         path='/'.join(unicode(part) for part in parts))

    def is_up(self):
        url = self.url()
        try:
            response = requests.get(url, verify=False)
            return response.status_code == 404
        except requests.RequestException:
            return False

    def get_cdr_result(self, token=None):
        result = requests.get(self.url('cdr'), headers={'X-Auth-Token': token}, verify=False)
        return result

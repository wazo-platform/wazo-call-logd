# Copyright 2012-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import sys
from functools import partial

import xivo_dao
from xivo.config_helper import set_xivo_uuid
from xivo.daemonize import pidfile_context
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging
from wazo_call_logd.config import load as load_config
from wazo_call_logd.controller import Controller

logger = logging.getLogger(__name__)
FOREGROUND = True  # Always in foreground systemd takes care of daemonizing


def main(argv):
    config = load_config(argv)

    user = config.get('user')
    if user:
        change_user(user)

    setup_logging(config['logfile'], FOREGROUND, config['debug'], config['log_level'])
    xivo_dao.init_db_from_config(config)

    set_xivo_uuid(config, logger)

    controller = Controller(config)
    signal.signal(signal.SIGTERM, partial(sigterm, controller))

    with pidfile_context(config['pidfile'], FOREGROUND):
        controller.run()


def sigterm(controller, signum, frame):
    del signum
    del frame

    controller.stop(reason='SIGTERM')


if __name__ == '__main__':
    main(sys.argv[1:])

# Copyright 2012-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import sys
from functools import partial

import xivo_dao
from xivo.config_helper import set_xivo_uuid
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging, silence_loggers
from wazo_call_logd.config import load as load_config
from wazo_call_logd.controller import Controller

logger = logging.getLogger(__name__)


def main():
    argv = sys.argv[1:]
    config = load_config(argv)

    user = config.get('user')
    if user:
        change_user(user)

    setup_logging(
        config['logfile'], debug=config['debug'], log_level=config['log_level']
    )
    silence_loggers(['amqp'], level=logging.WARNING)
    xivo_dao.init_db_from_config(config)

    set_xivo_uuid(config, logger)

    controller = Controller(config)
    signal.signal(signal.SIGTERM, partial(sigterm, controller))

    controller.run()


def sigterm(controller, signum, frame):
    del signum
    del frame

    controller.stop(reason='SIGTERM')


if __name__ == '__main__':
    main()

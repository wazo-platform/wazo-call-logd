# -*- coding: utf-8 -*-

# Copyright (C) 2012-2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import argparse
import logging
import signal

from xivo_bus.ctl.consumer import BusConsumer
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_dispatcher import CELDispatcher
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.orchestrator import CallLogsOrchestrator
from xivo_call_logs.writer import CallLogsWriter
from xivo import daemonize

_LOG_FILENAME = '/var/log/xivo-call-logd.log'
_PID_FILENAME = '/var/run/xivo-call-logd.pid'

logger = logging.getLogger(__name__)


def main():
    parsed_args = _parse_args()

    _init_logging(parsed_args)

    if not parsed_args.foreground:
        daemonize.daemonize()

    logger.info('Starting xivo-call-logd')
    daemonize.lock_pidfile_or_die(_PID_FILENAME)
    try:
        _run()
    except Exception:
        logger.exception('Unexpected error:')
    finally:
        logger.info('Stopping xivo-call-logd')
        daemonize.unlock_pidfile(_PID_FILENAME)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--foreground', action='store_true',
                        help='run in foreground')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase verbosity')
    return parser.parse_args()


def _init_logging(parsed_args):
    level = logging.DEBUG if parsed_args.verbose else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if parsed_args.foreground:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s (%(levelname)s): %(message)s'))
    else:
        handler = logging.FileHandler(_LOG_FILENAME)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(process)d] (%(levelname)s): %(message)s'))
    root_logger.addHandler(handler)


def _run():
    _init_signal()
    orchestrator = _init_orchestrator()
    orchestrator.run()


def _init_signal():
    signal.signal(signal.SIGTERM, _handle_sigterm)


def _handle_sigterm(signum, frame):
    raise SystemExit()


def _init_orchestrator():
    bus_consumer = BusConsumer()
    cel_fetcher = CELFetcher()
    caller_cel_interpretor = CallerCELInterpretor()
    callee_cel_interpretor = CalleeCELInterpretor()
    cel_dispatcher = CELDispatcher(caller_cel_interpretor,
                                   callee_cel_interpretor)
    generator = CallLogsGenerator(cel_dispatcher)
    writer = CallLogsWriter()
    manager = CallLogsManager(cel_fetcher, generator, writer)
    return CallLogsOrchestrator(bus_consumer, manager)


if __name__ == '__main__':
    main()

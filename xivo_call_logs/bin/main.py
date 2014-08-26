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

from xivo.daemonize import pidfile_context
from xivo.xivo_logging import setup_logging
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_dispatcher import CELDispatcher
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.writer import CallLogsWriter

DEFAULT_CEL_COUNT = 20000
PIDFILENAME = '/var/run/xivo-call-logs.pid'


def main():
    setup_logging('/dev/null', foreground=True, debug=False)
    with pidfile_context(PIDFILENAME, foreground=True):
        _generate_call_logs()


def _generate_call_logs():
    parser = argparse.ArgumentParser(description='Call logs generator')
    options = parse_args(parser)
    cel_fetcher = CELFetcher()
    caller_cel_interpretor = CallerCELInterpretor()
    callee_cel_interpretor = CalleeCELInterpretor()
    cel_dispatcher = CELDispatcher(caller_cel_interpretor,
                                   callee_cel_interpretor)
    generator = CallLogsGenerator(cel_dispatcher)
    writer = CallLogsWriter()
    manager = CallLogsManager(cel_fetcher, generator, writer)

    manager.generate_from_count(cel_count=options.cel_count)


def parse_args(parser):
    parser.add_argument('-c', '--cel-count',
                        default=DEFAULT_CEL_COUNT,
                        type=int,
                        help='Minimum number of CEL entries to process')
    return parser.parse_args()

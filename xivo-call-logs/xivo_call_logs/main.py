# -*- coding: utf-8 -*-

# Copyright (C) 2012-2013  Avencall
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

from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_interpretor import CELInterpretor
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.writer import CallLogsWriter


def main():
    cel_fetcher = CELFetcher()
    cel_interpretor = CELInterpretor()
    generator = CallLogsGenerator(cel_interpretor)
    writer = CallLogsWriter()
    manager = CallLogsManager(cel_fetcher, generator, writer)

    manager.generate()

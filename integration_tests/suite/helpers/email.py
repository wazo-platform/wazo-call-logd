# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations


class EmailClient:
    email_dir = '/var/mail'

    def __init__(self, host: str, execute):
        self.host = host
        self.execute = execute

    def get_last_email_url(self) -> str | None:
        emails = self._get_emails()
        if not emails:
            return None
        email_body = emails[-1]
        urls = [line for line in email_body.split('\n') if line.startswith('https://')]
        return urls[-1] if urls else None

    def _get_emails(self) -> list[str]:
        return [self._email_body(f) for f in self._get_email_filenames()]

    def _email_body(self, filename: str) -> str:
        command = ['cat', f'{self.email_dir}/{filename}']
        result = self.execute(command, self.host)
        return result.decode('utf-8')

    def _get_email_filenames(self) -> list[str]:
        command = ['ls', self.email_dir]
        result = self.execute(command, self.host)
        output_str = result.decode('utf-8').strip()
        output_list = output_str.split('\n') if output_str else []
        return output_list

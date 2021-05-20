# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from jinja2 import BaseLoader, Environment, TemplateNotFound


class TemplateLoader(BaseLoader):

    _templates = {
        'email_export': 'email_export_template',
        'email_export_get_body': 'email_export_get_response_body_template',
        'email_export_subject': 'email_export_subject_template',
    }

    def __init__(self, config):
        self._config = config

    def get_source(self, environment, template):
        config_key = self._templates.get(template)
        if not config_key:
            raise TemplateNotFound(template)

        template_path = self._config[config_key]
        if not os.path.exists(template_path):
            raise TemplateNotFound(template)

        mtime = os.path.getmtime(template_path)
        with open(template_path) as f:
            source = f.read()

        return source, template_path, lambda: mtime == os.path.getmtime(template_path)


class TemplateFormatter:
    def __init__(self, config):
        self.environment = Environment(loader=TemplateLoader(config))

    def format_export_email(self, context):
        template = self.environment.get_template('email_export')
        return template.render(**context)

    def get_export_email_get_body(self, context=None):
        context = context or {}
        template = self.environment.get_template('email_export_get_body')
        return template.render(**context)

    def format_export_subject(self, context):
        template = self.environment.get_template('email_export_subject')
        return template.render(**context)

# coding: utf-8
from __future__ import absolute_import, unicode_literals

import requests
import anyjson

from thebot import Plugin, on_command


class Plugin(Plugin):
    @on_command('(calc|calculate|convert|math)( me)? (?P<expression>.+)')
    def math(self, request, expression):
        """Use Google's calculator to do some math."""
        response = requests.get(
            'http://www.google.com/ig/calculator',
            params=dict(
                q=expression,
            ),
        )
        if response.status_code == 200:
            content = response.content.decode(response.encoding)
            content = content.replace('{', '{"').replace(':', '":').replace(',', ',"')

            try:
                data = anyjson.deserialize(content)
            except Exception:
                request.respond('Can\'t parse: {}'.format(content))
            else:
                if data['rhs']:
                    request.respond(data['rhs'])
                else:
                    request.respond('Could not compute.')


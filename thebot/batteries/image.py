# coding: utf-8
from __future__ import absolute_import, unicode_literals

import requests
import anyjson
import random

from thebot import Plugin, on_command


class Plugin(Plugin):
    @on_command('(image|img)( me)? (?P<query>.+)')
    def image(self, request, query):
        """Google random image on given topic."""
        url = self._find_image(query)
        if url is None:
            request.respond('No image was found for query "{0}"'.format(query))
        else:
            request.respond(url)

    @on_command('moustache( for)? (?P<query>.+)')
    @on_command('усы( для)? (?P<query>.+)')
    def mustache(self, request, query):
        """Apply moustache on image URL or random image on given topic."""
        type = int(random.randint(0, 2))

        if query.startswith('http'):
            url = query
        else:
            url = self._find_image(query)
            if url is None:
                request.respond('No image was found for query "{0}"'.format(query))
                return

        request.respond(
            'http://mustachify.me/{type}?src={url}'.format(
                type=type,
                url=url,
            )
        )

    def _find_image(self, query):
        response = requests.get(
            'http://ajax.googleapis.com/ajax/services/search/images',
            params=dict(
                v="1.0",
                rsz='8',
                q=query,
                safe='active',
            )
        )
        if response.status_code == 200:
            content = response.content
            data = anyjson.deserialize(content)
            images = data['responseData']['results']

            if len(images) > 0:
                image = random.choice(images[:5])
                return image['unescapedUrl']


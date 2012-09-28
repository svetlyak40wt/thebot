# coding: utf-8

import requests
import anyjson
import random
import thebot


class Plugin(thebot.Plugin):
    def get_callbacks(self):
        return [
            ('(image|img)( me)? (?P<query>.+)', self.image),
            ('(?:mo?u)?sta(?:s|c)he?(?: me)? (?P<query>.+)', self.mustache),
            ('нарисуй усы для (?P<query>.+)', self.mustache),
        ]

    def image(self, request, match):
        query = match.group('query')
        url = self.find_image(query)
        if url is None:
            request.respond('No image was found for query "{0}"'.format(query))
        else:
            request.respond(url)

    def find_image(self, query):
        response = requests.get(
            'http://ajax.googleapis.com/ajax/services/search/images',
            params=dict(
                v="1.0",
                rsz='8',
                q=query,
                safe='active',
            )
        )
        content = response.content
        data = anyjson.deserialize(content)
        images = data['responseData']['results']

        if len(images) > 0:
            image = random.choice(images)
            return image['unescapedUrl']


    def mustache(self, request, match):
        type = int(random.randint(0, 2))
        query = match.group('query')

        if query.startswith('http'):
            url = query
        else:
            url = self.find_image(query)
            if url is None:
                request.respond('No image was found for query "{0}"'.format(query))
                return

        request.respond(
            'http://mustachify.me/{type}?src={url}'.format(
                type=type,
                url=url,
            )
        )




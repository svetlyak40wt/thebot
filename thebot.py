#!/usr/bin/env python
# coding: utf-8

import requests
import re
import sys
import irc
import threading
import anyjson
import random

from time import sleep


class Request(object):
    def __init__(self, message):
        self.message = message

    def respond(self, message):
        raise NotImplementedError('You have to implement \'respond\' method in you Request class.')


class Adapter(object):
    def __init__(self, callback):
        self.callback = callback

# pass this object to callback, to terminate the bot
EXIT = object()


class IRCRequest(Request):
    def __init__(self, message, bot, nick, channel):
        super(IRCRequest, self).__init__(message)
        self.bot = bot
        self.nick = nick
        self.channel = channel

    def respond(self, message):
        self.bot.respond(message, channel=self.channel, nick=self.nick)


class IRCAdapter(Adapter):
    def on_line(self, nick, message, channel):
        request = IRCRequest(message, self.bot, nick, channel)
        return self.callback(request)

    def start(self):
        thread = threading.Thread(target=self.run_bot)
        thread.daemon = True
        thread.start()

    def run_bot(self):
        """
        Convenience function to start a bot on the given network, optionally joining
        some channels
        """
        host = 'irc.freenode.net'
        port = 6667
        nick = 'thebot'
        channels = ['svetlyak']
        conn = irc.IRCConnection(host, port, nick)

        on_line = self.on_line
        class IRCBot(irc.IRCBot):
            def command_patterns(self):
                return (
                    self.ping('^.*', on_line),
                )

        self.bot = IRCBot(conn)
        #TODO refactor
        self.bot.on_line = self.on_line

        while 1:
            conn.connect()
            channels = channels or []
            for channel in channels:
                conn.join(channel)
            conn.enter_event_loop()

class ConsoleRequest(Request):
    def respond(self, message):
        sys.stdout.write('{0}\n'.format(message))
        sys.stdout.flush()


class ConsoleAdapter(Adapter):
    def start(self):
        def loop():
            while True:
                sys.stdout.write('> ')
                sys.stdout.flush()
                line = sys.stdin.readline()
                if len(line) == 0:
                    # seems, Ctrl-D was pressed
                    self.callback(EXIT)
                    return

                line = line.strip()

                self.callback(ConsoleRequest(line))

        thread = threading.Thread(target=loop)
        thread.daemon = True
        thread.start()


class ImagePlugin(object):
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


class Bot(object):
    def __init__(self, adapters, plugins):
        self.adapters = []
        self.plugins = []
        self.patterns = []
        self.exiting = False

        for adapter in adapters:
            a = adapter(callback=self.on_request)
            a.start()
            self.adapters.append(a)

        for plugin in plugins:
            p = plugin()
            self.plugins.append(p)
            self.patterns.extend(p.get_callbacks())


    def on_request(self, request):
        if request is EXIT:
            self.exiting = True
        else:
            for pattern, callback in self.patterns:
                match = re.match(pattern, request.message)
                if match is not None:
                    result = callback(request, match)
                    if result is not None:
                        raise RuntimeError('Plugin {0} should not return response directly. Use request.respond(some message).')
                    break
            else:
                request.respond('I don\'t know command "{0}".'.format(request.message))

    def close(self):
        """Will close all connections here.
        """
        pass


def main():
    #bot = Bot([IRCAdapter], [ImagePlugin])
    bot = Bot([ConsoleAdapter], [ImagePlugin])
    try:
        while not bot.exiting:
            sleep(1)
    except KeyboardInterrupt:
        pass
    bot.close()


if __name__ == '__main__':
    main()


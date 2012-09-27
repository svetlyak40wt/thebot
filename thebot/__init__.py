# coding: utf-8

import importlib
import re

# pass this object to callback, to terminate the bot
EXIT = object()


class Request(object):
    def __init__(self, message):
        self.message = message

    def respond(self, message):
        raise NotImplementedError('You have to implement \'respond\' method in you Request class.')


class Adapter(object):
    def __init__(self, callback):
        self.callback = callback


class Bot(object):
    def __init__(self, adapters, plugins):
        self.adapters = []
        self.plugins = []
        self.patterns = []
        self.exiting = False

        def load(value, cls='Adapter'):
            """Returns class by it's name.

            Given a 'irc' string it will try to load the following:

            1) from thebot_irc import Adapter
            2) from thebot.batteries.irc import Adapter

            If all of them fail, it will raise ImportError
            """
            if isinstance(value, basestring):
                try:
                    module = importlib.import_module('thebot_' + value)
                except ImportError:
                    module = importlib.import_module('thebot.batteries.' + value)

                return getattr(module, cls)
            return value

        for adapter in map(lambda a: load(a, 'Adapter'), adapters):
            a = adapter(callback=self.on_request)
            a.start()
            self.adapters.append(a)

        for plugin in map(lambda a: load(a, 'Plugin'), plugins):
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


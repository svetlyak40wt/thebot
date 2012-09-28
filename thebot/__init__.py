# coding: utf-8

import importlib
import re
import argparse

# pass this object to callback, to terminate the bot
EXIT = object()


class Request(object):
    def __init__(self, message):
        self.message = message

    def respond(self, message):
        raise NotImplementedError('You have to implement \'respond\' method in you Request class.')


class Adapter(object):
    def __init__(self, args, callback):
        self.args = args
        self.callback = callback


class Plugin(object):
    def __init__(self, args):
        self.args = args


class Bot(object):
    def __init__(self, command_line_args):
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

        parser = Bot.get_general_options()
        args, unknown = parser.parse_known_args(filter(lambda x: x not in ('--help', '-h'), command_line_args))

        adapter_classes = map(lambda a: load(a, 'Adapter'), args.adapters.split(','))
        plugin_classes = map(lambda a: load(a, 'Plugin'), args.plugins.split(','))

        for cls in adapter_classes + plugin_classes:
            if hasattr(cls, 'get_options'):
                cls.get_options(parser)

        args = parser.parse_args(command_line_args)

        # adapters and plugins initialization

        for adapter in adapter_classes:
            a = adapter(args, callback=self.on_request)
            a.start()
            self.adapters.append(a)

        for plugin in plugin_classes:
            p = plugin(args)
            self.plugins.append(p)
            self.patterns.extend(p.get_callbacks())

    @staticmethod
    def get_general_options():
        parser = argparse.ArgumentParser(
            description='The Bot — Hubot\'s killer.'
        )
        parser.add_argument(
            '--verbose', '-v', action='store_true', default=False,
            help='Show more output.'
        )

        group = parser.add_argument_group('General options')
        group.add_argument(
            '--adapters', '-a', default='console',
            help='Adapters to use. You can specify a comma-separated list to use more than one adapter. Default: console.',
        )
        group.add_argument(
            '--plugins', '-p', default='image',
            help='Plugins to use. You can specify a comma-separated list to use more than one plugin. Default: image.',
        )
        return parser

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


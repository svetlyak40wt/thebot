# coding: utf-8

import importlib
import re
import argparse
import logging
import shelve

# pass this object to callback, to terminate the bot
EXIT = object()


class Request(object):
    def __init__(self, message):
        self.message = message

    def respond(self, message):
        raise NotImplementedError('You have to implement \'respond\' method in you Request class.')


class Adapter(object):
    def __init__(self, bot, callback):
        self.bot = bot
        self.callback = callback

    def start(self):
        """You have to override this method, if you plugin requires some background activity.

        Here you can create a thread, but don't forget to make its `daemon` attrubute equal to True.
        """


class Plugin(object):
    def __init__(self, bot):
        self.bot = bot

    def get_callbacks(self):
        for name in dir(self):
            value = getattr(self, name)
            if callable(value):
                patterns = getattr(value, '_patterns', [])
                for pattern in patterns:
                    yield (pattern, value)


def route(pattern):
    """Decorator to assign routes to plugin's methods.
    """
    def deco(func):
        if getattr(func, '_patterns', None) is None:
            func._patterns = []
        func._patterns.append(pattern)
        return func
    return deco


class HelpPlugin(Plugin):
    @route('help')
    def help(self, request):
        """Shows a help."""
        lines = []
        for pattern, callback in self.bot.patterns:
            docstring = callback.__doc__
            if docstring:
                lines.append('  ' + pattern + ' — ' + docstring)
            else:
                lines.append('  ' + pattern)

        lines.sort()
        lines.insert(0, 'I support following commands:')

        request.respond('\n'.join(lines))



class Storage(object):
    def __init__(self, filename, prefix=''):
        if isinstance(filename, basestring):
            self._shelve = shelve.open(filename)
        else:
            self._shelve = filename

        self.prefix = prefix

    def __getitem__(self, name):
        return self._shelve.__getitem__(self.prefix + name)

    def __setitem__(self, name, value):
        return self._shelve.__setitem__(self.prefix + name, value)

    def keys(self):
        return filter(lambda x: x.startswith(self.prefix), self._shelve.keys())

    def clear(self):
        for key in self.keys():
            del self._shelve[key]

    def with_prefix(self, prefix):
        return Storage(self._shelve, prefix=prefix)


class Bot(object):
    def __init__(self, command_line_args=[], adapters=None, plugins=None):
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

        if adapters is None:
            adapter_classes = map(lambda a: load(a, 'Adapter'), args.adapters.split(','))
        else:
            # we've got adapters argument (it is used for testing purpose
            adapter_classes = adapters

        if plugins is None:
            plugin_classes = map(lambda a: load(a, 'Plugin'), args.plugins.split(','))
        else:
            # we've got adapters argument (it is used for testing purpose
            plugin_classes = plugins

        plugin_classes.append(HelpPlugin)

        for cls in adapter_classes + plugin_classes:
            if hasattr(cls, 'get_options'):
                cls.get_options(parser)

        self.config = parser.parse_args(command_line_args)

        logging.basicConfig(
            filename=self.config.log_filename,
            format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            level=logging.DEBUG if self.config.verbose else logging.WARNING,
        )

        # adapters and plugins initialization

        for adapter in adapter_classes:
            a = adapter(self, callback=self.on_request)
            a.start()
            self.adapters.append(a)

        for plugin_cls in plugin_classes:
            p = plugin_cls(self)
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
        parser.add_argument(
            '--log-filename', default='thebot.log',
            help='Log\'s filename. Default: thebot.log.'
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
                    result = callback(request, **match.groupdict())
                    if result is not None:
                        raise RuntimeError('Plugin {0} should not return response directly. Use request.respond(some message).')
                    break
            else:
                request.respond('I don\'t know command "{0}".'.format(request.message))

    def close(self):
        """Will close all connections here.
        """
        pass


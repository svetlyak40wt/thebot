# coding: utf-8
from __future__ import absolute_import

import argparse
import importlib
import logging
import os
import pickle
import pkg_resources
import re
import shelve
import six
import threading
import time
import yaml

from . import utils

__version__ = pkg_resources.get_distribution(__name__).version


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
        self.storage = self.bot.storage.with_prefix(self.__module__ + ':')

    def get_callbacks(self):
        for name in dir(self):
            value = getattr(self, name)
            if callable(value):
                patterns = getattr(value, '_patterns', [])
                for pattern in patterns:
                    yield (pattern, value)


class ThreadedPlugin(Plugin):
    """ThreadedPlugin allows you to do some processing in a background thread.

    This class will take care on proper thread execution and termination.

    * First, implement method `do_job`, which will be executed with given interval.
    * Then run method `self.start_worker(interval=60)` to run a thread.
      It will call your do_job callback each 60 seconds.
    * To stop job execution, call `self.stop_worker()`.

    See `thebot-instagram`, as an example.
    """
    def do_job(self):
        raise NotImplemented('Implement "do_job" method to get real work done.')

    def is_working(self):
        thread = getattr(self, '_thread', None)
        return thread is not None and thread.is_alive()

    def start_worker(self, interval=60):
        if self.is_working():
            return

        self._event = threading.Event()
        self._thread = threading.Thread(target=self._worker, kwargs=dict(interval=interval))
        self._thread.daemon = True
        self._thread.start()

    def stop_worker(self, wait=True):
        event = getattr(self, '_event', None)
        if event is not None:
            event.set()

        if wait:
            self._thread.join()

    def _worker(self, interval=60):
        countdown = 0
        logger = logging.getLogger('thebot.' + self.__class__.__name__)

        on_start = getattr(self, 'on_start', None)
        if on_start is not None:
            on_start()

        while not self._event.is_set():
            if countdown == 0:
                try:
                    self.do_job()
                except Exception:
                    logger.exception('Error during the task execution')

                countdown = interval
            else:
                countdown -= 1

            time.sleep(1)

        on_stop = getattr(self, 'on_stop', None)
        if on_stop is not None:
            on_stop()


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
                lines.append(six.u('  {} — {}').format(pattern, docstring))
            else:
                lines.append(six.u('  ') + pattern)

        lines.sort()
        lines.insert(0, six.u('I support following commands:'))

        request.respond(six.u('\n').join(lines))


class Pickler(pickle.Pickler):
    def __init__(self, file, protocol=None, global_objects=None):
        pickle.Pickler.__init__(self, file, protocol=protocol)
        self._global_objects = dict(
            (id(obj), persistent_id)
            for persistent_id, obj in (global_objects or {}).items()
        )

    def persistent_id(self, obj):
        return self._global_objects.get(id(obj))


class Unpickler(pickle.Unpickler):
    def __init__(self, file, global_objects=None):
        pickle.Unpickler.__init__(self, file)
        self._global_objects = global_objects or {}

    def persistent_load(self, obj_id):
        return self._global_objects[obj_id]


class Shelve(shelve.DbfilenameShelf):
    """A custom Shelve, to use custom Pickler and Unpickler.
    """
    def __init__(self, filename, global_objects=None):
        shelve.DbfilenameShelf.__init__(self, filename)
        self._global_objects = global_objects or {}

    def __getitem__(self, key):
        try:
            value = self.cache[key]
        except KeyError:
            f = six.BytesIO(self.dict[key])
            value = Unpickler(f, global_objects=self._global_objects).load()
            if self.writeback:
                self.cache[key] = value
        return value

    def __setitem__(self, key, value):
        if self.writeback:
            self.cache[key] = value
        f = six.BytesIO()
        p = Pickler(f, self._protocol, global_objects=self._global_objects)
        p.dump(value)
        self.dict[key] = f.getvalue()


class Storage(object):
    def __init__(self, filename, prefix='', global_objects=None):
        """Specials are used to restore references to some nonserializable objects,
        such as TheBot itself.
        """
        if isinstance(filename, Shelve):
            self._shelve = filename
        else:
            self._shelve = Shelve(filename, global_objects=global_objects)

        self.prefix = prefix
        self.global_objects = global_objects or {}

    def __getitem__(self, name):
        return self._shelve.__getitem__(self.prefix + name)

    def get(self, name, default=None):
        return self._shelve.get(self.prefix + name, default)

    def __setitem__(self, name, value):
        return self._shelve.__setitem__(self.prefix + name, value)

    def __delitem__(self, name):
        return self._shelve.__delitem__(self.prefix + name)

    def keys(self):
        return list(filter(lambda x: x.startswith(self.prefix), self._shelve.keys()))

    def clear(self):
        for key in self.keys():
            del self._shelve[key]

    def with_prefix(self, prefix):
        return Storage(self._shelve, prefix=prefix, global_objects=self.global_objects)

    def close(self):
        self._shelve.close()


class Config(object):
    def read_from_file(self, filename):
        with open(filename) as f:
            self.read_from_string(f.read())

    def read_from_string(self, data):
        data = yaml.load(data)

        # This complex code allows you
        # to translate such YAML config:
        #
        # adapters: [xmpp, http]
        # xmpp:
        #   jid: thebot@ya.ru
        # http:
        #   port: 9000
        #
        # into a config with attributes `xmpp_jid` and `http_port`.
        for key in ('plugins', 'adapters'):
            for item in data.get(key, []):
                item_settings = data.pop(item, None)
                if item_settings is not None:
                    for k, v in item_settings.items():
                        data[item + '_' + k] = v


        for key, value in data.items():
            setattr(self, key, value)

    def update_from_args(self, args):
        """Gets settings from the Namespace object, generated by argparse."""
        for key, value in args._get_kwargs():
            if value is not None:
                if key in ('adapters', 'plugins'):
                    value = value.split(',')

                setattr(self, key, value)


class Bot(object):
    def __init__(self, command_line_args=[], adapters=None, plugins=None, config_dict={}):
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
            if isinstance(value, six.string_types):
                try:
                    module = importlib.import_module('thebot_' + value)
                except ImportError:
                    module = importlib.import_module('thebot.batteries.' + value)

                loaded_value = getattr(module, cls)
                if not hasattr(loaded_value, 'name'):
                    loaded_value.name = value
                return loaded_value

            return value


        config_filename = 'thebot.conf'
        config = Config()

        config.read_from_string("""
            adapters: [console]
            plugins: [image]
            unittest: no
            storage_filename: thebot.storage
            log_filename: thebot.log
            verbose: no
        """)

        if os.path.exists(config_filename):
            config.read_from_file(config_filename)

        parser = Bot.get_general_options()
        args, unknown = parser.parse_known_args(
            list(filter(lambda x: x not in ('--help', '-h'), command_line_args))
        )
        config.update_from_args(args)

        if adapters is None:
            adapter_classes = map(lambda a: load(a, 'Adapter'), config.adapters)
        else:
            # we've got adapters argument (it is used for testing purpose
            adapter_classes = adapters

        if plugins is None:
            plugin_classes = [load(a, 'Plugin') for a in  config.plugins]
        else:
            # we've got adapters argument (it is used for testing purpose
            plugin_classes = plugins

        plugin_classes.append(HelpPlugin)

        for cls in adapter_classes + plugin_classes:
            if hasattr(cls, 'get_options'):
                cls.get_options(parser)

        args = parser.parse_args(command_line_args)
        config.update_from_args(args)
        self.config = config

        for key, value in config_dict.items():
            setattr(self.config, key, value)

        self.storage = Storage(self.config.storage_filename, global_objects=dict(bot=self))

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

        self.patterns = [
            (utils.force_unicode(pattern), callback)
            for pattern, callback in self.patterns
        ]


    @staticmethod
    def get_general_options():
        parser = argparse.ArgumentParser(
            description='The Bot — Hubot\'s killer.'
        )
        parser.add_argument(
            '--verbose', '-v', action='store_true', default=None,
            help='Show more output. Default: False.'
        )
        parser.add_argument(
            '--log-filename',
            help='Log\'s filename. Default: thebot.log.'
        )
        parser.add_argument(
            '--storage-filename',
            help='Path to a database file, used for TheBot\'s memory. Default: thebot.storage.'
        )

        group = parser.add_argument_group('General options')
        group.add_argument(
            '--adapters', '-a',
            help='Adapters to use. You can specify a comma-separated list to use more than one adapter. Default: console.',
        )
        group.add_argument(
            '--plugins', '-p',
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
        self.storage.close()

    def get_adapter(self, name):
        """Returns adapter by it's name."""
        for adapter in self.adapters:
            if getattr(adapter, 'name', None) == name:
                return adapter
        raise KeyError(six.u('Adapter {} not found').format(name))

    def get_plugin(self, name):
        """Returns plugin by it's name."""
        for plugin in self.plugins:
            if getattr(plugin, 'name', None) == name:
                return plugin
        raise KeyError(six.u('Plugin {} not found').format(name))


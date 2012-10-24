# coding: utf-8
from __future__ import absolute_import, unicode_literals

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

try:
    from collections import MutableMapping
except ImportError:
    from UserDict import DictMixin as MutableMapping


from . import utils

__version__ = pkg_resources.get_distribution(__name__).version


# pass this object to callback, to terminate the bot
EXIT = object()


class Request(object):
    def __init__(self, message):
        self.message = message

    def respond(self, message):
        """Bot will use this method to reply directly to the user."""
        raise NotImplementedError('You have to implement \'respond\' method in you Request class.')

    def shout(self, message):
        """This method will be used to say something to the channel or a chatroom."""
        self.respond(message)


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
                    pattern.plugin_name = self.name
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


class Re(object):
    def __init__(self, pattern):
        self.pattern = pattern
        self._re = None

    def __unicode__(self):
        return self.pattern

    def match(self, message):
        if self._re is not None:
            return self._re.match(message)


class PatternRe(Re):
    def __init__(self, pattern):
        super(PatternRe, self).__init__(pattern)
        self._re = re.compile('.*' + self.pattern + '.*')


class CommandRe(Re):
    def __init__(self, pattern):
        super(CommandRe, self).__init__(pattern)
        self._re = re.compile('^' + pattern + '$')


def _make_routing_decorator(pattern_cls):
    def decorator(pattern):
        """Decorator to assign routes to plugin's methods.
        """
        def deco(func):
            if getattr(func, '_patterns', None) is None:
                func._patterns = []
            func._patterns.append(pattern_cls(pattern))
            return func
        return deco
    return decorator


on_pattern = _make_routing_decorator(PatternRe)
on_command = _make_routing_decorator(CommandRe)


class HelpPlugin(Plugin):
    name = 'help'

    @on_command('help')
    def help(self, request):
        """Shows a help."""
        lines = []
        commands = []
        reactions = []

        for pattern, callback in self.bot.patterns:
            if isinstance(pattern, CommandRe):
                commands.append((pattern, callback))
            else:
                reactions.append((pattern, callback))

        def gen_docs(pattern_list):
            current_plugin = None
            previous_callback = None

            for pattern, callback in pattern_list:
                if current_plugin != pattern.plugin_name:
                    current_plugin = pattern.plugin_name
                    lines.append('  Plugin \'{}\':'.format(current_plugin))

                docstring = utils.force_unicode(callback.__doc__)
                if not docstring:
                    docstring = 'No description'

                if previous_callback != callback:
                    lines.append('    {} — {}'.format(pattern.pattern, docstring))
                else:
                    lines.append('    ' + pattern.pattern)

                previous_callback = callback

        lines.append('I support following commands:')
        gen_docs(commands)
        lines.append('')
        lines.append('And react on following patterns:')
        gen_docs(reactions)

        request.respond('\n'.join(lines))


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


class Storage(MutableMapping):
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

    def __setitem__(self, name, value):
        return self._shelve.__setitem__(self.prefix + name, value)

    def __delitem__(self, name):
        return self._shelve.__delitem__(self.prefix + name)

    def __len__(self):
        return sum(1 for key in self)

    def __iter__(self):
        prefix_len = len(self.prefix)
        return (
            key[prefix_len:]
            for key in self._shelve.keys()
                if key.startswith(self.prefix)
        )

    def keys(self):
        return list(self)

    def clear(self):
        for key in self.keys():
            del self._shelve[self.prefix + key]

    def with_prefix(self, prefix):
        return Storage(self._shelve, prefix=self.prefix + prefix, global_objects=self.global_objects)

    def close(self):
        self._shelve.close()


class Config(object):
    def __init__(self):
        self._data = {}

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


        self._data.update(data)

    def update_from_dict(self, args):
        """Gets settings from the Namespace object, generated by argparse."""
        for key, value in args.items():
            if value is not None:
                if key in ('adapters', 'plugins'):
                    value = value.split(',')

                self._data[key] = value

    def __repr__(self):
        return 'Config: {}'.format(self._data)

    def __getattr__(self, name):
        return self._data[name]


class Bot(object):
    def __init__(
            self,
            command_line_args=[],
            adapters=None,
            plugins=None,
            config_dict={},
            config_filename='thebot.conf',
        ):

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


        default_config = """
            unittest: no
        """

        # read config first time, to figure out possible adapter
        config = Config()
        config.read_from_string(default_config)

        parser = Bot.get_general_options()
        defaults = dict(parser.parse_args([])._get_kwargs())
        config.update_from_dict(defaults)

        if os.path.exists(config_filename):
            config.read_from_file(config_filename)

        args, unknown = parser.parse_known_args(
            list(filter(lambda x: x not in ('--help', '-h'), command_line_args))
        )
        # we override options only if there was specified value different from default
        args = dict(
            (key, value)
            for key, value in args._get_kwargs()
                if value != defaults.get(key)
        )
        config.update_from_dict(args)


        # now, load plugin and adapter classes, collect their options
        # and parse command line again

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


        # now, reread config to write there all defaults from all plugins
        config = Config()
        config.read_from_string(default_config)

        # getting options' defaults from parser
        defaults = dict(parser.parse_args([])._get_kwargs())
        config.update_from_dict(defaults)

        # now applying settings from the config file
        if os.path.exists(config_filename):
            config.read_from_file(config_filename)

        # and finally, override them with command line options
        # if there was specified value different from default
        args = parser.parse_args(command_line_args)
        args = dict(
            (key, value)
            for key, value in args._get_kwargs()
                if value != defaults.get(key)
        )
        config.update_from_dict(args)
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
            callbacks = p.get_callbacks()
            self.patterns.extend(callbacks)

    @staticmethod
    def get_general_options():
        parser = argparse.ArgumentParser(
            description='The Bot — Hubot\'s killer.'
        )
        parser.add_argument(
            '--verbose', '-v', action='store_true', default=False,
            help='Show more output. Default: False.'
        )
        parser.add_argument(
            '--log-filename', default='thebot.log',
            help='Log\'s filename. Default: thebot.log.'
        )
        parser.add_argument(
            '--storage-filename', default='thebot.storage',
            help='Path to a database file, used for TheBot\'s memory. Default: thebot.storage.'
        )

        group = parser.add_argument_group('General options')
        group.add_argument(
            '--adapters', '-a', default='console',
            help='Adapters to use. You can specify a comma-separated list to use more than one adapter. Default: console.',
        )
        group.add_argument(
            '--plugins', '-p', default='image,math,todo',
            help='Plugins to use. You can specify a comma-separated list to use more than one plugin. Default: image.',
        )
        return parser

    def on_request(self, request, direct=True):
        if request is EXIT:
            self.exiting = True
        else:
            for pattern, callback in self.patterns:
                match = pattern.match(request.message)
                if match is not None:
                    result = callback(request, **match.groupdict())
                    if result is not None:
                        raise RuntimeError('Plugin {0} should not return response directly. Use request.respond(some message).')
                    break
            else:
                if direct:
                    # If message wass addressed to TheBot, then it
                    # should report that he does not know such command.
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
        raise KeyError('Adapter {} not found'.format(name))

    def get_plugin(self, name):
        """Returns plugin by it's name."""
        for plugin in self.plugins:
            if getattr(plugin, 'name', None) == name:
                return plugin
        raise KeyError('Plugin {} not found'.format(name))


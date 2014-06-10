# coding: utf-8
from __future__ import absolute_import, unicode_literals

import argparse
import importlib
import logging
import os
import pickle
import pkg_resources
import re
import server_reloader
import shelve
import six
import textwrap
import threading
import time
import yaml

from .utils import MutableMapping, force_str, printable

__version__ = pkg_resources.get_distribution(__name__).version


# pass this object to callback, to terminate the bot
EXIT = object()


@printable
class User(object):
    def __init__(self, id):
        self.id = id

    def __unicode__(self):
        return self.id

    def __eq__(self, another):
        return self.id == another.id


@printable
class Room(object):
    def __init__(self, id):
        self.id = id

    def __unicode__(self):
        return self.id

    def __eq__(self, another):
        return self.id == another.id


@printable
class Request(object):
    def __init__(self, adapter, message, user, room=None, refer_by_name=False):
        self.adapter = adapter
        self.message = message
        self.user = user
        self.room = room
        self.refer_by_name = refer_by_name

    def __unicode__(self):
        result = '{} from {}'.format(self.message, self.user)
        if self.room:
            result += ' at {}'.format(self.room)
        return result

    def respond(self, message):
        self.adapter.send(
            message,
            user=self.user,
            room=self.room,
            refer_by_name=self.refer_by_name,
        )

    def shout(self, message):
        """This method should be used to say something to the channel or a chatroom."""
        self.adapter.send(
            message,
            room=self.room,
        )



@printable
class Adapter(object):
    def __init__(self, bot, callback):
        self.bot = bot
        self.callback = callback

    def __unicode__(self):
        return self.name

    def start(self):
        """You have to override this method, if you plugin requires some background activity.

        Here you can create a thread, but don't forget to make its `daemon` attrubute equal to True.
        """

    def is_online(self, user):
        return False


@printable
class Plugin(object):
    def __init__(self, bot):
        self.bot = bot
        self.storage = self.bot.storage.with_prefix(self.__module__ + ':')
        self.logger = logging.getLogger('thebot.plugin.' + self.name)

    def __unicode__(self):
        return self.name

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


@printable
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
    """Shows help and basic information about TheBot."""
    name = 'help'

    def __init__(self, *args, **kwargs):
        super(HelpPlugin, self).__init__(*args, **kwargs)
        self._started_at = time.time()

    @on_command('help')
    def show_commands(self, request):
        """Show available commands."""

        lines = ['This is the list of available plugins:']

        def gen_line(plugin):
            if plugin.__doc__:
                return '  * {} — {}'.format(plugin.name, plugin.__doc__.split('\n')[0])
            else:
                return '  * {}'.format(plugin.name)

        lines.extend(sorted(map(gen_line, self.bot.plugins)))

        lines.append('Use \'help <plugin>\' to learn about each plugin.')
        request.respond('\n'.join(lines))


    @on_command('help (?P<plugin>.*)')
    def help(self, request, plugin):
        """Show help on given plugin."""
        lines = []
        commands = []
        reactions = []

        def gen_docs(pattern_list):
            previous_callback = None

            for pattern, callback in pattern_list:
                docstring = utils.force_unicode(callback.__doc__)
                if not docstring:
                    docstring = 'No description'

                if previous_callback != callback:
                    lines.append('    {} — {}'.format(pattern.pattern, docstring))
                else:
                    lines.append('    ' + pattern.pattern)

                previous_callback = callback

        try:
            plugin = self.bot.get_plugin(plugin)
        except KeyError as e:
            request.respond(''.join(e.args))
            return

        # dividing all patterns to commands and hearings
        for pattern, callback in plugin.get_callbacks():
            if isinstance(pattern, CommandRe):
                commands.append((pattern, callback))
            else:
                reactions.append((pattern, callback))

        if plugin.__doc__:
            splitted = plugin.__doc__.split('\n', 1)
            doc = ' — {}'.format(splitted[0])

            if len(splitted) == 2:
                remaining = splitted[1]
                remaining = remaining.rstrip()
                remaining = textwrap.dedent(remaining)
                doc += '\n{}'.format(remaining)
        else:
            doc = '.'

        lines.append('Plugin \'{}\'{}\n'.format(plugin.name, doc))

        if commands:
            lines.append('Provides following commands:')
            gen_docs(commands)

        if reactions:
            if lines:
                lines.append('')

            lines.append('And reacts on these patterns:')
            gen_docs(reactions)

        request.respond('\n'.join(lines))

    @on_command('version')
    def version(self, request):
        """Shows TheBot's version."""
        request.respond('My version is "{}".'.format(__version__))

    @on_command('uptime')
    def uptime(self, request):
        """Shows TheBot's uptime."""
        uptime = time.time() - self._started_at
        days = int(uptime / (24 * 3600))
        hours = int((uptime % (24 * 3600) / 3600))
        minutes = int((uptime % 3600 / 60))
        seconds = int((uptime % 60))

        uptime ='My uptime is '
        if days:
            uptime += '{} day(s)'.format(days)
        elif hours:
            uptime += '{} hour(s)'.format(hours)
        elif minutes:
            uptime += '{} minute(s).'.format(minutes)
        else:
            uptime += '{} second(s).'.format(seconds)

        request.respond(uptime)


@printable
class Stub(object):
    """A stub class to replace objects which can't be unpickled.

    It allows to call any method or access any attribute.
    """
    def __init__(self, name):
        self.name = name

    def __getattr__(self, name):
        return Stub(self.name + '.' + name)

    def __call__(self, *args, **kwargs):
        return None

    def __unicode__(self):
        return self.name


class Pickler(pickle.Pickler):
    def __init__(self, file, protocol=None, global_objects=None):
        pickle.Pickler.__init__(self, file, protocol=protocol)
        self._global_objects = dict(
            (id(obj), persistent_id)
            for persistent_id, obj in (global_objects or {}).items()
        )

    def persistent_id(self, obj):
        if isinstance(obj, Stub):
            return obj.name
        return self._global_objects.get(id(obj))


class Unpickler(pickle.Unpickler):
    """A custom unpickler, to restore references to adapters, plugins and the bot."""
    def __init__(self, file, global_objects=None):
        pickle.Unpickler.__init__(self, file)
        self._global_objects = global_objects or {}

    def persistent_load(self, obj_id):
        try:
            return self._global_objects[obj_id]
        except KeyError:
            return Stub(obj_id)


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
        value = f.getvalue()
        self.dict[key] = value


class Storage(utils.MutableMapping):
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
        return self._shelve.__getitem__(utils.force_str(self.prefix + name))

    def __setitem__(self, name, value):
        return self._shelve.__setitem__(utils.force_str(self.prefix + name), value)

    def __delitem__(self, name):
        return self._shelve.__delitem__(utils.force_str(self.prefix + name))

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
            del self[key]

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
        head = name
        tail = ''
        data = self._data
        
        while head:
            if head in data:
                data = data[head]
                head = tail
                tail = ''
            else:
                if '_' in head:
                    head, part = head.rsplit('_', 1)
                    tail = part + '_' + tail
                else:
                    raise AttributeError('Attribute {0} does not exist'.format(name))
        return data


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

        def create_loader(cls='Adapter'):
            def load(name):
                """Returns class by it's name.

                Given a 'irc' string it will try to load the following:

                1) from thebot_irc import Adapter
                2) from thebot.batteries.irc import Adapter

                If all of them fail, it will raise ImportError
                """

                if isinstance(name, six.string_types):
                    try:
                        module = importlib.import_module('thebot_' + name)
                    except ImportError:
                        module = importlib.import_module('thebot.batteries.' + name)

                    value = getattr(module, cls)
                    if not hasattr(value, 'name'):
                        value.name = name
                else:
                    value = name

                return value

            loaded = set()

            def loader(names):
                """Recursive loader."""
                for name in names:
                    if name not in loaded:
                        cls = load(name)
                        loaded.add(name)

                        deps = getattr(cls, 'deps', ())
                        for dep in loader(deps):
                            yield dep
                        yield cls

            return loader


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
        load_plugins = create_loader('Plugin')
        load_adapters = create_loader('Adapter')

        if adapters is None:
            adapters = config.adapters
        adapter_classes = list(load_adapters(adapters))

        if plugins is None:
            plugins = config.plugins

        plugin_classes = list(load_plugins(plugins))
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

        logging.basicConfig(
            filename=self.config.log_filename,
            format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            level=logging.DEBUG if self.config.verbose else logging.WARNING,
        )

        with open(self.config.pid_filename, 'w') as f:
            f.write(str(os.getpid()))

        # adapters and plugins initialization
        global_objects = dict(bot=self)

        for adapter in adapter_classes:
            a = adapter(self, callback=self.on_request)
            global_objects[a.name] = a
            a.start()
            self.adapters.append(a)

        self.storage = Storage(self.config.storage_filename, global_objects=global_objects)

        for plugin_cls in plugin_classes:
            p = plugin_cls(self)
            self.plugins.append(p)
            callbacks = p.get_callbacks()
            self.patterns.extend(callbacks)

        if self.config.reload_on_changes:
            server_reloader.trigger_on_code_changes()

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
            '--pid-filename', default='thebot.pid',
            help='TheBot\'s pid filename. Default: thebot.pid.'
        )
        parser.add_argument(
            '--storage-filename', default='thebot.storage',
            help='Path to a database file, used for TheBot\'s memory. Default: thebot.storage.'
        )
        parser.add_argument(
            '--reload-on-changes', action='store_true', default=False,
            help='Track source files changes and restart the bot. Default: False.'
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
                    try:
                        result = callback(request, **match.groupdict())
                    except Exception:
                        logging.getLogger('thebot.core.on_request').exception(
                            'During processing "{0}" request'.format(request))
                    else:
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
        raise KeyError('Adapter {} not found.'.format(name))

    def get_plugin(self, name):
        """Returns plugin by it's name."""
        for plugin in self.plugins:
            if getattr(plugin, 'name', None) == name:
                return plugin
        raise KeyError('Plugin {} not found.'.format(name))


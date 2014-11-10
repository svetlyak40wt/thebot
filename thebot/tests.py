# coding: utf-8

from __future__ import absolute_import, unicode_literals

import times
import datetime
import mock
import thebot
import sys
import re

from thebot import Request, User, Adapter, Plugin, Storage, Config, on_pattern, on_command, Stub
from thebot.batteries import todo
from thebot.batteries.identity import Person
from nose.tools import eq_, assert_raises
from contextlib import closing

PYTHON_VERSION = '-'.join(map(str, sys.version_info[:3]))
STORAGE_FILENAME = 'unittest-{}.storage'.format(PYTHON_VERSION)


class Bot(thebot.Bot):
    """Test bot which uses slightly different settings."""
    def __init__(self, *args, **kwargs):
        kwargs['config_dict'] = dict(
            unittest=True,
            log_filename='unittest.log',
            storage_filename=STORAGE_FILENAME,
        )
        kwargs['config_filename'] = 'unexistent.conf'
        super(Bot, self).__init__(*args, **kwargs)

    def close(self):
        self.storage.clear()
        super(Bot, self).close()


class TestAdapter(Adapter):
    name = 'test'

    def __init__(self, *args, **kwargs):
        super(TestAdapter, self).__init__(*args, **kwargs)
        self._lines = []
        self._offline_users = set()

    def send(self, message, user=None, room=None, refer_by_name=None):
        self._lines.append(message)

    def write(self, input_line, user='some user'):
        """This method is for test purpose.
        """
        name = 'Thebot, '

        if input_line.startswith(name):
            self.callback(Request(self, input_line[len(name):], user=User(user)), direct=True)
        else:
            self.callback(Request(self, input_line, user=User(user)), direct=False)

    def offline(self, user):
        self._offline_users.add(user)

    def is_online(self, user):
        return not user.id in self._offline_users


class TestPlugin(Plugin):
    """A simple test plugin.

    With extended documentation.
    Which can be multiline, and will be shown as plugin's help.
    """
    name = 'test'
    @on_pattern('cat')
    def i_like_cats(self, request):
        """Shows how TheBot likes cats."""
        request.respond('I like cats!!!')

    @on_command('search (?P<this>.*)')
    @on_command('find (?P<this>.*)')
    def find(self, request, this=None):
        """Making a fake search of the term."""
        request.respond('I found {0}'.format(this))


def test_install_adapters():
    with closing(Bot(adapters=[TestAdapter], plugins=[])) as bot:
        assert len(bot.adapters) == 1


def test_install_plugins():
    with closing(Bot(adapters=[], plugins=[TestPlugin])) as bot:
        eq_(0, len(bot.adapters))
        eq_(2, len(bot.plugins)) # Help plugin is added by default
        eq_(7, len(bot.patterns))


def test_one_line():
    with closing(Bot(adapters=[TestAdapter], plugins=[TestPlugin])) as bot:
        adapter = bot.get_adapter('test')

        eq_(adapter._lines, [])
        adapter.write('I have a cat')
        eq_(adapter._lines, ['I like cats!!!'])

        adapter.write('find Umputun')
        eq_(adapter._lines[-1], 'I found Umputun')


def test_unknown_command():
    """TheBot reports about unknown commands, addressed directly to him."""

    with closing(Bot(adapters=[TestAdapter], plugins=[TestPlugin])) as bot:
        adapter = bot.adapters[0]

        eq_(adapter._lines, [])
        adapter.write('Thebot, some command')
        eq_(adapter._lines, ['I don\'t know command "some command".'])


def test_exception_raised_if_plugin_returns_not_none():
    class BadPlugin(Plugin):
        name = 'bad'
        @on_command('do')
        def do(self, request):
            return 'Hello world'


    with closing(Bot(adapters=[TestAdapter], plugins=[BadPlugin])) as bot:
        adapter = bot.adapters[0]

        assert_raises(RuntimeError, adapter.write, 'do')


def test_simple_storage():
    with closing(Storage(STORAGE_FILENAME)) as storage:
        storage.clear()

        eq_([], storage.keys())

        storage['blah'] = 'minor'
        storage['one'] = {'some': 'dict'}

        eq_(['blah', 'one'], sorted(storage.keys()))
        eq_('minor', storage['blah'])


def test_storage_nesting():
    with closing(Storage(STORAGE_FILENAME)) as storage:
        storage.clear()

        first = storage.with_prefix('first:')
        second = storage.with_prefix('second:')

        eq_([], storage.keys())

        first['blah'] = 'minor'
        second['one'] = {'some': 'dict'}

        eq_(['first:blah', 'second:one'], sorted(storage.keys()))
        eq_(['first:blah', 'second:one'], sorted(list(storage)))

        eq_(['blah'], first.keys())
        eq_(['blah'], list(first))

        eq_(['one'], second.keys())
        eq_(['one'], list(second))

        eq_('minor', first['blah'])
        assert_raises(KeyError, lambda: second['blah'])

        first.clear()
        eq_(['second:one'], sorted(storage.keys()))
        eq_(['second:one'], sorted(list(storage)))

def test_storage_deep_nesting():
    with closing(Storage(STORAGE_FILENAME)) as storage:
        storage.clear()

        first = storage.with_prefix('first:')
        second = first.with_prefix('second:')

        second['blah'] = 'minor'

        eq_(['first:second:blah'], storage.keys())
        eq_(['second:blah'], first.keys())
        eq_(['blah'], second.keys())


def test_help_command():
    with closing(Bot(adapters=[TestAdapter], plugins=[TestPlugin])) as bot:
        adapter = bot.adapters[0]

        adapter.write('help')
        eq_(
            [
                'This is the list of available plugins:\n'
                '  * help — Shows help and basic information about TheBot.\n'
                '  * test — A simple test plugin.\n'
                'Use \'help <plugin>\' to learn about each plugin.'
            ],
            adapter._lines
        )


def test_help_plugin_command():
    with closing(Bot(adapters=[TestAdapter], plugins=[TestPlugin])) as bot:
        adapter = bot.adapters[0]

        adapter.write('help test')
        eq_(
            [
                'Plugin \'test\' — A simple test plugin.\n'
                '\n'
                'With extended documentation.\n'
                'Which can be multiline, and will be shown as plugin\'s help.\n'
                '\n'
                'Provides following commands:\n'
                '    find (?P<this>.*) — Making a fake search of the term.\n'
                '    search (?P<this>.*)\n'
                '\n'
                'And reacts on these patterns:\n'
                '    cat — Shows how TheBot likes cats.'
            ],
            adapter._lines
        )


def test_help_plugin_not_found():
    with closing(Bot(adapters=[TestAdapter], plugins=[TestPlugin])) as bot:
        adapter = bot.adapters[0]

        adapter.write('help blah')
        eq_('Plugin blah not found.', adapter._lines[-1])


def test_delete_from_storage():
    with closing(Storage(STORAGE_FILENAME)) as storage:
        storage.clear()

        storage['blah'] = 'minor'
        del storage['blah']

        eq_([], sorted(storage.keys()))


def test_storage_is_iterable_as_dict():
    with closing(Storage(STORAGE_FILENAME)) as storage:
        storage.clear()

        storage['blah'] = 'minor'
        storage['another'] = 'option'

        eq_(['another', 'blah'], sorted(storage.keys()))
        eq_(['minor', 'option'], sorted(storage.values()))
        eq_([('another', 'option'), ('blah', 'minor')], sorted(storage.items()))

        eq_(
            ['another', 'blah'],
            sorted(item for item in storage)
        )



def test_storage_restores_bot_attribute():
    with closing(Bot(adapters=[TestAdapter], plugins=[TestPlugin])) as bot:
        adapter = bot.get_adapter('test')
        original = Request(adapter, 'some text', 'a user')

        bot.storage['request'] = original

        restored = bot.storage['request']
        eq_(restored.adapter, original.adapter)


def test_storage_with_prefix_keeps_global_objects():
    with closing(Storage(STORAGE_FILENAME, global_objects=dict(some='value'))) as storage:
        prefixed = storage.with_prefix('nested:')

        eq_(storage.global_objects, prefixed.global_objects)


def test_get_adapter_by_name():
    with closing(Bot(adapters=[TestAdapter])) as bot:
        adapter = bot.get_adapter('test')
        assert isinstance(adapter, TestAdapter)


def test_todo_plugin():
    with closing(Bot(adapters=[TestAdapter], plugins=[todo.Plugin])) as bot:
        adapter = bot.get_adapter('test')

        adapter.write('remind at 2012-10-05 to Celebrate my birthday')
        adapter.write('remind at 2012-12-18 to Celebrate daughter\'s birthday')
        adapter.write('remind at 2012-09-01 to Write a doc for TheBot')
        adapter.write('my tasks')

        eq_(
            [
                'ok',
                'ok',
                'ok',
                '16) 2012-09-01 00:00 Write a doc for TheBot\n'
                'cd) 2012-10-05 00:00 Celebrate my birthday\n'
                '9c) 2012-12-18 00:00 Celebrate daughter\'s birthday',
            ],
            adapter._lines
        )


def test_todo_plugin_for_different_users():
    with closing(Bot(adapters=[TestAdapter], plugins=[todo.Plugin])) as bot:
        adapter = bot.get_adapter('test')

        adapter.write('remind at 2012-10-05 to Celebrate my birthday', user='blah')
        adapter.write('remind at 2012-12-18 to Celebrate daughter\'s birthday', user='minor')

        adapter._lines[:] = []
        adapter.write('my tasks', user='minor')

        eq_(
            [
                '9c) 2012-12-18 00:00 Celebrate daughter\'s birthday',
            ],
            adapter._lines
        )


def test_todo_remind():
    with closing(Bot(adapters=[TestAdapter], plugins=[todo.Plugin])) as bot:
        adapter = bot.get_adapter('test')
        plugin = bot.get_plugin('todo')


        adapter.write('set timezone Asia/Shanghai')
        # these are the local times
        adapter.write('remind at 2012-09-05 10:00 to do task1')
        adapter.write('remind at 2012-09-05 10:30 to do task2')

        with mock.patch.object(times, 'now') as now:
            # this is a server time in UTC
            # it is 10:01 at Shanghai (+8 hours)
            now.return_value = datetime.datetime(2012, 9, 5, 2, 1)

            adapter._lines[:] = []
            plugin._remind_users_about_their_tasks()

            eq_(['TODO: do task1 (03f9)'], adapter._lines)

            # but it does not reminds twice
            now.return_value = datetime.datetime(2012, 9, 5, 2, 12)

            adapter._lines[:] = []
            plugin._remind_users_about_their_tasks()
            eq_([], adapter._lines)


def test_todo_done():
    with closing(Bot(adapters=[TestAdapter], plugins=[todo.Plugin])) as bot:

        adapter = bot.get_adapter('test')


        adapter.write('set timezone Asia/Shanghai')
        adapter.write('remind at 2012-09-05 10:00 to do task1')
        adapter.write('remind at 2012-09-05 10:30 to do task2')
        adapter.write('03 done')

        adapter._lines[:] = []
        adapter.write('my tasks')

        eq_(
            [
                '26) 2012-09-05 10:30 do task2',
            ],
           adapter._lines
        )


def test_todo_remind_at_uses_timezones():
    with closing(Bot(adapters=[TestAdapter], plugins=[todo.Plugin])) as bot:
        adapter = bot.get_adapter('test')
        plugin = bot.get_plugin('todo')
        identity_plugin = bot.get_plugin('identity')
        identity = identity_plugin.get_identity_by_user(adapter, User('some user'))

        adapter.write('set timezone Asia/Shanghai')
        adapter.write('remind at 2012-09-05 00:00 to do task1')
        tasks = plugin._get_tasks(identity)
        eq_(datetime.datetime(2012, 9, 4, 16, 0), tasks[0][0])


def test_yaml_config():
    cfg = Config()
    cfg.read_from_string("""
adapters: [xmpp, irc]
irc:
    channels: [thebot, test]
xmpp:
    jid: thebot@ya.ru
""")

    eq_(['xmpp', 'irc'], cfg.adapters)
    eq_('thebot@ya.ru', cfg.xmpp_jid)


def test_get_config_values_from_nested_structures():
    cfg = Config()
    cfg.read_from_string("""
xmpp:
    jid: thebot@ya.ru
    notify:
       adapter: irc
       to_username: art
       
""")
    eq_('thebot@ya.ru', cfg.xmpp['jid'])
    eq_('thebot@ya.ru', cfg.xmpp_jid)

    eq_('irc', cfg.xmpp_notify_adapter)
    eq_('art', cfg.xmpp_notify_to_username)


def _get_identity_id(adapter):
    match = re.match(
        r'.*bind to ([0-9a-f]{40}).*',
        adapter._lines[-1]
    )
    assert match is not None
    return match.group(1)


def test_identity_create():
    with closing(Bot(adapters=[TestAdapter], plugins=['identity'])) as bot:
        adapter = bot.get_adapter('test')

        adapter.write('build identity', user='user1')
        identity = _get_identity_id(adapter)

        adapter.write('bind to {}'.format(identity), user='user2')

        adapter._lines[:] = []
        adapter.write('show my accounts', user='user1')

        eq_(
            'Your identities are:\n'
            '1) user1 (test, online)\n'
            '2) user2 (test, online)',
            adapter._lines[0]
        )


def test_identity_get_by_xxx():
    with closing(Bot(adapters=[TestAdapter], plugins=['identity'])) as bot:
        adapter = bot.get_adapter('test')
        plugin = bot.get_plugin('identity')

        adapter.write('build identity', user='user1')
        identity = _get_identity_id(adapter)

        adapter.write('bind to {}'.format(identity), user='user2')

        eq_(identity, plugin.get_identity_by_id(identity).id)
        eq_(identity, plugin.get_identity_by_user(adapter, User('user1')).id)
        eq_(identity, plugin.get_identity_by_user(adapter, User('user2')).id)

        eq_(None, plugin.get_identity_by_id('unexistent'))

        # for the new user, a new identity will be created
        new_identity = plugin.get_identity_by_user(adapter, User('unknown user'))
        assert new_identity.id != identity


def test_identity_show_my_identities_when_there_is_no_identity():
    with closing(Bot(adapters=[TestAdapter], plugins=['identity'])) as bot:
        adapter = bot.get_adapter('test')

        adapter._lines[:] = []
        adapter.write('show my accounts', user='user1')

        eq_(
            'Your identities are:\n'
            '1) user1 (test, online)',
            adapter._lines[0]
        )

def test_bind_to_another_identity():
    """Testing bind to another identity, when there is already exists another identity."""
    with closing(Bot(adapters=[TestAdapter], plugins=['identity'])) as bot:
        adapter = bot.get_adapter('test')
        plugin = bot.get_plugin('identity')

        adapter._lines[:] = []
        adapter.write('show my accounts', user='user1')

        eq_(
            'Your identities are:\n'
            '1) user1 (test, online)',
            adapter._lines[-1]
        )

        adapter.write('show my accounts', user='user2')

        eq_(
            'Your identities are:\n'
            '1) user2 (test, online)',
            adapter._lines[-1]
        )

        # there should be two identities now
        eq_(2, len(plugin.identities))
        # and two persons
        eq_(2, len(plugin.persons))

        # now let's bind user2 to user1
        adapter.write('build identity', user='user1')
        identity = _get_identity_id(adapter)

        adapter.write('bind to {}'.format(identity), 'user2')

        # now there should be only one identity
        eq_(1, len(plugin.identities))
        # and still two persons
        eq_(2, len(plugin.persons))
        # pointing to the same identity
        eq_(
            [identity, identity],
            list(plugin.persons.values())
        )

def test_persons_equality():
    with closing(Bot(adapters=[TestAdapter], plugins=['identity'])) as bot:
        adapter = bot.get_adapter('test')
        eq_(
            Person(adapter, User('tester')),
            Person(adapter, User('tester')),
        )


def test_users_equality():
    eq_(
        User('tester'),
        User('tester'),
    )


def test_unbind_from_identity():
    with closing(Bot(adapters=[TestAdapter], plugins=['identity'])) as bot:
        adapter = bot.get_adapter('test')

        adapter.write('build identity', user='user1')
        identity = _get_identity_id(adapter)
        adapter.write('bind to {}'.format(identity), user='user2')
        adapter.write('unbind', user='user2')

        adapter._lines[:] = []
        adapter.write('show my accounts', user='user1')

        eq_(
            'Your identities are:\n'
            '1) user1 (test, online)',
            adapter._lines[0]
        )


def test_notify_first_online_person():
    with closing(Bot(adapters=[TestAdapter], plugins=['notify'])) as bot:
        adapter = bot.get_adapter('test')
        plugin = bot.get_plugin('notify')

        adapter.write('build identity', user='user1')
        identity_id = _get_identity_id(adapter)
        adapter.write('bind to {}'.format(identity_id), user='user2')
        # now we have identity with two users

        adapter._lines[:] = []

        # first, check if first user will receive message
        eq_(True, plugin.notify(identity_id, 'hello 1'))
        eq_('hello 1', adapter._lines[-1])

        adapter.offline('user1')

        eq_(True, plugin.notify(identity_id, 'hello 2'))
        eq_('hello 2', adapter._lines[-1])

        adapter.offline('user2')

        eq_(2, len(adapter._lines))
        eq_(False, plugin.notify(identity_id, 'hello 3'))
        # no messages was sent, because all persons are offline
        eq_(2, len(adapter._lines))


def test_notification_priorities():
    class TestAdapter2(TestAdapter):
        name = 'test2'

    with closing(Bot(adapters=[TestAdapter, TestAdapter2], plugins=['notify'])) as bot:
        adapter1 = bot.get_adapter('test')
        adapter2 = bot.get_adapter('test2')

        plugin = bot.get_plugin('notify')

        adapter1.write('build identity', user='user1')
        identity_id = _get_identity_id(adapter1)
        adapter2.write('bind to {}'.format(identity_id), user='user2')
        # now we have identity with two users

        adapter1._lines[:] = []
        adapter2._lines[:] = []

        # without priorities, first user will receive message
        eq_(True, plugin.notify(identity_id, 'hello 1'))
        eq_('hello 1', adapter1._lines[-1])

        adapter1.write('set notification-priorities test2,test', user='user1')

        # now second adapter has higher priority
        eq_(True, plugin.notify(identity_id, 'hello 2'))
        eq_('hello 2', adapter2._lines[-1])


def test_set_get_settings():
    with closing(Bot(adapters=[TestAdapter], plugins=['settings', 'identity'])) as bot:
        adapter = bot.get_adapter('test')
        plugin = bot.get_plugin('settings')

        adapter.write('build identity', user='user1')
        identity_id = _get_identity_id(adapter)
        adapter.write('bind to {}'.format(identity_id), user='user2')
        # now we have identity with two users

        plugin.set(identity_id, 'some-key', 'blah')
        eq_('blah', plugin.get(identity_id, 'some-key'))

        adapter.write('set some-key some-value', user='user1')
        eq_('some-value', plugin.get(identity_id, 'some-key'))

        plugin.set(identity_id, 'some-key', 'another-value')
        adapter.write('get some-key', user='user2')
        eq_('some-key = another-value', adapter._lines[-1])

        adapter.write('my settings', user='user1')
        eq_('You settings are:\nsome-key = another-value', adapter._lines[-1])


def test_load_dependencies():
    """Plugin notify should depend on settings, and settings plugin in it's
    turn, depends on identity.
    """

    with closing(Bot(adapters=[], plugins=['notify'])) as bot:
        settings = bot.get_plugin('settings')
        assert settings is not None

        identity = bot.get_plugin('identity')
        assert identity is not None

def test_stub_methods():
    stub = Stub('blah')
    eq_('blah', stub.name)
    eq_('blah.is_online', '{}'.format((stub.is_online)))
    eq_(None, stub.is_online())


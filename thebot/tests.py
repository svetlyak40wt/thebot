# coding: utf-8

from __future__ import absolute_import, unicode_literals

import times
import datetime
import mock
import thebot
import sys

from thebot import Request, Adapter, Plugin, Storage, Config, on_pattern, on_command
from thebot.batteries import todo
from nose.tools import eq_, assert_raises
from contextlib import closing


class Bot(thebot.Bot):
    """Test bot which uses slightly different settings."""
    def __init__(self, *args, **kwargs):
        python_version = '-'.join(map(str, sys.version_info[:3]))
        kwargs['config_dict'] = dict(
            unittest=True,
            log_filename='unittest.log',
            storage_filename='unittest-{}.storage'.format(python_version),
        )
        kwargs['config_filename'] = 'unexistent.conf'
        super(Bot, self).__init__(*args, **kwargs)

        self.storage.clear()


class TestRequest(Request):
    def __init__(self, message, bot, user):
        super(TestRequest, self).__init__(message)
        self.bot = bot
        self.user = user

    def respond(self, message):
        adapter = self.bot.get_adapter('test')
        adapter._lines.append(message)

    def get_user(self):
        return self.user


class TestAdapter(Adapter):
    name = 'test'

    def __init__(self, *args, **kwargs):
        super(TestAdapter, self).__init__(*args, **kwargs)
        self._lines = []

    def write(self, input_line, user='some user'):
        """This method is for test purpose.
        """
        name = 'Thebot, '

        if input_line.startswith(name):
            self.callback(TestRequest(input_line[len(name):], self.bot, user), direct=True)
        else:
            self.callback(TestRequest(input_line, self.bot, user), direct=False)


class TestPlugin(Plugin):
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
        eq_(4, len(bot.patterns))


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
    storage = Storage('/tmp/thebot.storage')
    storage.clear()

    eq_([], storage.keys())

    storage['blah'] = 'minor'
    storage['one'] = {'some': 'dict'}

    eq_(['blah', 'one'], sorted(storage.keys()))
    eq_('minor', storage['blah'])


def test_storage_nesting():
    storage = Storage('/tmp/thebot.storage')
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
    storage = Storage('/tmp/thebot.storage')
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
                'I support following commands:\n'
                '  Plugin \'test\':\n'
                '    find (?P<this>.*) — Making a fake search of the term.\n'
                '    search (?P<this>.*)\n'
                '  Plugin \'help\':\n'
                '    help — Shows a help.\n'
                '\n'
                'And react on following patterns:\n'
                '  Plugin \'test\':\n'
                '    cat — Shows how TheBot likes cats.'
            ],
            adapter._lines
        )


def test_delete_from_storage():
    storage = Storage('/tmp/thebot.storage')
    storage.clear()

    storage['blah'] = 'minor'
    del storage['blah']

    eq_([], sorted(storage.keys()))


def test_storage_is_iterable_as_dict():
    storage = Storage('/tmp/thebot.storage')
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
        storage = Storage('/tmp/thebot.storage', global_objects=dict(bot=bot))
        storage.clear()

        original = Request('blah')
        original.bot = bot

        storage['request'] = original

        restored = storage['request']
        eq_(restored.bot, original.bot)


def test_storage_with_prefix_keeps_global_objects():
    storage = Storage('/tmp/thebot.storage', global_objects=dict(some='value'))
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


        adapter.write('set my timezone to Asia/Shanghai')
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


        adapter.write('set my timezone to Asia/Shanghai')
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


        adapter.write('set my timezone to Asia/Shanghai')
        adapter.write('remind at 2012-09-05 00:00 to do task1')
        tasks = plugin._get_tasks('some user')
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


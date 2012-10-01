# coding: utf-8

from thebot import Bot, Request, Adapter, Plugin, Storage, route
from nose.tools import eq_, assert_raises


class TestAdapter(Adapter):
    def __init__(self, *args, **kwargs):
        super(TestAdapter, self).__init__(*args, **kwargs)
        self._lines = []

    def write(self, input_line):
        """This method is for test purpose.
        """
        lines = self._lines
        class TestRequest(Request):
            def respond(self, message):
                lines.append(message)

        self.callback(TestRequest(input_line))


class TestPlugin(Plugin):
    @route('^show me a cat$')
    def show_a_cat(self, request):
        """Shows a cat."""
        request.respond('the Cat')

    @route('^find (?P<this>.*)$')
    def find(self, request, this=None):
        """Making a fake search of the term."""
        request.respond('I found {0}'.format(this))


def test_install_adapters():
    bot = Bot(adapters=[TestAdapter], plugins=[])
    assert len(bot.adapters) == 1


def test_install_plugins():
    bot = Bot(adapters=[], plugins=[TestPlugin])
    eq_(0, len(bot.adapters))
    eq_(2, len(bot.plugins)) # Help plugin is added by default
    eq_(3, len(bot.patterns))


def test_one_line():
    bot = Bot(adapters=[TestAdapter], plugins=[TestPlugin])
    adapter = bot.adapters[0]

    eq_(adapter._lines, [])
    adapter.write('show me a cat')
    eq_(adapter._lines, ['the Cat'])

    adapter.write('find Umputun')
    eq_(adapter._lines[-1], 'I found Umputun')


def test_unknown_command():
    bot = Bot(adapters=[TestAdapter], plugins=[TestPlugin])
    adapter = bot.adapters[0]

    eq_(adapter._lines, [])
    adapter.write('some command')
    eq_(adapter._lines, ['I don\'t know command "some command".'])


def test_exception_raised_if_plugin_returns_not_none():
    class BadPlugin(Plugin):
        @route('^do$')
        def do(self, request):
            return 'Hello world'


    bot = Bot(adapters=[TestAdapter], plugins=[BadPlugin])
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
    eq_(['first:blah'], sorted(first.keys()))
    eq_(['second:one'], sorted(second.keys()))

    eq_('minor', first['blah'])
    assert_raises(KeyError, lambda: second['blah'])

    first.clear()
    eq_(['second:one'], sorted(storage.keys()))


def test_help_command():
    bot = Bot(adapters=[TestAdapter], plugins=[TestPlugin])
    adapter = bot.adapters[0]

    adapter.write('help')
    eq_(
        [
            'I support following commands:\n'
            '  ^find (?P<this>.*)$ — Making a fake search of the term.\n'
            '  ^help$ — Shows a help.\n'
            '  ^show me a cat$ — Shows a cat.'
        ],
        adapter._lines
    )


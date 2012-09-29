from thebot import Bot, Request, Adapter, Plugin
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
    def get_callbacks(self):
        return [
            ('^show me a cat$', self.show_a_cat),
            ('^find (?P<this>.*)$', self.find),
        ]

    def show_a_cat(self, request, match):
        request.respond('the Cat')

    def find(self, request, match):
        request.respond('I found {0}'.format(match.group('this')))


def test_install_adapters():
    bot = Bot(adapters=[TestAdapter], plugins=[])
    assert len(bot.adapters) == 1


def test_install_plugins():
    bot = Bot(adapters=[], plugins=[TestPlugin])
    assert len(bot.adapters) == 0
    assert len(bot.plugins) == 1
    assert len(bot.patterns) == 2


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
        def get_callbacks(self):
            return [
                ('^do$', self.do),
            ]

        def do(self, request, match):
            return 'Hello world'


    bot = Bot(adapters=[TestAdapter], plugins=[BadPlugin])
    adapter = bot.adapters[0]

    assert_raises(RuntimeError, adapter.write, 'do')

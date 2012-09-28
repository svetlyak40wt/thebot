from __future__ import absolute_import

import threading
import irc
import thebot


class IRCRequest(thebot.Request):
    def __init__(self, message, bot, nick, channel):
        super(IRCRequest, self).__init__(message)
        self.bot = bot
        self.nick = nick
        self.channel = channel

    def respond(self, message):
        self.bot.respond(message, channel=self.channel, nick=self.nick)


class Adapter(thebot.Adapter):
    @staticmethod
    def get_options(parser):
        group = parser.add_argument_group('IRC options')
        group.add_argument(
            '--irc-host', default='irc.freenode.net',
            help='Server to connect. Default: irc.freenode.net.'
        )
        group.add_argument(
            '--irc-port', default=6667,
            help='Port to connect. Default: 6667.'
        )
        group.add_argument(
            '--irc-channels', default='thebot',
            help='Comma-separated list of channels. Default: thebot.',
        )
        group.add_argument(
            '--irc-nick', default='thebot',
            help='IRC nick. Default: thebot.',
        )


    def on_line(self, nick, message, channel):
        request = IRCRequest(message, self.bot, nick, channel)
        return self.callback(request)

    def start(self):
        thread = threading.Thread(target=self.run_bot)
        thread.daemon = True
        thread.start()

    def run_bot(self):
        """
        Convenience function to start a bot on the given network, optionally joining
        some channels
        """
        host = self.args.irc_host
        port = self.args.irc_port
        nick = self.args.irc_nick
        channels = self.args.irc_channels.split(',')

        conn = irc.IRCConnection(host, port, nick)

        on_line = self.on_line
        class IRCBot(irc.IRCBot):
            def command_patterns(self):
                return (
                    self.ping('^.*', on_line),
                )

        self.bot = IRCBot(conn)
        #TODO refactor
        self.bot.on_line = self.on_line

        while 1:
            conn.connect()
            channels = channels or []
            for channel in channels:
                conn.join(channel)
            conn.enter_event_loop()



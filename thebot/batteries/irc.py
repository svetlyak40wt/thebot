from __future__ import absolute_import

import irc
import logging
import thebot
import threading


class IRCRequest(thebot.Request):
    def __init__(self, message, bot, nick, channel):
        super(IRCRequest, self).__init__(message)
        self.irc_bot = bot
        self.nick = nick
        self.channel = channel

    def respond(self, message):
        for line in message.split('\n'):
            self.irc_bot.respond(line, channel=self.channel, nick=self.nick)


class IRCConnection(irc.IRCConnection):
    def get_logger(self, logger_name, filename):
        """We override this method because don't want to have a separate log for irc messages.
        """
        return logging.getLogger(logger_name)


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


    def start(self):
        thread = threading.Thread(target=self.run_bot)
        thread.daemon = True
        thread.start()

    def run_bot(self):
        """
        Convenience function to start a bot on the given network, optionally joining
        some channels
        """
        host = self.bot.config.irc_host
        port = self.bot.config.irc_port
        nick = self.bot.config.irc_nick
        channels = self.bot.config.irc_channels.split(',')

        conn = IRCConnection(host, port, nick)

        def on_message(nick, message, channel):
            """A callback to be called by irckit's bot when new message will arrive.

            In it's turn, it will call TheBot's callback, to pass
            request into it.
            """
            request = IRCRequest(message, self.irc_bot, nick, channel)
            return self.callback(request)

        class IRCBot(irc.IRCBot):
            def command_patterns(self):
                return (
                    self.ping('^.*', on_message),
                )

        self.irc_bot = IRCBot(conn)

        while 1:
            conn.connect()
            channels = channels or []
            for channel in channels:
                conn.join(channel)
            conn.enter_event_loop()



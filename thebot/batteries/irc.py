from __future__ import absolute_import

import re
import irc
import logging
import thebot
import threading


class IRCRequest(thebot.Request):
    def __init__(self, message, bot, nick, channel):
        super(IRCRequest, self).__init__(message)
        self.bot = bot
        self.nick = nick
        self.channel = channel

    def get_user(self):
        return (self.channel, self.nick)

    def respond(self, message):
        message = thebot.utils.force_str(message)
        adapter = self.bot.get_adapter('irc')
        irc_connection = adapter.irc_connection

        for line in message.split('\n'):
            irc_connection.respond(line, channel=self.channel, nick=self.nick)


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

        def on_message(nick, message, channel):
            """A callback to be called by irckit when new message will arrive.

            It verifies if a bot's nick is mentioned, and pass data to TheBot.
            """
            message = thebot.utils.force_unicode(message)
            nick_re = re.compile(u'^%s[:,\s]\s*' % conn.nick)

            if nick_re.match(message) is not None:
                message = nick_re.sub(u'', message)
                request = IRCRequest(message, self.bot, nick, channel)
                return self.callback(request)

        conn = IRCConnection(host, port, nick)
        conn.register_callbacks((
            (re.compile(u'.*'), on_message),
        ))

        self.irc_connection = conn

        while 1:
            conn.connect()
            channels = channels or []
            for channel in channels:
                conn.join(channel)
            conn.enter_event_loop()



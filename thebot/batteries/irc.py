from __future__ import absolute_import, unicode_literals

import re
import irc
import logging
import time
import thebot
import threading


class IRCRequest(thebot.Request):
    def __init__(self, message, bot, nick, channel, direct):
        super(IRCRequest, self).__init__(message)
        self.bot = bot
        self.nick = nick
        self.channel = channel
        self.direct = direct

    def get_user(self):
        return (self.channel, self.nick)

    def respond(self, message):
        self._post(message, self.direct)

    def shout(self, message):
        self._post(message, False)

    def _post(self, message, respond_directly=True):
        logger = logging.getLogger('adapter.irc.request')
        adapter = self.bot.get_adapter('irc')
        irc_connection = adapter.irc_connection

        sleep_time = 0.05
        max_sleep_time = 1

        for line in message.split('\n'):
            if respond_directly:
                line = self.nick + ': ' + line

            logger.debug('Sending "{}" to {} at {}'.format(
                line, self.nick, self.channel
            ))
            irc_connection.respond(thebot.utils.force_str(line), channel=self.channel, nick=self.nick)

            # this is a protection from the flood
            # if we'll send to often, then server may decide to
            # logout us
            time.sleep(min(sleep_time, max_sleep_time))
            sleep_time *= 2


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
            logging.getLogger('adapter.irc').debug(
                'Received message "{}" from {} at channel {}.'.format(
                    message, nick, channel
                )
            )
            message = thebot.utils.force_unicode(message)
            nick_re = re.compile('^%s[:,\s]\s*' % conn.nick)

            direct = nick_re.match(message) is not None
            message = nick_re.sub('', message)

            request = IRCRequest(message, self.bot, nick, channel, direct)
            return self.callback(request, direct=direct)

        conn = IRCConnection(host, port, nick)
        conn.register_callbacks((
            (re.compile('.*'), on_message),
        ))

        self.irc_connection = conn

        while 1:
            conn.connect()
            channels = channels or []
            for channel in channels:
                conn.join(channel)
            conn.enter_event_loop()



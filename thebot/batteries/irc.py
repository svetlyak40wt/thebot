from __future__ import absolute_import, unicode_literals

import re
import irc
import logging
import time
import thebot
import threading

from collections import defaultdict
from functools import wraps


class IRCConnection(irc.IRCConnection):
    def __init__(self, *args, **kwargs):
        super(IRCConnection, self).__init__(*args, **kwargs)
        # a map nick -> list of events
        # to signal about received online status
        self._ison_requests = defaultdict(list)
        # a map nick -> True/False
        # if True, then this nick is online
        self._online_statuses = {}

    def get_logger(self, logger_name, filename):
        """We override this method because don't want to have a separate log for irc messages.
        """
        return logging.getLogger(logger_name)

    def dispatch_patterns(self):
        callbacks = list(super(IRCConnection, self).dispatch_patterns())
        callbacks.append(
            (re.compile(':(?:.*?)\s+303(?:.*?):(?P<nicks>.*)'), self.on_ison_response)
        )
        def threaded_callback(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                thread = threading.Thread(target=func, args=args, kwargs=kwargs)
                thread.daemon = True
                thread.start()
            return wrapper

        callbacks = tuple(
            (pattern, threaded_callback(callback))
            for pattern, callback
                in callbacks
        )
        return callbacks

    def is_online(self, nick):
        """This method sends ISON request and waits for response."""
        event = threading.Event()
        self._ison_requests[nick].append(event)
        self._online_statuses[nick] = False

        self.send('ISON {}'.format(nick))
        event.wait(timeout=3)
        return self._online_statuses[nick]

    def on_ison_response(self, nicks):
        logger = logging.getLogger('thebot.adapter.irc')
        logger.debug('These nicks are online: ' + nicks)

        for nick in nicks.split(' '):
            self._online_statuses[nick] = True
            for event in self._ison_requests[nick]:
                event.set()


class Adapter(thebot.Adapter):
    @staticmethod
    def get_options(parser):
        group = parser.add_argument_group('IRC options')
        group.add_argument(
            '--irc-host', default='irc.freenode.net',
            help='Server to connect. Default: irc.freenode.net.'
        )
        group.add_argument(
            '--irc-port', default=6667, type=int,
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

            request = thebot.Request(
                self,
                message,
                thebot.User(nick),
                thebot.Room(channel) if channel else None,
                refer_by_name=direct
            )
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

    def send(self, message, user=None, room=None, refer_by_name=False):
        logger = logging.getLogger('thebot.adapter.irc')

        sleep_time = 0.05
        max_sleep_time = 1

        for line in message.split('\n'):
            if refer_by_name:
                line = user.id + ', ' + line

            logger.debug('Sending "{}" to {} at {}'.format(
                line,
                'everybody' if user is None else user,
                'private channel' if room is None else room,
            ))
            self.irc_connection.respond(
                thebot.utils.force_str(line),
                nick=user.id if user else None,
                channel=room.id if room else None,
            )

            # this is a protection from the flood
            # if we'll send to often, then server may decide to
            # logout us
            time.sleep(min(sleep_time, max_sleep_time))
            sleep_time *= 2

    def is_online(self, user):
        return self.irc_connection.is_online(user.id)


# coding: utf-8
from __future__ import absolute_import, unicode_literals

import sleekxmpp
import thebot
import threading


class User(thebot.User):
    def __init__(self, jid):
        self.id, self.resource = jid.split('/')


class Adapter(thebot.Adapter):
    ignore_jids = [
        'lastmail.ya.ru/Яндекс.Информер',
    ]
    @staticmethod
    def get_options(parser):
        group = parser.add_argument_group('XMPP options')
        group.add_argument(
            '--xmpp-jid', default='thebot@ya.ru',
            help='Jabber JID. Default: thebot@ya.ru.'
        )
        group.add_argument(
            '--xmpp-server', default='',
            help='Jabber server. Optional.'
        )
        group.add_argument(
            '--xmpp-password', default='',
            help='Password to connect to the server. Default: "".'
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

        jid = self.bot.config.xmpp_jid
        password = self.bot.config.xmpp_password

        def on_message(msg):
            """A callback to be called by xmpppy's when new message will arrive.

            In it's turn, it will call TheBot's callback, to pass request into it.
            """

            if msg['type'] in ('chat', 'normal'):
                if msg['from'] != msg['to'] and msg['from'] not in self.ignore_jids:
                    request = thebot.Request(
                        self,
                        msg['body'],
                        user=User(unicode(msg['from']))
                    )
                    self.callback(request)


        def on_start(event):
            self.xmpp_bot.get_roster()
            self.xmpp_bot.send_presence()


        self.xmpp_bot = sleekxmpp.ClientXMPP(jid, password)
        self.xmpp_bot._use_daemons = True
        self.xmpp_bot.add_event_handler('session_start', on_start)
        self.xmpp_bot.add_event_handler('message', on_message)

        self.xmpp_bot.connect()
        self.xmpp_bot.process(block=True)

    def send(self, message, user=None, room=None, refer_by_name=False):
        msg = sleekxmpp.stanza.message.Message()
        msg['to'] = user.id + '/' + user.resource
        msg['type'] = 'chat'
        msg['body'] = message

        self.xmpp_bot.send(msg)

    def is_online(self, user):
        return len(self.xmpp_bot.client_roster.presence(user.id)) > 0


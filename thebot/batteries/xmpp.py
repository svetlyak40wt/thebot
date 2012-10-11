from __future__ import absolute_import

import copy
import sleekxmpp
import thebot
import threading


class XMPPRequest(thebot.Request):
    def __init__(self, message, bot, _from):
        super(XMPPRequest, self).__init__(message)
        self.bot = bot
        self._from = _from

    def get_user(self):
        return self._from

    def respond(self, message):
        msg = sleekxmpp.stanza.message.Message()
        msg['to'] = self._from
        msg['type'] = 'chat'
        msg['body'] = message

        adapter = self.bot.get_adapter('xmpp')
        adapter.xmpp_bot.send(msg)


class Adapter(thebot.Adapter):
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
            help='Password to connect to the server. Default: ''.'
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
                if msg['from'] != msg['to']:
                    request = XMPPRequest(msg['body'], self.bot, unicode(msg['from']))
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



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
        host = 'irc.freenode.net'
        port = 6667
        nick = 'thebot'
        channels = ['svetlyak']
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



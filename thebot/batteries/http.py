from __future__ import absolute_import, unicode_literals

import irc
import logging
import thebot
import threading

from wsgiref.simple_server import make_server, WSGIRequestHandler


class HttpRequest(thebot.Request):
    def __init__(self, environ, start_response):
        super(HttpRequest, self).__init__(environ['PATH_INFO'])
        self.environ = environ
        self.start_response = start_response
        self.response_sent = False

    def respond(self, message):
        if self.response_sent:
            raise RuntimeError('Response to this HTTP request already sent.')

        status = '200 OK'
        headers = [
            ('Server', 'TheBot/' + thebot.__version__),
            ('Content-type', 'text/plain; charset=utf-8'),
        ]

        write = self.start_response(status, headers)
        write(message)
        self.response_sent = True


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
            '--http-host', default='127.0.0.1',
            help='IP to bind to. Default: 127.0.0.1.'
        )
        group.add_argument(
            '--http-port', default=8888,
            help='TCP port to bind to. Default: 8888.'
        )


    def start(self):
        class QuietHandler(WSGIRequestHandler):
            def __init__(self, *args, **kwargs):
                self.logger = logging.getLogger('thebot.batteries.http')
                WSGIRequestHandler.__init__(self, *args, **kwargs)

            def log_message(self, format, *args):
                self.logger.info(
                    '%s - - [%s] %s',
                    self.address_string(),
                    self.log_date_time_string(),
                    format % args
                )

        server = make_server(
            self.bot.config.http_host,
            int(self.bot.config.http_port),
            self._wsgi_handler,
            handler_class=QuietHandler,
        )

        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

    def _wsgi_handler(self, environ, start_response):
        request = HttpRequest(environ, start_response)
        self.callback(request)
        if not request.response_sent:
            request.respond('')
        return []


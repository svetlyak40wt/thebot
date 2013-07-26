from __future__ import absolute_import, unicode_literals

import irc
import logging
import threading

from wsgiref.simple_server import make_server, WSGIRequestHandler
from .. import Request, Adapter, User, __version__
from ..utils import force_str
from cgi import parse_qs

class HttpRequest(Request):
    def __init__(self, adapter, environ, start_response):
        super(HttpRequest, self).__init__(adapter, environ['PATH_INFO'], user=User('http service'))
        self.environ = environ
        self.start_response = start_response
        self.response_sent = False
        self.method = environ['REQUEST_METHOD']

        self.GET = parse_qs(environ['QUERY_STRING'])

        if self.method == 'POST':
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(content_length)
            self.POST = parse_qs(request_body)
        else:
            self.POST = None

    def respond(self, message):
        if self.response_sent:
            raise RuntimeError('Response to this HTTP request already sent.')

        status = b'200 OK'
        headers = [
            (b'Server', b'TheBot/' + force_str(__version__)),
            (b'Content-type', b'text/plain; charset=utf-8'),
        ]

        write = self.start_response(status, headers)
        write(force_str(message))
        self.response_sent = True


class Adapter(Adapter):
    @staticmethod
    def get_options(parser):
        group = parser.add_argument_group('HTTP options')
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
        request = HttpRequest(self, environ, start_response)
        self.callback(request)
        if not request.response_sent:
            request.respond('')
        return []


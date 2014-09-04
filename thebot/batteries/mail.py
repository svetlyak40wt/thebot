from __future__ import absolute_import, unicode_literals, print_function

import email
import email.message
import imaplib
import smtplib
import logging
import time
import thebot
import threading

#from email.mime.text import MIMEText


class Request(thebot.Request):
    def __init__(self, adapter, message, from_email, message_id, subject):
        super(Request, self).__init__(adapter, message, user=thebot.User(from_email))
        self.message_id = message_id
        self.subject = subject

    def respond(self, message):
        subject = self.subject

        # if there wasn't any message, then probably this request
        # was created just to notify somebody on some event
        if self.message and not subject.lower().startswith('re: '):
            subject = 'Re: ' + subject

        citate = ''
        if self.message:
            citate = '> {}\n'.format(self.message)
            
        self.adapter.send(
            citate + message,
            self.user,
            subject=subject,
            in_reply_to=self.message_id,
        )

    def shout(self, message):
        self.respond(message)


def _get_text_from_email(message):

    def _get_text(message):
        if message.is_multipart():
            for part in message.get_payload():
                text = _get_text(part)
                if text is not None:
                    return text
        else:
            mimetype = message.get_content_type()
            if mimetype == 'text/plain':
                payload = message.get_payload()
                charset = message.get_content_charset()
                if charset is not None:
                    payload = payload.decode(charset, 'replace')
                return payload

    return _get_text(message)


class Imap(object):
    def __init__(self, host, port, username, password):
        self.logger = logging.getLogger('thebot.batteries.mail.imap')
        if port == 143:
            self._imap = imaplib.IMAP4(host, port)
        else:
            self._imap = imaplib.IMAP4_SSL(host, port)
        self.username = username
        self.password = password

    def __enter__(self):
        status, messages = self._imap.login(self.username, self.password)
        if status != 'OK':
            raise RuntimeError(''.join(messages))

        status, messages = self._imap.select()
        if status != 'OK':
            raise RuntimeError(' '.join(messages))

        return self

    def __exit__(self, *args):
        self._imap.logout()

    def fetch_messages(self):
        status, data = self._imap.uid('search', None, 'ALL')
        uids = data[0].split() if data[0] is not None else []

        for uid in uids:
            self.logger.debug('fetching message with uid {}'.format(uid))
            status, data = self._imap.uid('fetch', uid, '(RFC822)')
            message = email.message_from_string(data[0][1])
            message.uid = uid
            yield message

    def delete(self, message):
        self.logger.debug('deleting message with uid {}'.format(message.uid))
        self._imap.uid('store', message.uid, '+FLAGS', '\\Deleted')
        self._imap.expunge()


class Adapter(thebot.Adapter):
    @staticmethod
    def get_options(parser):
        group = parser.add_argument_group('SMTP options')
        group.add_argument(
            '--smtp-host', default='localhost',
            help='SMTP server to connect. Default: localhost.'
        )
        group.add_argument(
            '--smtp-port', default=25,
            help='SMTP port to connect. Default: 25.'
        )
        group.add_argument(
            '--smtp-username',
            help='Username to connect to SMTP server.'
        )
        group.add_argument(
            '--smtp-password',
            help='Password to connect to SMTP server.'
        )
        group.add_argument(
            '--smtp-from',
            help='An email to use in From: header.'
        )

        group = parser.add_argument_group('IMAP options')
        group.add_argument(
            '--imap-host', default='localhost',
            help='IMAP server to connect. Default: localhost.'
        )
        group.add_argument(
            '--imap-port', default=143,
            help='IMAP port to connect. Default: 143.'
        )
        group.add_argument(
            '--imap-username',
            help='Username to connect to IMAP server.'
        )
        group.add_argument(
            '--imap-password',
            help='Password to connect to IMAP server.'
        )


    def start(self):
        thread = threading.Thread(target=self._fetch_messages)
        thread.daemon = True
        thread.start()

    def get_imap(self):
        cfg = self.bot.config
        return Imap(cfg.imap_host, int(cfg.imap_port), cfg.imap_username, cfg.imap_password)

    def create_request(self,
                       message=None,
                       email=None,
                       message_id=None,
                       subject=None):
        return Request(self, message, email, message_id, subject)

    def _fetch_messages(self):
        logger = logging.getLogger('thebot.batteries.mail')

        while True:
            with self.get_imap() as imap:
                for message in imap.fetch_messages():
                    try:
                        from_ = email.Header.decode_header(message['from'])
                        full_from = (value.decode(charset or 'ascii') for value, charset in from_)
                        full_from = ' '.join(full_from)
                        from_email = [value for value, charset in from_ if charset is None and '@' in value][0]

                        text = _get_text_from_email(message)
                        if text is None:
                            logger.warning('Message from {} contains no plain/text part.'.format(full_from))
                        else:
                            # selecting first non empty line
                            lines = text.split('\n')
                            lines = (line.strip() for line in lines)
                            lines = list(filter(None, lines))
                            first_line = lines[0]
                            request = self.create_request(
                                message=first_line,
                                email=from_email,
                                message_id=message['Message-Id'],
                                subject=message['Subject'],
                            )
                            self.callback(request, direct=True)

                            imap.delete(message)
                    except Exception:
                        logger.exception('processing message')

                time.sleep(5)

    def send(self, message, user, subject='Message from TheBot', in_reply_to=None):
        to_email = user.id

        logger = logging.getLogger('thebot.batteries.mail')
        logger.debug('Sending email to "{}" in reply to "{}"'.format(to_email, in_reply_to))

        cfg = self.bot.config

        port = int(cfg.smtp_port)
        if port == 25:
            server = smtplib.SMTP(cfg.smtp_host, port)
        else:
            server = smtplib.SMTP_SSL(cfg.smtp_host, port)

        server.login(cfg.smtp_username, cfg.smtp_password)
        #server.set_debuglevel(1)

        from_email = getattr(cfg, 'smtp_from', None)
        if from_email is None and '@' in cfg.smtp_username:
            from_email = cfg.smtp_username
        else:
            raise RuntimeError('Please, specify "--smtp-from" option.')

        response = email.message.Message()
        response['From'] = 'dev.thebot@ya.ru'
        response['To'] = to_email
        response['Subject'] = subject
        if in_reply_to:
            response['In-Reply-To'] = in_reply_to
        response.set_payload(message.encode('utf8'), 'utf-8')

        server.sendmail(from_email, to_email, response.as_string())
        server.quit()

    def close(self):
        self.imap.close()
        self.imap.logout()



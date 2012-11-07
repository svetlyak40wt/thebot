from __future__ import absolute_import, unicode_literals

import sys
import threading
import thebot


class Adapter(thebot.Adapter):
    def start(self):
        def loop():
            while True:
                sys.stdout.write('> ')
                sys.stdout.flush()
                line = sys.stdin.readline()
                if len(line) == 0:
                    # seems, Ctrl-D was pressed
                    self.callback(thebot.EXIT)
                    return

                line = line.strip()

                request = thebot.Request(
                    self,
                    line,
                    thebot.User('console'),
                )
                self.callback(request)

        thread = threading.Thread(target=loop)
        thread.daemon = True
        thread.start()

    def send(self, message, user=None, room=None, refer_by_name=False):
        sys.stdout.write('{0}\n'.format(message))
        sys.stdout.flush()

    def is_online(self, user):
        return True

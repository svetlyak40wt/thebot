from __future__ import absolute_import, unicode_literals

import sys
import threading
import thebot


class ConsoleRequest(thebot.Request):
    def respond(self, message):
        sys.stdout.write('{0}\n'.format(message))
        sys.stdout.flush()

    def get_user(self):
        return 'local'


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

                self.callback(ConsoleRequest(line))

        thread = threading.Thread(target=loop)
        thread.daemon = True
        thread.start()




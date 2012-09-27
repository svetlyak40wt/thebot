#!/usr/bin/env python
# coding: utf-8

import thebot

from time import sleep

def main():
    #bot = Bot([IRCAdapter], [ImagePlugin])
    bot = thebot.Bot(['console'], ['image'])
    try:
        while not bot.exiting:
            sleep(1)
    except KeyboardInterrupt:
        pass
    bot.close()


if __name__ == '__main__':
    main()


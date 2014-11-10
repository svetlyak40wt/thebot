The Bot
=======

This is a general purpose chat bot, extensible in varios ways.
The reason, why it was written is because NodeJS and CoffeeScript are sucks and
Hubot uses them.

The Bot is written in orthodox Python and can be installed via [pip][].
It's functionality can be extended by installation of additional python packages,
you don't have to clone a repository and hack some code there.

Badges
------

[![](https://secure.travis-ci.org/svetlyak40wt/thebot.png)](http://travis-ci.org/svetlyak40wt/thebot)
[![](http://allmychanges.com/p/python/thebot/badge)](http://allmychanges.com/p/python/thebot/)

Installation
------------

    virtualenv env
    source env/bin/activate
    pip install 'git+git://github.com/svetlyak40wt/thebot.git'
    thebot

To connect TheBot to the IRC channel do:

    thebot --adapter irc --irc-host irc.freenode.net --irc-channels somechannel --irc-nick thebot

To turn on more useful plugins, install them via pip. For example, to install Instagram and Github plugins, do:

    pip install 'git+git://github.com/svetlyak40wt/thebot-github.git'
    pip install 'git+git://github.com/svetlyak40wt/thebot-instagram.git'
    thebot --adapter irc --plugins instagram --irc-host irc.freenode.net --irc-channels somechannel --irc-nick thebot

Then, join this channel and send `thebot, instagram on` message. To list all supported command, issue the message
`thebot, help`.


Available adapters
------------------

### Builtins

* [irc](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/irc.py);
* [xmpp](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/xmpp.py);
* [http](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/http.py);
* [console](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/console.py);
* [mail](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/mail.py);

### External

* Be the first, who will write the one!

Available plugins
-----------------

### Builtins

* [image](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/image.py) — uses Google Image and [mustachify.me](http://mustachify.me), to search images and to make them funny.
* [math](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/math.py) — uses Google Calculator to do some math and convert currencies.
* [todo](https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/todo.py) — a simple task manager which will store your tasks and send you reminders.

### External

* [github](https://github.com/svetlyak40wt/thebot-github) — allows to track new issues, pull requests and comments.
* [instagram](https://github.com/svetlyak40wt/thebot-instagram) — posts new popular images from Instagram.
* [translate](https://github.com/svetlyak40wt/thebot-translate) — translates texts from one language to another.
* [pomodoro](https://github.com/svetlyak40wt/thebot-pomodoro) — powerful [pomodoro timer](http://pomodorotechnique.com/) to boost your productivity.
* [draftin](https://github.com/svetlyak40wt/thebot-draftin) — accepts callbacks from draftin.com and runs a shell command to publish post into the static generated blog.
* [webhooks](https://github.com/svetlyak40wt/thebot-webhooks) — configurable webhooks, to run any number of commands on HTTP POST or GET requests.
* Add yours plugins to this list!


Alternatives
------------

There are some bots written in Python, but all of them sucks, because,
most of the works only with IRC and none of them has such beautiful
architecture as The Bot.

But if you still have some doubts, here is a list of some bots. Go, try
them and come back to ask The Bot to forgive you treason.

* http://gozerbot.org/ and his son https://code.google.com/p/jsonbot/
* http://pypi.python.org/pypi/supybot/
* https://github.com/brunobord/cmdbot/
* http://inamidst.com/phenny/ and a Python3 version https://github.com/sbp/duxlot/
* https://github.com/toastdriven/toastbot uses irckit и gevent
* https://github.com/gbin/err too complex and over-engeneered architecture, but has plugins.

TODO
----

* Implement method `create_request` in `irc` and `xmpp` adapters, to be able to use
  them as a notification channel in the `thebot-webooks` plugin.

[pip]: http://pypi.python.org/pypi/pip

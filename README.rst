The Bot
=======

This is a general purpose chat bot, extensible in varios ways.
The reason, why it was written is because NodeJS and CoffeeScript are sucks and
Hubot uses them.

The Bot is written in orthodox Python and can be installed via `pip`.
It's functionality can be extended by installation of additional python packages,
you don't have to clone a repository and hack some code there.

Build Status
------------

| This project uses Travis for continuous integration:
| |travis|_

Installation
------------

.. code:: bash

    virtualenv env
    source env/bin/activate
    pip install 'git+git://github.com/svetlyak40wt/thebot.git'
    thebot

To connect TheBot to the IRC channel do:

.. code:: bash

    thebot --adapter irc --irc-host irc.freenode.net --irc-channels somechannel --irc-nick thebot

To turn on more useful plugins, install them via pip. For example, to install Instagram and Github plugins, do:

.. code:: bash

    pip install 'git+git://github.com/svetlyak40wt/thebot-github.git'
    pip install 'git+git://github.com/svetlyak40wt/thebot-instagram.git'
    thebot --adapter irc --plugins instagram --irc-host irc.freenode.net --irc-channels somechannel --irc-nick thebot

Then, join this channel and send `thebot, instagram on` message. To list all supported command, issue the message
`thebot, help`.


Available adapters
------------------

Builtins
^^^^^^^^

* `irc <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/irc.py>`_;
* `xmpp <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/xmpp.py>`_;
* `http <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/http.py>`_;
* `console <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/console.py>`_;
* `mail <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/mail.py>`_;

External
^^^^^^^^

* Be the first, who will write the one!

Available plugins
-----------------

Builtins
^^^^^^^^

* `image <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/image.py>`_ — uses Google Image and `mustachify.me <http://mustachify.me>`_, to search images and to make them funny.
* `math <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/math.py>`_ — uses Google Calculator to do some math and convert currencies.
* `todo <https://github.com/svetlyak40wt/thebot/blob/master/thebot/batteries/todo.py>`_ — a simple task manager which will store your tasks and send you reminders.

External
^^^^^^^^

* `github <https://github.com/svetlyak40wt/thebot-github>`_ — allows to track new issues, pull requests and comments.
* `instagram <https://github.com/svetlyak40wt/thebot-instagram>`_ — posts new popular images from Instagram.
* `translate <https://github.com/svetlyak40wt/thebot-translate>`_ — translates texts from one language to another.
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

.. _pip: http://pypi.python.org/pypi/pip
.. |travis| image:: https://secure.travis-ci.org/svetlyak40wt/thebot.png
.. _travis: http://travis-ci.org/svetlyak40wt/thebot


The Bot
=======

This is a general purpose chat bot, extensible in varios ways.
The reason, why it was written is because NodeJS and CoffeeScript are sucks and
Hubot uses them.

The Bot is written in orthodox Python and can be installed via `pip`_.
It's functionality can be extended by installation of additional python packages,
you don't have to clone a repository and hack some code there.

Badges
------

.. image:: https://secure.travis-ci.org/svetlyak40wt/thebot.png
   :target: http://travis-ci.org/svetlyak40wt/thebot

.. image:: http://allmychanges.com/u/svetlyak40wt/python/thebot/badge
   :target: http://allmychanges.com/u/svetlyak40wt/python/thebot/

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

Then, join this channel and send ``thebot, instagram on`` message. To list all supported command, issue the message
``thebot, help``.


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
* `pomodoro <https://github.com/svetlyak40wt/thebot-pomodoro>`_ — powerful `pomodoro timer <http://pomodorotechnique.com/>`_ to boost your productivity.
* `draftin <https://github.com/svetlyak40wt/thebot-draftin>`_ — accepts callbacks from draftin.com and runs a shell command to publish post into the static generated blog.
* `webhooks <https://github.com/svetlyak40wt/thebot-webhooks>`_ — configurable webhooks, to run any number of commands on HTTP POST or GET requests.
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

* Implement method ``create_request`` in ``irc`` and ``xmpp`` adapters, to be able to use
  them as a notification channel in the ``thebot-webooks`` plugin.

.. _pip: http://pypi.python.org/pypi/pip


0.4.0
-----

* Added new command line option `--pid-filename`. The bot will
  write pid of the main worker's process. This allows to shut it down
  gracefully when bot was started by a process manager like circusd.

0.3.3
-----

* Fixed missing import in http adapter.

0.3.2
-----

* Http adapter was fixed to use newer Request.

0.3.1
-----

* Bot was fixed to run on Python3.

0.3.0
-----

This release makes TheBot more usable, as it introduces a new
system to tie user's data not to their accounts in separate
instant messengers, but to a unique ids.

It is recommended to use new plugin 'identity', to retrive user's
id by request, and to tie all data to this id.

Another great feature, is ability to send a notification to first
adapter where user concidered as "online". Each plugin now can
implement method 'is_online', which used by 'notify' plugin.

And finally, 'settings' plugin was added, to create a single
storage for user's preferences.

See 'todo' plugin as example, it uses all these three new plugins
to handle it's job.

### Major changes

* Added recursive dependency handling for plugins and adapters.
* Working is_online methods for irc and xmpp plugins.
* Three new plugins were added 'identity', 'settings' and 'notify'.
* Now plugin 'todo' work with identity to store data and notifies user via 'notify' pluging.
* Added a new adapter 'mail' to talk with TheBot via email.

### Minor changes

* Help system was refactored and now shows each plugin's docstring as it's documentation.
* Now each plugin has it's own self.logger.
* Fixed issue with missing adapter, when restoring state from the database.
* Builtin autoreloader was replaced with external 'server-reloader' module.

### Small fixes

* Fixed issue when bot does not saved db state to disk on code reload and Ctrl-C.
* Added option --reload-on-changes to watch on code changes, without it, server does not reload itself.
* Tests were fixed to close storage.
* JID of lastmail.ya.ru bot was added to ignore list.

0.2.1
-----

* Don't who unnecessary line 'And react on following patterns:' if there is now such patterns.

0.2.0
-----

### Features

* No more 'route' decorator. Use 'on_command' and 'on_pattern' instead (backward incompatible).
* Now plugin can 'respond' directly to the user or 'shout' to all channel/room members.
* Added ability to reply to 'directs' in IRC. And flood protection.
* Added autoreload on source change.

### Fixes

* Storage was fixed to support deep nesting and dict like interface.
* Added get_user method in Console adapter.
* Fixed issue with UserDict, missing in Python3.
* Fixed error in 'todo' plugin, releated to tasks, missing in a storage.
* Removed six.u function. It was replaced with future 'unicode_literals'.
* Fixed __iter__ method of the Storage.
* Now XMPP returns a JID without resource part as result of a get_user call.

0.1.3
-----

* Fixed the way, how config and command-line options are applied.

0.1.2
-----

* Now all options can be specified in YAML config 'thebot.conf'.

0.1.1
-----

* Port to Python3.

0.1.0
-----

Initial version with basic adapters and plugins.

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

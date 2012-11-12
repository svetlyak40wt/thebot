# coding: utf-8
from __future__ import absolute_import, unicode_literals

import types
import six

from bisect import insort
from thebot import Plugin


class Plugin(Plugin):
    """Allows other plugins to notify user via different adapters.

    This plugin has no it's own commands but you can control
    it's behaviour via notification-priorities settings, like that:

    set notification-priorities xmpp,irc,email
    """
    deps = ['settings']

    def notify(self, identity, message):
        identity_plugin = self.bot.get_plugin('identity')
        settings_plugin = self.bot.get_plugin('settings')

        if isinstance(identity, six.string_types):
            identity = identity_plugin.get_identity_by_id(identity)

        priorities = settings_plugin.get(identity.id, 'notification-priorities', '')
        priorities = enumerate(item.strip() for item in priorities.split(','))
        priorities = dict((key, value) for value, key in priorities)
        # now priorities is a map from adapter's name to a number

        # there we'll store sorted by priority
        online_contacts = []

        for default_priority, contact in enumerate(identity.persons, 1000):
            # we need increasing default_priority, to keep order of
            # contacts without preferences

            if contact.adapter.is_online(contact.user):
                insort(
                    online_contacts,
                    (
                        priorities.get(contact.adapter.name, default_priority),
                        contact
                    )
                )

        if online_contacts:
            contact = online_contacts[0][1]
            contact.adapter.send(message, contact.user)
            return True

        return False


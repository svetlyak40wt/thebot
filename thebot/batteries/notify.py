# coding: utf-8
from __future__ import absolute_import, unicode_literals

from bisect import insort
from thebot import Plugin


class Plugin(Plugin):
    def notify(self, identity_id, message):
        identity_plugin = self.bot.get_plugin('identity')
        settings_plugin = self.bot.get_plugin('settings')
        identity = identity_plugin.get_identity_by_id(identity_id)

        priorities = settings_plugin.get(identity.id, 'notification-priorities', '')
        priorities = enumerate(item.strip() for item in priorities.split(','))
        priorities = dict((key, value) for value, key in priorities)
        # now priorities is a map from adapter's name to a number

        # there we'll store sorted by priority
        online_contacts = []

        for contact in identity.persons:
            if contact.adapter.is_online(contact.user):
                insort(
                    online_contacts,
                    (
                        priorities.get(contact.adapter.name, 1000),
                        contact
                    )
                )

        if online_contacts:
            contact = online_contacts[0][1]
            contact.adapter.send(message, contact.user)
            return True

        return False


# coding: utf-8
from __future__ import absolute_import, unicode_literals

from thebot import Plugin, on_command


class Plugin(Plugin):
    """Stores user settings."""
    deps = ['identity']

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.user_settings = self.storage.with_prefix('user:')

    @on_command('set (?P<key>[a-z][a-z-]*) (?P<value>.*)')
    def on_set(self, request, key, value):
        """Set a key to a given value."""
        identity_plugin = self.bot.get_plugin('identity')
        identity = identity_plugin.get_identity_by_user(request.adapter, request.user)
        self.set(identity.id, key, value)

    @on_command('get (?P<key>[a-z][a-z-]*)')
    def on_get(self, request, key):
        """Get setting with a given key."""
        identity_plugin = self.bot.get_plugin('identity')
        identity = identity_plugin.get_identity_by_user(request.adapter, request.user)
        try:
            request.respond('{} = {}'.format(
                key,
                self.get(identity.id, key)
            ))
        except KeyError:
            request.respond('Settings {} not found'.format(key))

    @on_command('my settings')
    def my_settings(self, request):
        """Show all settings."""
        identity_plugin = self.bot.get_plugin('identity')
        identity = identity_plugin.get_identity_by_user(request.adapter, request.user)
        user_settings = self.user_settings.with_prefix('{}:'.format(identity.id))

        lines = []
        for key, value in user_settings.items():
            lines.append('{} = {}'.format(key, value))

        if lines:
            lines.insert(0, 'You settings are:')
        else:
            lines.append('You have no any settings yet.')

        request.respond('\n'.join(lines))

    def get(self, identity_id, key, default=None):
        return self.user_settings.get('{}:{}'.format(identity_id, key), default)

    def set(self, identity_id, key, value):
        self.user_settings['{}:{}'.format(identity_id, key)] = value


# coding: utf-8
from __future__ import absolute_import, unicode_literals

import hashlib
import time
import random

from thebot import Plugin, on_command
from thebot.utils import printable


@printable
class Person(object):
    def __init__(self, adapter, user):
        self.adapter = adapter
        self.user = user

    def __unicode__(self):
        return '{} ({})'.format(self.user, self.adapter)

    def __eq__(self, another):
        return self.adapter == another.adapter and self.user == another.user


class Identity(object):
    def __init__(self, identity_id):
        self.id = identity_id
        self.persons = []


class Plugin(Plugin):
    """Allows to join several accounts from different chats.

    This plugin is used by other plugins, to retrive a user's UID.
    You can join several accounts from different adapters, and
    all of them will be binded to the same UID.

    That way, user's information can be accessible from different
    instant messengers.
    """
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.identities = {}
        self.persons = {} # a map from person to identity.id

        self.identity_storage = self.storage.with_prefix('i:')

        for identity in self.identity_storage.values():
            self._add_identity(identity, save_to_storage=False)

    @on_command('build identity')
    def build(self, request):
        """Extend you identity with another accounts."""
        identity = self.get_identity_by_user(request.adapter, request.user)

        request.respond(
            r'Ok, please, send me this command via other adapters: "bind to {}"'.format(identity.id)
        )

    def _add_identity(self, identity, save_to_storage=True):
        if save_to_storage:
            self.identity_storage[identity.id] = identity

        self.identities[identity.id] = identity
        for person in identity.persons:
            self.persons[(person.adapter.name, person.user.id)] = identity.id

    def _create_identity(self, adapter, user):
        identity = Identity(
            hashlib.sha1(
                (str(time.time()) + str(random.random())).encode('utf-8')
            ).hexdigest()
        )
        identity.persons.append(Person(adapter, user))
        self._add_identity(identity)

        self.logger.debug('Created identity {}'.format(identity.id))
        return identity

    @on_command('bind to (?P<identity_id>[0-9a-f]{40})')
    def bind(self, request, identity_id):
        """Bind current account to a given identity id. To use this command, execute 'build identity' from another account first."""
        to_identity = self.identities.get(identity_id, None)

        if to_identity is None:
            request.respond('Identity with id {} not found'.format(identity_id))
        else:
            from_identity = self.get_identity_by_request(request)

            if from_identity != to_identity:
                person = Person(request.adapter, request.user)
                self.logger.debug('Binding {} to identity {}'.format(person, to_identity.id))

                to_identity.persons.append(person)
                self._add_identity(to_identity)

                from_identity.persons.remove(person)
                if len(from_identity.persons) == 0:
                    del self.identity_storage[from_identity.id]
                    del self.identities[from_identity.id]
            request.respond('ok')

    @on_command('unbind')
    def unbind(self, request):
        """Unbind current account from the identity."""
        from_identity = self.get_identity_by_request(request)
        person = Person(request.adapter, request.user)

        self.logger.debug('Unbinding {} to identity {}'.format(person, from_identity.id))
        from_identity.persons.remove(person)

        if len(from_identity.persons) == 0:
            del self.identity_storage[from_identity.id]
            del self.identities[from_identity.id]

    @on_command('show my accounts')
    def show_my_ids(self, request):
        """Show all accounts, binded to a current identity."""
        identity = self.get_identity_by_request(request)
        if identity is not None:
            # TODO rename identitites to accounts
            request.respond(
                'Your identities are:\n' + '\n'.join(
                    '{}) {} ({}, {})'.format(
                        idx,
                        contact.user,
                        contact.adapter,
                        'online' if contact.adapter.is_online(contact.user) else 'offline'
                    )
                    for idx, contact in enumerate(identity.persons, 1)
                )
            )

    def get_identity_by_id(self, identity_id):
        return self.identities.get(identity_id)

    def get_identity_by_user(self, adapter, user):
        """Returns identity for user.

        If it does not exist, then identity will be created.
        """
        identity_id = self.persons.get((adapter.name, user.id), None)
        if identity_id is None:
            return self._create_identity(adapter, user)
        else:
            return self.identities.get(identity_id, None)

    def get_identity_by_request(self, request):
        return self.get_identity_by_user(request.adapter, request.user)


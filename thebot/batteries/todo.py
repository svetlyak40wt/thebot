# coding: utf-8
from __future__ import absolute_import, unicode_literals

import bisect
import times
import hashlib
import six

from dateutil.parser import parse
from thebot import ThreadedPlugin, on_command


def _gen_hashes(tasks):
    """Generates sha1 hashes for tasks and minumum subhash's
    length for which all generated hashes are unique.
    """
    if not tasks:
        return [], 0

    shas = [
        hashlib.sha1(about.encode('utf-8')).hexdigest()
        for dt, about, r in tasks
    ]
    for min_len in range(2, len(shas[0]) + 1):
        trimmed = set(h[:min_len] for h in shas)
        if len(trimmed) == len(shas):
            break
    return shas, min_len


class Plugin(ThreadedPlugin):
    """Allows to manage a simple todo list.

    By default, all dates are in the UTC.
    To use your local time everywhere, set timezone like that:

    set timezone Europe/Moscow
    """
    name = 'todo'
    deps = ['notify', 'identity', 'settings']

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)

        # interval between bot's attemts to find expired tasks
        self.interval = 60

        if not self.bot.config.unittest:
            self.start_worker(interval=self.interval)

    def _get_tasks(self, identity):
        return self.storage.get('tasks:{}'.format(identity.id), [])

    def _set_tasks(self, identity, tasks):
        self.storage['tasks:{}'.format(identity.id)] = tasks

    @on_command('remind( me)? at (?P<datetime>.+) to (?P<about>.+)')
    def remind(self, request, datetime, about):
        """Remind about a TODO at given time."""

        try:
            identity = self.bot.get_plugin('identity').get_identity_by_request(request)
            dt = parse(datetime)
            tz = self._get_user_timezone(identity)
            dt = times.to_universal(dt, tz)

            tasks = self._get_tasks(identity)
            bisect.insort(tasks, (dt, about, identity.id))
            self._set_tasks(identity, tasks)
        except Exception as e:
            request.respond('Unable to parse a date: ' + six.text_type(e))
            raise

        request.respond('ok')

    @on_command('my tasks')
    def my_tasks(self, request):
        """Show my tasks"""
        identity = self.bot.get_plugin('identity').get_identity_by_request(request)
        tasks = self._get_tasks(identity)

        if tasks:
            tz = self._get_user_timezone(identity)
            hashes, min_len = _gen_hashes(tasks)

            lines = []
            for h, (dt, about, identity_id) in zip(hashes, tasks):
                dt = times.to_local(dt, tz)
                lines.append('{0}) {1:%Y-%m-%d %H:%M} {2}'.format(h[:min_len], dt, about))

            request.respond('\n'.join(lines))
        else:
            request.respond('You have no tasks')

    @on_command('(?P<task_id>[0-9a-z]{2,40}) done')
    def done(self, request, task_id):
        """Mark given task as done."""
        # TODO add unittests for two cases:
        # * when task_id not found
        # * when there are more than one task which hash started from task_id
        identity = self.bot.get_plugin('identity').get_identity_by_request(request)
        tasks = self._get_tasks(identity)

        if tasks:
            hashes, min_len = _gen_hashes(tasks)
            filtered_tasks = []
            for h, (dt, about, identity_id) in zip(hashes, tasks):
                if not h.startswith(task_id):
                    filtered_tasks.append((dt, about, identity_id))

            self._set_tasks(identity, filtered_tasks)
        request.respond('done')

    def _remind_users_about_their_tasks(self):
        now = times.now()
        tasks_storage = self.storage.with_prefix('tasks:')
        notify = self.bot.get_plugin('notify').notify

        for identity_id, todos in tasks_storage.items():
            idx = bisect.bisect_left(todos, (now, None, None))
            to_remind = todos[:idx]

            for td, about, id_id in to_remind:
                delta = (now - td)
                if delta.seconds <= self.interval:
                    # Remind only if reminder's datetime is between
                    # this and previous checks
                    notify(identity_id, 'TODO: {0} ({1})'.format(
                        about,
                        hashlib.sha1(about.encode('utf-8')).hexdigest()[:4]
                    ))

    def do_job(self):
        self._remind_users_about_their_tasks()

    def _get_user_timezone(self, identity):
        settings = self.bot.get_plugin('settings')
        return settings.get(identity.id, 'timezone', 'UTC')

    @on_command('now')
    def now(self, request):
        """Outputs server time and user time."""
        identity = self.bot.get_plugin('identity').get_identity_by_request(request)

        now = times.now()
        tz = self._get_user_timezone(identity)
        local = times.to_local(now, tz)

        request.respond('Server time: {}\nLocal time:{}'.format(now, local))


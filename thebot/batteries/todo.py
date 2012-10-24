# coding: utf-8
from __future__ import absolute_import, unicode_literals

import bisect
import times
import hashlib
import six

from dateutil.parser import parse
from collections import defaultdict
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
    name = 'todo'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)

        # interval between bot's attemts to find expired tasks
        self.interval = 60

        if not self.bot.config.unittest:
            self.start_worker(interval=self.interval)

    def _get_tasks(self, user):
        return self.storage.get('tasks', defaultdict(list))[user]

    def _set_tasks(self, user, tasks):
        all_tasks = self.storage.get('tasks', defaultdict(list))
        all_tasks[user] = tasks
        self.storage['tasks'] = all_tasks

    @on_command('remind( me)? at (?P<datetime>.+) to (?P<about>.+)')
    def remind(self, request, datetime, about):
        """Remind about a TODO at given time."""

        try:
            user = request.get_user()
            dt = parse(datetime)
            tz = self._get_user_timezone(user)
            dt = times.to_universal(dt, tz)

            tasks = self._get_tasks(user)
            bisect.insort(tasks, (dt, about, request))
            self._set_tasks(user, tasks)
        except Exception as e:
            request.respond('Unable to parse a date: ' + six.text_type(e))
            raise

        request.respond('ok')

    @on_command('my tasks')
    def my_tasks(self, request):
        """Show my tasks"""
        user = request.get_user()
        tasks = self._get_tasks(user)

        if tasks:
            tz = self._get_user_timezone(user)
            hashes, min_len = _gen_hashes(tasks)

            lines = []
            for h, (dt, about, request) in zip(hashes, tasks):
                dt = times.to_local(dt, tz)
                lines.append('{0}) {1:%Y-%m-%d %H:%M} {2}'.format(h[:min_len], dt, about))

            request.respond('\n'.join(lines))
        else:
            request.respond('You have no tasks')

    @on_command('(?P<task_id>[0-9a-z]{2,40}) done')
    def done(self, request, task_id):
        # TODO add unittests for two cases:
        # * when task_id not found
        # * when there are more than one task which hash started from task_id
        tasks = self._get_tasks(request.get_user())

        if tasks:
            hashes, min_len = _gen_hashes(tasks)
            filtered_tasks = []
            for h, (dt, about, r) in zip(hashes, tasks):
                if not h.startswith(task_id):
                    filtered_tasks.append((dt, about, r))

            self._set_tasks(request.get_user(), filtered_tasks)
        request.respond('done')

    def _remind_users_about_their_tasks(self):
        now = times.now()
        for todos in self.storage.get('tasks', {}).values():
            idx = bisect.bisect_left(todos, (now, None, None))
            to_remind = todos[:idx]

            for td, about, request in to_remind:
                delta = (now - td)
                if delta.seconds <= self.interval:
                    # Remind only if reminder's datetime is between
                    # this and previous checks
                    request.respond('TODO: {0} ({1})'.format(
                        about,
                        hashlib.sha1(about.encode('utf-8')).hexdigest()[:4]
                    ))

    def do_job(self):
        self._remind_users_about_their_tasks()

    @on_command('set my timezone to (?P<timezone>.+/.+)')
    def set_timezone(self, request, timezone):
        """Set you timezone"""
        timezones = self.storage.get('timezones', {})
        timezones[request.get_user()] = timezone
        self.storage['timezones'] = timezones

        request.respond('done')

    def _get_user_timezone(self, user):
        timezones = self.storage.get('timezones', {})
        return timezones.get(user, 'UTC')


    @on_command('now')
    def now(self, request):
        """Outputs server time and user time."""

        now = times.now()
        user = request.get_user()
        tz = self._get_user_timezone(user)
        local = times.to_local(now, tz)

        request.respond('Server time: {}\nLocal time:{}'.format(now, local))

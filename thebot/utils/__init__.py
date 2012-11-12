from __future__ import absolute_import, unicode_literals

import sys

try:
    from collections import MutableMapping
except ImportError:
    from UserDict import DictMixin as MutableMapping


if sys.version_info.major == 3:
    force_unicode = lambda x: x
    force_str = lambda x: x
else:
    def force_unicode(value):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value

    def force_str(value):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return value


def printable(cls):
    """This decorator creates __str__ object for python2.x
    or renames __uncode__ into __str__ for python3.x
    """
    if sys.version_info.major == 3:
        setattr(cls, '__str__', getattr(cls, '__unicode__'))
        delattr(cls, '__unicode__')
    else:
        setattr(cls, '__str__', lambda self: self.__unicode__().encode('utf8'))

    return cls


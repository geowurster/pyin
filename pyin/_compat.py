"""
Python 2 vs. 3 compatibility
"""


import itertools as it
import sys


if sys.version_info.major == 2:  # pragma no cover
    text_type = unicode
    string_types = basestring,
    filter = it.ifilter
    map = it.imap
else:  # pragma no cover
    text_type = str
    string_types = str,
    filter = filter
    map = map

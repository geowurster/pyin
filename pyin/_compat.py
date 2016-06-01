"""
Python 2 vs. 3 compatibility
"""


import sys


if sys.version_info.major == 2:  # pragma no cover
    text_type = unicode
    string_types = basestring,
else:  # pragma no cover
    text_type = str
    string_types = str,

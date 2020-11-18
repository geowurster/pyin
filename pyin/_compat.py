"""Python 2 and 3 compatibility."""


import itertools as it
import sys


if sys.version_info.major == 2:
    from collections import Iterable
    filter = it.ifilter
    map = it.imap
    range = xrange
    zip = it.zip
    string_types = basestring,
    text_type = unicode
    binary_type = bytes

    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        # From six
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec_("""def reraise(tp, value, tb=None):
    try:
        raise tp, value, tb
    finally:
        tb = None
    """)

else:
    from collections.abc import Iterable
    filter = filter
    map = map
    range = range
    string_types = str,
    text_type = str
    binary_type = bytes
    zip = zip

    def reraise(tp, value, tb=None):
        # From six
        try:
            if value is None:
                value = tp()
            if value.__traceback__ is not tb:
                raise value.with_traceback(tb)
            raise value
        finally:
            value = None
            tb = None


def ensure_binary(s, encoding='utf-8', errors='strict'):

    """Coerce **s** to six.binary_type.
    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`
    For Python 3:
      - `str` -> encoded to `bytes`
      - `bytes` -> `bytes`
    """

    # From six

    if isinstance(s, binary_type):
        return s
    elif isinstance(s, text_type):
        return s.encode(encoding, errors)
    else:
        raise TypeError("not expecting type '%s'" % type(s))


def ensure_text(s, encoding='utf-8', errors='strict'):

    """Coerce **s** to six.text_type.

    For Python 2:
      - `unicode` -> `unicode`
      - `str` -> `unicode`
    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """

    # From six

    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    elif isinstance(s, text_type):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))

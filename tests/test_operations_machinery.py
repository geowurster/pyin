"""Tests for making :mod:`pyin` operations work.

Registration, how information about the parent scope is passed around, etc.
"""


import pytest

import pyin


def test_subclass_missing_positional_only_args():

    """Subclasses must define positional-only args."""

    with pytest.raises(RuntimeError) as e:

        class DirectiveBroken(pyin.Directive):
            def __init__(self, directive):
                super().__init__(
                    directive, variable='_', stream_variable='_', scope={})

    assert 'DirectiveBroken.__init__()' in str(e.value)
    assert 'lacks the positional-only arguments' in str(e.value)


def test_subclass_missing_type_annotation():

    """Positional-only args must have type hints."""

    with pytest.raises(RuntimeError) as e:
        class DirectiveBroken(pyin.DirectiveFilter):
            def __init__(self, directive, /, **kwargs):
                super().__init__(directive, **kwargs)

    assert "DirectiveBroken.__init__()" in str(e.value)
    assert "argument 'directive'" in str(e.value)
    assert "must have a type annotation" in str(e.value)


def test_subclass_missing_positional_only_arguments():

    """Positional-only arguments are required."""

    with pytest.raises(RuntimeError) as e:

        class DirectiveBroken(pyin.Directive):
            def __init__(self, directive, arg, **kwargs):
                super().__init__(directive, **kwargs)

    assert "DirectiveBroken.__init__() is malformed" in str(e.value)
    assert "lacks the positional-only arguments" in str(e.value)


def test_Directive_repr():

    """Check 'Directive.__repr__()'."""

    class DirectiveRepr(pyin.Directive):
        def __call__(self, stream):
            raise NotImplementedError

    o = DirectiveRepr('%directive', scope={})
    assert repr(o) == '<DirectiveRepr(%directive, ...)>'


def test_DirectiveError():

    """Ensure ``DirectiveError()``'s message is correct."""

    exc = pyin.DirectiveError('%example')

    assert str(exc) == "invalid directive: %example"

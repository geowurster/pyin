"""Tests for making :mod:`pyin` operations work.

Registration, how information about the parent scope is passed around, etc.
"""


import pytest

import pyin


def test_directive_registry_conflict():

    """Two operations register the same directive."""

    class Op1(pyin.OpBase, directives=('%dir', )):
        pass

    with pytest.raises(RuntimeError) as e:

        # The test lives in 'OpBase.__init_subclass__()', so the class
        # cannot even be defined.
        class Op2(pyin.OpBase, directives=('%dir', )):
            pass

    assert "directive '%dir' conflict" in str(e.value)
    assert 'Op1' in str(e.value)
    assert 'Op2' in str(e.value)


def test_subclass_missing_positional_only_args():

    """Subclasses must define positional-only args."""

    with pytest.raises(RuntimeError) as e:

        class OpBroken(pyin.OpBase, directives=('%test', )):

            def __init__(self, directive):
                super().__init__(
                    directive, variable='_', stream_variable='_', scope={})

    assert 'OpBroken.__init__()' in str(e.value)
    assert 'lacks the positional-only arguments' in str(e.value)


def test_subclass_missing_type_annotation():

    """Positional-only args must have type hints."""

    with pytest.raises(RuntimeError) as e:

        class OpBroken(pyin.OpBase, directives=('%test',)):
            def __init__(self, directive, /, **kwargs):
                super().__init__(directive, **kwargs)

    assert "OpBroken.__init__()" in str(e.value)
    assert "argument 'directive'" in str(e.value)
    assert "must have a type annotation" in str(e.value)


def test_subclass_missing_positional_only_arguments():

    """Positional-only arguments are required."""

    with pytest.raises(RuntimeError) as e:

        class OpBroken(pyin.OpBase, directives=('%test', )):
            def __init__(self, directive, arg, **kwargs):
                super().__init__(directive, **kwargs)

    assert "OpBroken.__init__() is malformed" in str(e.value)
    assert "lacks the positional-only arguments" in str(e.value)


@pytest.mark.parametrize('directive', ['test', '%%test'])
def test_OpBase_subclass_no_prefix(directive):

    with pytest.raises(RuntimeError) as e:

        class OpTest(pyin.OpBase, directives=(directive, )):

            def __init__(self, directive: str, /, **kwargs):
                super().__init__(directive, **kwargs)

    msg = f"'{directive}' for class 'OpTest' is not prefixed with a single '%'"
    assert msg in str(e.value)

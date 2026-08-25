"""Like ``sed``, but Python."""


import abc
import argparse
import builtins
from collections.abc import Iterable
from contextlib import ExitStack
import csv
import functools
from functools import partial
import importlib.util
import inspect
import itertools as it
import json
import operator as op
import os
import re
import signal
import sys
import traceback


__version__ = '1.0dev'
__author__ = 'Kevin Wurster'
__license__ = '''
New BSD License

Copyright (c) 2015-2024, Kevin D. Wurster
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* The names of pyin its contributors may not be used to endorse or
  promote products derived from this software without specific prior written
  permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


_DEFAULT_VARIABLE = 'i'
_DEFAULT_STREAM_VARIABLE = 's'
_IMPORTER_REGEX = re.compile(r"([a-zA-Z_.][a-zA-Z0-9_.]*)")
_DEFAULT_SCOPE = {
    '__builtins__': builtins,
    'it': it,
    'op': op,
    'reduce': functools.reduce
}


class DirectiveError(RuntimeError):

    """Indicates a directive is invalid."""

    def __init__(self, directive):
        self.directive = directive
        super().__init__(f"invalid directive: {self.directive}")


def _normalize_expressions(f):

    """Ensure functions can receive single or multiple expressions.

    A single expression is a string, and multiple expressions is a sequence
    of strings. Function's first positional argument must be ``expressions``.

    :param callable f:
        Decorated function.

    :rtype callable:

    :return:
        Wrapped function.
    """

    @functools.wraps(f)
    def inner(expressions, *args, **kwargs):

        if isinstance(expressions, str):
            expressions = (expressions, )
        elif not isinstance(expressions, Iterable):
            raise TypeError(f"not a sequence: {expressions=}")

        return f(tuple(expressions), *args, **kwargs)

    return inner


@_normalize_expressions
def compile(
        expressions,
        variable=_DEFAULT_VARIABLE,
        stream_variable=_DEFAULT_STREAM_VARIABLE,
        scope=None,
        global_scope=None,
):

    """Compile expressions to ``pyin`` objects.

    Each class is a subclass of ``Directive()``.

    :param str or sequence expressions:
        One or more expressions to compile.
    :param str variable:
        Operations should use this variable when inserting an item into
        a scope during evaluation.
    :param str stream_variable:
        Like ``variable`` but when referencing the entire data stream.
    :param dict or None scope:
        Import into this dictionary.
    :param dict or None global_scope:
        Also expose this global scope to all directives.

    :rtype sequence:

    :return:
        A sequence of compiled operations. An operation is a subclass of
        ``Directive()``.
    """

    tokens = list(expressions)

    # Note that 'scope = scope or {}' is different from 'if scope is None'.
    # The latter always creates a new dict if the caller does not pass one,
    # and the latter creates a new dict if the caller passes an empty dict.
    # The former makes it impossible to update an existing empty scope, while
    # the latter does not.
    if scope is None:
        scope = {}

    if global_scope is None:
        global_scope = _DEFAULT_SCOPE

    compiled = []
    while tokens:

        if not tokens:
            raise DirectiveError('parsing error: no tokens remain')  # pragma no cover

        if not tokens[0].startswith('%'):
            tokens.insert(0, '%evalauto')

        directive = tokens.pop(0)

        if directive not in _DIRECTIVE_REGISTRY:
            raise DirectiveError(directive)

        cls = _DIRECTIVE_REGISTRY[directive]
        sig = inspect.signature(cls)

        # Collect additional arguments for the class.
        args = []

        # The first argument is the directive, which have already consumed.
        for param in tuple(sig.parameters.values())[1:]:

            if param.kind != param.POSITIONAL_ONLY:
                continue

            if not tokens:
                raise DirectiveError(
                    f"missing argument 'expression' for: {directive}"
                )
            else:
                value = tokens.pop(0)
                value = param.annotation(value)
                args.append(value)

        compiled.append(
            cls(
                directive,
                *args,
                scope=scope,
                global_scope=global_scope,
                variable=variable,
                stream_variable=stream_variable,
            )
        )

    return tuple(compiled)


@_normalize_expressions
def importer(expressions, scope):

    """Parse expressions and import modules into a single scope.

    An expression might be something like ``"os.path.exists(i)"``. This
    function parses that expression and imports ``os.path`` into ``scope``.
    Expressions are evaluated by Python's eval within this scope.

    :param str or sequence expressions:
        One or more Python expression.
    :param dict scope:
        Track imported objects in this scope. Typically, all imports are
        written to a single scope.

    :rtype dict:
    """

    # Find all potential modules to try and import
    all_matches = set(it.chain.from_iterable(
        re.findall(_IMPORTER_REGEX, expr) for expr in expressions))

    for match in all_matches:

        # 'match' could be something like:
        #   json.dumps
        #   collections.OrderedDict.items
        module = match.split('.', 1)[0]

        # Try and limit the number of import attempts, but only when confident.
        if not module or hasattr(builtins, module):
            continue

        try:
            scope[module] = importlib.import_module(module)

        # Failed to import. To be helpful, check and see if the module exists.
        # if it does, the caller is referencing something that cannot be
        # imported, like a class method. Unclear how to trigger this in a test.
        except ImportError:  # pragma no cover
            res = importlib.util.find_spec(module)
            if res is not None:
                raise ImportError(
                    f"attempting to import something that cannot be imported"
                    f" from a module that does exist: {match}"
                )  # pragma no cover

    return scope


@_normalize_expressions
def eval(
        expressions,
        stream,
        scope=None,
        global_scope=None,
        variable=_DEFAULT_VARIABLE,
        stream_variable=_DEFAULT_STREAM_VARIABLE
):

    """Evaluate Python expressions across a stream of data.

    Expressions are passed through ``importer()`` to construct a scope, and
    then evaluated one-by-one across each item in ``stream`` by Python's
    ``eval()``.

    :param str or sequence expressions:
        One or more expressions.
    :param iterable stream:
        Map all ``expressions`` across each item.
    :param dict or None scope:
        A scope for Python's builtin ``eval()``. This function automatically
        imports modules referenced in ``expressions`` into the scope.
    :param str variable:
        Each item in ``stream`` should be stored in this variable in the
        scope.
    :param str stream_variable:
        Like ``variable`` but for referencing ``stream`` itself.

    :return:
        An iterator of results.
    """

    if scope is None:
        scope = {}

    if global_scope is None:
        global_scope = _DEFAULT_SCOPE

    importer(expressions, scope=scope)
    compiled_expressions = compile(
        expressions,
        variable=variable,
        stream_variable=stream_variable,
        scope=scope
    )

    for op_instance in compiled_expressions:
        stream = op_instance(stream)

    yield from stream


###############################################################################
# Operations


def _peek(iterable):

    """Peek at the first item of an iterable.

    :param iterable iterable:
        Get the first item from this iterable.

    :return:
        A ``tuple`` with two elements. The first is the next value in
        ``iterable``, and the second is the reconstructed iterable, but
        likely as a different type.
    """

    iterable = (i for i in iterable)
    first = next(iterable)
    return first, it.chain([first], iterable)


class Directive(abc.ABC):

    """Base class for defining an operation.

    Subclassers can use positional-only arguments and type annotations in
    ``__init__`` to define arguments associated with the directive and
    their type.

    Subclassers are free to reference a variety of attributes on their instance
    that contain a variety of information about how they should execute:

    directive
      A string like ``%eval`` indicating which directive is being executed.
      Subclassers may make decisions based on the name of the directive.

    variable
      When executing a Python expression, place the item currently being
      processed into this environment in the scope for Python's builtin
      ``eval()``. When only evaluating an expression against an item (and not
      the full ``stream`` object), it is good to not use ``stream_variable``.

    stream_variable
      Like ``variable`` but for the entire ``stream`` object.

    scope
      Use this as the global scope when executing expressions with Python's
      builtin ``eval()`` function.
    """

    def __init__(
            self,
            directive: str,
            # The slash below is significant! Its presence makes the preceding
            # args positional-only argument, which we look for elsewhere.
            /,
            scope: dict,
            global_scope: dict | None = None,
            variable: str = _DEFAULT_VARIABLE,
            stream_variable: str = _DEFAULT_STREAM_VARIABLE,
    ):

        """
        :param str directive:
            The directive actually usd in the expressions. Some operation
            classes can support multiple directives.
        """

        if global_scope is None:
            global_scope = _DEFAULT_SCOPE

        self.directive = directive
        self.scope = scope
        self.global_scope = global_scope
        self.variable = variable
        self.stream_variable = stream_variable

    def __init_subclass__(cls):

        """Validate a subclass."""

        # First validate subclass
        sig = inspect.signature(cls.__init__)

        # Positional-only arguments are used to define arguments for a
        # directive.
        pos_only = [
            p for p in sig.parameters.values()
            if p.kind == p.POSITIONAL_ONLY
        ]
        pos_only = pos_only[1:]  # First is 'self'
        if not pos_only:
            raise RuntimeError(
                f"{cls.__name__}.__init__() is malformed and lacks the"
                f" positional-only arguments used for determining directive"
                f" arguments"
            )

        # Positional arguments _must_ be type hinted for casting purposes.
        for param in pos_only:
            if param.annotation == inspect._empty:
                raise RuntimeError(
                    f"argument '{param.name}' for '{cls.__name__}.__init__()'"
                    f" must have a type annotation"
                )

    def __repr__(self):

        """Approximate representation of operation instance."""

        return f"<{self.__class__.__name__}({self.directive}, ...)>"

    @abc.abstractmethod
    def __call__(self, stream):

        """Process a stream of data.

        Implementation must:

        1. Treat ``stream`` as an iterable object and be otherwise agnostic
           to its type. Iterating directly as a ``for`` loop, or wrapping
           as a generator via ``(i for i in stream)`` are both appropriate.
        2. Consume all items in ``stream``.
        3. Be a generator or return an iterator.
        4. Be prepared for the input ``stream`` to not contain any data.

        An implementation should also be conscious of function call overhead.
        ``pyin`` primarily seeks to be friendly and convenient, but fast is
        also nice.

        :param stream:
            Input data stream. An iterable object.

        :return:
            An iterable object.
        """

        raise NotImplementedError  # pragma no cover


class DirectiveEval(Directive):

    """Evaluate a Python expression or statement.

    Uses ``eval()`` and ``exec()``.

    In code terms, this:

    .. code:: python

        >>> import pyin
        >>> list(pyin.eval('i + 1', range(3)))
        [1, 2, 3]

    is equivalent to:

    .. code:: python

        >>> import pyin
        >>> list(pyin.eval(['%eval', 'i + 1'], range(3)))
        [1, 2, 3]
    """

    # Order matters. Aside from 'auto', this is the order in which compiling is
    # tried. Most statements compile for 'exec', but in most cases the caller
    # wants 'eval'.
    supported_modes = ('auto', 'eval', 'exec')

    def __init__(
            self,
            directive: str,
            expression: str,
            /,
            *args,
            mode,
            operate_on_stream=False,
            **kwargs,
    ):

        super().__init__(directive, *args, **kwargs)
        self.expression = expression
        self.operate_on_stream = operate_on_stream

        if self.expression == '' or self.expression.isspace():
            raise SyntaxError(
                f'expression is white space or empty: {repr(self.expression)}'
            )

        elif mode not in self.supported_modes:  # pragma no cover
            raise ValueError(
                f'invalid {mode=} expected one of:'
                f' {" ".join(self.supported_modes)}'
            )

        if mode == 'auto':
            try_modes = tuple(i for i in self.supported_modes if i != 'auto')
        else:
            try_modes = (mode, )

        exc = None
        for try_mode in try_modes:
            try:
                self.code = builtins.compile(
                    self.expression,
                    filename='<string>',
                    mode=try_mode,
                )
                self.mode = try_mode
                break
            except SyntaxError as e:
                exc = e
        else:
            raise exc

        has_variable_conflict = (
            self.variable in self.code.co_names
            and self.stream_variable in self.code.co_names
        )

        if has_variable_conflict:
            raise ValueError(
                f'contains item and stream variables: {self.expression}'
            )

    def __repr__(self):
        return '<{cname}({directive}, {expression})>'.format(
            cname=self.__class__.__name__,
            directive=self.directive,
            expression=repr(self.expression),
        )

    def _call(self, stream, variable):

        if self.mode == 'eval':
            for item in stream:
                self.scope[variable] = item
                yield builtins.eval(
                    self.code,
                    self.global_scope,
                    self.scope,
                )

        elif self.mode == 'exec':

            # Unlike 'eval()', 'exec()' executes statements, meaning that it
            # updates the scope in place. The current item must be extracted
            # from the scope after calling 'exec()'. BUT! It is possible for
            # 'exec()' to delete the variable, so we cannot assume it
            # exists in the local scope later. Possibly supporting this
            # behavior is bad, and we should instead produce an error if this
            # happens.

            local_scope = {}
            for item in stream:
                self.scope[self.variable] = item
                builtins.exec(
                    self.code,
                    self.global_scope,
                    self.scope,
                )

                # It is possible to 'del variable'!
                if variable in self.scope:
                    yield self.scope[variable]

        else:  # pragma no cover
            raise DirectiveError(self.directive)


    def __call__(self, stream):

        if self.operate_on_stream:
            stream = [(i for i in stream)]
            variable = self.stream_variable
        else:
            variable = self.variable

        out = self._call(stream, variable)
        if self.operate_on_stream:
            out = next(out)

        yield from out


class DirectiveEvalIf(Directive):

    """Like ``DirectiveEval()``, but for optionally executing an expression.

    Does not filter. If the sentinel expression evaluates as ``False``, the
    item is emitted without evaluating the expression.
    """

    def __init__(
            self,
            directive: str,
            sentinel_expression: str,
            expression: str,
            /,
            *args,
            mode,
            **kwargs
    ):

        """See base class for most parameters.

        :param str sentinel_expression:
            Determines if ``expression`` should be evaluated.
        """

        super().__init__(directive, *args, **kwargs)

        self.expression = expression
        self.sentinel_expression = sentinel_expression
        self.mode = mode

    def __call__(self, stream):

        selection, stream = it.tee(stream, 2)

        selector = DirectiveEval(
            self.directive[:5],
            self.sentinel_expression,
            variable=self.variable,
            mode='eval',
            stream_variable=self.stream_variable,
            scope=self.scope,
            global_scope=self.global_scope,
        )

        evaluator = DirectiveEval(
            self.directive[:5],
            self.expression,
            mode=self.directive[1:5],
            variable=self.variable,
            stream_variable=self.stream_variable,
            scope=self.scope,
            global_scope=self.global_scope,
        )

        selection = selector(selection)
        evaluated = evaluator(stream)

        for sentinel in selection:
            if sentinel:
                yield next(evaluated)
            else:
                yield next(stream)

        # Ensure both iterators were fully exhausted. If not, something is
        # wrong.
        hint_data = {
            'selection': selection,
            'evaluated': evaluated
        }
        for hint, data in hint_data.items():
            try:
                next(data)
                raise RuntimeError(f'failed to exhaust: {hint}')  # pragma no cover
            except StopIteration:
                pass


class DirectiveFilter(Directive):

    """Filter data based on a Python expression.

    These are equivalent:

      %filter "i > 2"
      %filterfalse "i <= 2"
    """

    def __init__(
            self,
            directive: str,
            expression: str,
            /,
            *args,
            filterfalse: bool = False,
            **kwargs
    ):
        super().__init__(directive, *args, **kwargs)

        if expression.lower() == 'none':
            self.expression = 'None'
            evaluator_expression = f'bool({self.variable})'
        else:
            self.expression = expression
            evaluator_expression = self.expression

        self.filterfalse = filterfalse
        self.expression = expression

        self.evaluator = DirectiveEval(
            '%eval',
            evaluator_expression,
            *args,
            mode='eval',
            **kwargs,
        )

    def __repr__(self):
        return '<{cname}({directive}, {expression}, filterfalse={ff})'.format(
            cname=self.__class__.__name__,
            directive=self.directive,
            expression=repr(self.evaluator.expression),
            ff=self.filterfalse
        )

    def __call__(self, stream):

        stream, selection = it.tee(stream, 2)

        selection = self.evaluator(selection)
        if self.filterfalse:
            selection = (not i for i in selection)

        return it.compress(stream, selection)


class DirectiveAccumulate(Directive):

    """Accumulate the entire stream into a single object."""

    def __call__(self, stream):

        # At first glance the simplest implementation is:
        #   yield list(stream)
        # however, if 'stream' is empty this is equivalent to:
        #   yield []
        # which converts the contents of 'stream' into a single empty list.
        stream = list(stream)
        if stream:
            yield stream


class DirectiveChain(Directive):

    """Flatten the stream by one level – like ``itertools.chain()``."""

    def __call__(self, stream):

        return it.chain.from_iterable(stream)


class DirectiveJSON(Directive):

    """Serialize/deserialize JSON data.

    If the input is a string it is assumed to be JSON and deserialized.
    Otherwise, it is serialized.
    """

    def __call__(self, stream):

        try:
            first, stream = _peek(stream)
        except StopIteration:
            return []

        # 'json.loads/dumps()' both use these objects internally, but create
        # an instance with every call. Presumably this is faster.
        if isinstance(first, str):
            func = json.JSONDecoder().decode
        else:
            func = json.JSONEncoder().encode

        return map(func, stream)


class DirectiveCSVDict(Directive):

    """Read/write data via ``csv.DictReader()`` and ``csv.DictWriter()``.

    If the input data is text data is parsed with the default
    ``csv.DictReader()`` settings. Otherwise, a header and rows with "quote
    all" enabled are written.
    """

    def __call__(self, stream):

        try:
            first, stream = _peek(stream)
        except StopIteration:
            return

        # Reading from a CSV
        if isinstance(first, str):
            yield from csv.DictReader(stream)

        # Writing to a CSV
        else:

            # This file-like object doesn't actually write to a file. Since
            # 'csv.DictWriter.write()' just returns values up the chain, just
            # returning from 'FakeFile.write()' is enough to get a line of
            # text to pass down the line.
            class FakeFile:
                def write(self, data):
                    return data

            writer = csv.DictWriter(
                FakeFile(),
                fieldnames=list(first.keys()),
                quoting=csv.QUOTE_ALL,
                lineterminator='',  # pyin itself handles newline characters
            )

            yield writer.writeheader()
            for row in stream:
                yield writer.writerow(row)


class DirectiveReversed(Directive):

    """Reverse item/stream."""

    def __init__(
            self,
            directive: str,
            /,
            *args,
            revstream: bool = False,
            **kwargs,
    ):
        super().__init__(directive, *args, **kwargs)
        self.revstream = revstream

    def __call__(self, stream):

        # Python's 'reversed()' is kind of weird, and seems to only work well
        # when the object is immediately iterated over. So, to be more helpful,
        # we have some very extra special handling here.

        if self.revstream:
            yield from reversed(stream)

        else:

            try:
                first, stream = _peek(stream)
            except StopIteration:
                return

            # Can reverse these objects by slicing while preserving the
            # original type.
            if isinstance(first, (str, list, tuple)):
                yield from (i[::-1] for i in stream)

            else:
                yield from (tuple(reversed(i)) for i in stream)


class DirectiveBatched(Directive):

    """Group stream into chunks with no more than N elements.

    Equivalent to ``itertools.batched()``.
    """

    def __init__(self, directive: str, chunksize: int, /, **kwargs):

        """
        :param str directive:
            See parent implementation.
        :param int chunksize:
            Maximum number of items to include in each "batch".
        :param **kwargs kwargs:
            See parent implementation.
        """

        super().__init__(directive, **kwargs)
        self.chunksize = chunksize

    def __call__(self, stream):

        # 'itertools.batched()' was introduced in Python 3.12 and cannot
        # be used
        stream = (i for i in stream)
        while chunk := tuple(it.islice(stream, self.chunksize)):
            yield tuple(chunk)

class DirectiveString(Directive):

    def __call__(self, stream):

        split = self.directive.split(':', 1)

        args = []
        if len(split) == 1:
            directive = split[0]
        else:
            directive, arg = split
            args.append(arg)

        method = directive[1:]

        return map(op.methodcaller(method, *args), stream)


class DirectiveReplace(Directive):

    """Replace a portion of a string with a new string."""

    def __init__(self, directive: str, old: str, new: str, /, **kwargs):

        """
        :param str directive:
            Currently active directive.
        :param str old:
            Replace all occurrences of this substring with ``new``.
        :param str new:
            See ``old``.
        :param **kwargs kwargs:
            See parent implementation.
        """

        super().__init__(directive, **kwargs)

        self.old = old
        self.new = new

    def __call__(self, stream):

        return map(op.methodcaller('replace', self.old, self.new), stream)


class DirectiveCast(Directive):

    """Cast to a builtin Python type."""

    def __call__(self, stream):
        func = getattr(builtins, self.directive[1:])
        return map(func, stream)


class DirectiveISlice(Directive):

    """Take at most the first N items from the stream."""

    def __init__(self, directive: str, count: int, /, **kwargs):
        super().__init__(directive, **kwargs)
        self.count = count

    def __call__(self, stream):
        return it.islice(stream, self.count)


class DirectivePartition(DirectiveString):
    def __init__(self, directive: str, sep: str, /, *args, **kwargs):
        super().__init__(f'{directive}:{sep}', *args, **kwargs)


###############################################################################
# Directive Registry

_DIRECTIVE_REGISTRY = {
    '%accumulate': DirectiveAccumulate,
    '%batched': DirectiveBatched,
    '%bool': DirectiveCast,
    '%chain': DirectiveChain,
    '%csvd': DirectiveCSVDict,
    '%dict': DirectiveCast,
    '%eval': partial(DirectiveEval, mode='eval'),
    '%evalauto': partial(DirectiveEval, mode='auto'),
    '%evalif': partial(DirectiveEvalIf, mode='eval'),
    '%exec': partial(DirectiveEval, mode='exec'),
    '%execif': partial(DirectiveEvalIf, mode='exec'),
    '%filter': DirectiveFilter,
    '%filterfalse': partial(DirectiveFilter, filterfalse=True),
    '%float': DirectiveCast,
    '%int': DirectiveCast,
    '%islice': DirectiveISlice,
    '%join': DirectiveString,
    '%json': DirectiveJSON,
    '%list': DirectiveCast,
    '%lower': DirectiveString,
    '%lstrip': DirectiveString,
    '%lstrips': DirectiveString,
    '%partition': DirectivePartition,
    '%replace': DirectiveReplace,
    '%rev': DirectiveReversed,
    '%revstream': partial(DirectiveReversed, revstream=True),
    '%rpartition': DirectivePartition,
    '%rstrip': DirectiveString,
    '%set': DirectiveCast,
    '%split': DirectiveString,
    '%str': DirectiveCast,
    '%stream': partial(DirectiveEval, mode='auto', operate_on_stream=True),
    '%strip': DirectiveString,
    '%tuple': DirectiveCast,
    '%upper': DirectiveString,
}


###############################################################################
# Command Line Interface


def _type_variable(value):

    """:mod:`argparse` type caster for ``--variable`` flag.

    Ensures the given variable is valid.
    """

    if not value.isidentifier():
        raise argparse.ArgumentTypeError(
            f'string is not valid as a variable: {value}')

    return value


def _type_gen(value):

    """Ensure ``--gen`` is not combined with piping data to ``stdin``."""

    if not sys.stdin.isatty():
        raise argparse.ArgumentTypeError(
            'cannot combine with piping data to stdin')

    return _type_expression(value)


def _type_expression(value):

    """Validate a Python expression argument.

    Not comprehensive. Ultimately compiling the expression to a code object
    is the only method for ensuring compliance.
    """

    if value.isspace():
        raise argparse.ArgumentTypeError(
            'expression is entirely white space'
        )
    elif value == '':
        raise argparse.ArgumentTypeError(
            'empty expression'
        )

    return value


def argparse_parser():

    """Construct an :obj:`argparse.ArgumentParser`.

    Provided as an entrypoint to argument parsing that can provide a better
    entrypoint to :func:`main` from Python.
    """

    aparser = argparse.ArgumentParser(
        description="Like sed, but Python!",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    aparser.add_argument(
        '--version', action='version', version=__version__
    )

    # Input data
    input_group = aparser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--gen',
        metavar='EXPR',
        dest='generate_expr',
        type=_type_gen,
        help="Execute this Python expression and feed results into other"
             " expressions."
    )
    input_group.add_argument(
        '-i', '--infile',
        metavar='PATH',
        default='-',
        help="Read input from this file. Use '-' for stdin (the default)."
    )

    aparser.add_argument(
        '-o', '--outfile',
        metavar='PATH',
        default='-',
        help="Write to this file. Use '-' for stdout (the default)."
    )
    aparser.add_argument(
        '--linesep',
        metavar='STR',
        default=os.linesep,
        help=f"Write this after every line. Defaults to: {repr(os.linesep)}."
    )
    aparser.add_argument(
        '-s', '--setup', action='append', metavar='EXPR',
        type=_type_expression,
        help="Execute one or more Python statements to pre-initialize objects,"
             " import objects with new names, etc."
    )
    aparser.add_argument(
        '--variable',
        metavar='STR',
        type=_type_variable,
        default=_DEFAULT_VARIABLE,
        help="Place each input item in this variable when evaluating"
             " expressions."
    )
    aparser.add_argument(
        '--stream-variable',
        metavar='STR',
        type=_type_variable,
        default=_DEFAULT_STREAM_VARIABLE,
        help="Place the stream in this variable when evaluating expressions"
             " against the stream itself."
    )

    aparser.add_argument(
        'expressions',
        metavar='EXPR',
        type=_type_expression,
        nargs='*',
        help='Python expression.'
    )

    return aparser


def _adjust_sys_path(f):

    """Adjust ``sys.path`` to include nearby files.

    Being able to reference Python files or modules in the current directory
    is very powerful, but requires an adjustment ``sys.path`` that we to
    only manifest in certain contexts.

    Primarily, applying this to ``main()`` allows it to provide an interface
    to the CLI from within Python that also includes the ``sys.path``
    adjustment.

    :param callable f:
        Function to wrap.
    """

    @functools.wraps(f)
    def inner(*args, **kwargs):

        cleanup = '' not in sys.path
        try:
            if '' not in sys.path:
                sys.path.append('')
            return f(*args, **kwargs)
        finally:
            if cleanup:
                sys.path.pop(sys.path.index(''))

    return inner


@_adjust_sys_path
def main(
        generate_expr,
        infile,
        outfile,
        expressions,
        linesep,
        setup,
        variable,
        stream_variable):

    """Command line interface.

    Direct access to the CLI logic. See ``argparse_parser()`` for a compatible
    parser. Returns an exit code, but does not suppress all exceptions.

    :param str generate_expr:
        Generate input data from this expression instead of ``infile``.
    :param file infile:
        Read text from this file.
    :param file outfile:
        Write text to this file.
    :param sequence expressions:
        Evaluate these expressions.
    :param str linesep:
        Postfix for each output line.
    :param list setup:
        Execute these Python statements to set up the environment.
    :param str variable:
        Expressions reference input data via this variable.
    :param str stream_variable:
        Expressions reference the stream via this variable.

    :rtype int:

    :returns:
        Exit code.
    """

    # ==== Setup ==== #

    # Just let 'eval()' handle scope creation
    if not setup:
        scope = None

    # Run setup 'exec()' statements.
    else:

        # Will eventually be treated as the global scope in 'eval()'. Only
        # need a local scope to get data out of the 'exec()' calls. Local
        # scope is copied to global scope.
        scope = importer(setup, _DEFAULT_SCOPE.copy())
        local_scope = {}

        # Probably possible to use 'OpEval(%exec)' here, but not immediately
        # clear how to manifest the scope changes.
        for statement in setup:
            code_object = builtins.compile(statement, '<string>', 'exec')
            exec(code_object, scope, local_scope)
            scope.update(local_scope)

        del local_scope

    # ==== Fetch Input Data Stream ==== #

    # Equivalent to just invoking '$ pyin'. No input files, no piping data
    # to 'stdin', and no '--gen' flag. Technically users can type data into
    # 'stdin' in this mode, but that doesn't seem very useful.
    if generate_expr is None and infile.isatty():
        argparse_parser().print_help()
        return 2

    # Generating data for input.
    elif generate_expr is not None:
        input_stream = eval(
            [generate_expr],
            [object],  # Need something to iterate over
            variable='_'  # Obfuscate the scope a bit
        )

        input_stream = next(input_stream)
        if not isinstance(input_stream, Iterable):
            print(
                "ERROR: '--gen' expression did not produce an iterable"
                " object:", generate_expr, file=sys.stderr)
            return 1

    # Reading from the input file.
    else:
        input_stream = infile

        # Strip newline characters. They are added later.
        input_stream = (i.rstrip(os.linesep) for i in input_stream)

    # ==== Process Data ==== #

    for line in eval(
            expressions, input_stream, scope=scope,
            variable=variable, stream_variable=stream_variable):

        if not isinstance(line, str):
            line = repr(line)

        try:
            outfile.write(line)
            outfile.write(linesep)

        # Probably piping to something like '$ head' that intentionally does
        # not fully consume the stream. Python docs have a note recommending
        # handling. Note that this is not an error in our case, so we do not
        # 'exit(1)'. Unclear how to reliably test this.
        # https://docs.python.org/3/library/signal.html?#note-on-sigpipe
        except BrokenPipeError:  # pragma no cover
            # Python flushes standard streams on exit; redirect remaining output
            # to devnull to avoid another BrokenPipeError at shutdown
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            break

    return 0


def _cli_entrypoint(rawargs=None):

    """Command-line interface entrypoint.

    ``main()`` and ``argparse_parser()`` provide the tooling needed to use
    the ``$ pyin`` utility's logic from within Python. This layer handles
    some error conditions that are closer to the shell than Python.

    Raises ``SystemExit`` instead of returning a value.

    :param list or None rawargs:
        Like :obj:`sys.argv` (used by default) but without the interpreter
        path. Used in testing.

    :raises SystemExit:
    """

    kwargs = vars(argparse_parser().parse_args(args=rawargs))

    try:

        with ExitStack() as stack:

            infile = kwargs['infile']
            if infile == '-':
                infile = sys.stdin
            else:
                infile = stack.enter_context(open(infile))

            outfile = kwargs['outfile']
            if outfile == '-':
                outfile = sys.stdout
            else:
                outfile = stack.enter_context(open(outfile, 'w'))

            kwargs.update(
                infile=infile,
                outfile=outfile,
            )

            exit_code = main(**kwargs)

    except SyntaxError as e:

        exit_code = 1

        # Reformat the exception information to provide clarity that this is
        # something the user did wrong, and not something 'pyin' did wrong.
        lines = [
            f'ERROR: expression contains a syntax error: {e.msg}',
            '',
            # For some reason 'compile(..., mode=exec)' produces a
            # 'SyntaxError' with a trailing newline, but 'mode=eval' does not!
            f'    {e.text.rstrip(os.linesep)}',
            f'    {" " * (e.offset - 1)}^',
        ]
        print(os.linesep.join(lines), file=sys.stderr)

    # User interrupted with '^C' most likely, but technically this is just
    # a SIGINT. At one point the code in the 'except' block showed up in the
    # 'pytest-cov' report, but not anymore.
    except KeyboardInterrupt:  # pragma no cover
        print()  # Don't get a trailing newline otherwise
        exit_code = 128 + signal.SIGINT

    except Exception as e:

        exit_code = 1

        # A 'RuntimeError()' indicates a problem that should have been caught
        # during testing. We want a full traceback in these cases, but not when
        # the user provided an invalid directive name.
        is_rte = isinstance(e, RuntimeError)
        is_de = isinstance(e, DirectiveError)
        if 'PYIN_FULL_TRACEBACK' in os.environ or (is_rte and not is_de):
            message = ''.join(traceback.format_exc()).rstrip()
        else:
            message = f"ERROR: {str(e)}"

        print(message, file=sys.stderr)

    exit(exit_code)


if __name__ == '__main__':
    _cli_entrypoint()  # pragma no cover

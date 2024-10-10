"""Like ``sed``, but Python."""


import abc
import argparse
from collections import deque
from collections.abc import Iterable
import builtins
import csv
import functools
import importlib.util
import inspect
import io
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

Copyright (c) 2015-2023, Kevin D. Wurster
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
_EVAL_DIRECTIVE = '%eval'
_IMPORTER_REGEX = re.compile(r"([a-zA-Z_.][a-zA-Z0-9_.]*)")
_DIRECTIVE_REGISTRY = {}
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
        scope=None):

    """Compile expressions to operation classes.

    An operation class is a subclass of ``OpBase()``.

    :param str or sequence expressions:
        One or more expressions to compile.
    :param str variable:
        Operations should use this variable when inserting an item into
        a scope during evaluation.
    :param str stream_variable:
        Like ``variable`` but when referencing the entire data stream.
    :param dict or None scope:
        Import into this dictionary.

    :rtype sequence:

    :return:
        A sequence of compiled operations. An operation is a subclass of
        ``OpBase()``.
    """

    compiled = []

    # Note that 'scope = scope or {}' is different from 'if scope is None'.
    # The latter always creates a new dict if the caller does not pass one,
    # and the latter creates a new dict if the caller passes an empty dict.
    # The former makes it impossible to update an existing empty scope, while
    # the latter does not.
    if scope is None:
        scope = {}

    tokens = list(expressions)
    del expressions

    # Check for empty strings in expressions. A check with 'all(tokens)' may
    # be sufficient, but could be confused by '__bool__()'.
    if not all(len(t) for t in tokens):
        raise SyntaxError(
            f"one or more expression is an empty string:"
            f" {' '.join(map(repr, tokens))}")

    while tokens:

        # Get a directive
        directive = tokens.pop(0)

        # If it is not actually a directive just assume it is a Python
        # expression that should be evaluated. Stick the token back in the
        # queue so that it can be evaluated as an argument - makes the rest
        # of the code simpler.
        if directive[0] != '%':
            tokens.insert(0, directive)
            directive = _EVAL_DIRECTIVE

        if directive not in _DIRECTIVE_REGISTRY:
            raise ValueError(f'invalid directive: {directive}')
        cls = _DIRECTIVE_REGISTRY[directive]

        # Operation classes define how many arguments are associated with the
        # directives they service with annotated positional-only arguments.
        # Find them.

        sig = inspect.signature(cls.__init__)
        pos_only = [
            p for p in sig.parameters.values()
            if p.kind == p.POSITIONAL_ONLY
        ]
        pos_only = pos_only[1:]  # First is 'self'

        # Arguments for instantiating argument class
        args = [directive]
        for param in pos_only[1:]:

            # Ran out of CLI arguments but expected more
            if not len(tokens):
                raise ValueError(
                    f"missing argument '{param.name}' for directive:"
                    f" {directive}")

            args.append(param.annotation(tokens.pop(0)))

        # 'OpBaseExpression()' is special in that it receives scope information
        # for Python's builtin 'eval()' and 'exec()' functions, and associated
        # variables.
        kwargs = {}
        if issubclass(cls, OpBaseExpression):
            kwargs.update(
                variable=variable,
                scope=scope,
                stream_variable=stream_variable
            )

        compiled.append(cls(*args, **kwargs))

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

    # Update with standard baseline
    scope.update(_DEFAULT_SCOPE)

    # Make the scope discoverable with a bit of introspection. Callers may
    # want to find out what is available. This is documented.
    scope['_scope'] = scope

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


class OpBase(abc.ABC):

    """Base class for defining an operation.

    Subclassers can use positional-only arguments and type annotations in
    ``__init__`` to define arguments associated with the directive and
    their type.

    Subclassers are free to reference a variety of attributes on their instance
    that contain a variety of information about how they should execute:

    directive
      The directive currently being executed. Set to ``None`` to disable
      registering. This behavior is useful for base classes that extend
      ``OpBase()``.

    directives
      A list of all supported directives.

    variable
      When executing a Python expression, place the item currently being
      processed into this environment in the scope for Python's builtin
      ``eval()``. When only evaluating an expression against an item (and not
      the full ``stream`` object), it is good to not use ``stream_variable``.

    stream_variable
      Like ``variable`` but for the entire ``stream`` object.

    scope
      Use this as the global scope when exeucting expressions with Python's
      builtin ``eval()`` function.
    """

    directives = None

    def __init__(
            self,
            directive: str,
            # The slash below is significant! Its presence makes the preceding
            # args positional-only argument, which we look for elsewhere.
            /
    ):

        """
        :param str directive:
            The directive actually usd in the expressions. Some operation
            classes can support multiple directives.
        """

        self.directive = directive

        if self.directive not in self.directives:
            raise RuntimeError(
                f"instantiated '{repr(self)}' with directive"
                f" '{self.directive}' but supports:"
                f" {' '.join(self.directives)}"
            )

    def __init_subclass__(cls, /, directives, **kwargs):

        """Register subclass and its directives.

        Also populates ``Operations.directives`` class variable.

        :param str directives:
            Directives supported by this class. Like ``('%upper', '%lower')``.
        :param **kwargs kwargs:
            Additional arguments.
        """

        global _DIRECTIVE_REGISTRY

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
                    f"argument '{param.name}' for directive"
                    f" '{cls.__name__}.__init__()' must have a type annotation"
                )

        # Register subclasss
        super().__init_subclass__(**kwargs)
        if directives is not None:
            for d in directives:
                if d[0] != '%' or d.count('%') != 1:
                    raise RuntimeError(
                        f"directive '{d}' for class '{cls.__name__}' is not"
                        f" prefixed with a single '%'")
                elif d in _DIRECTIVE_REGISTRY:
                    raise RuntimeError(
                        f"directive '{d}' conflict:"
                        f" {cls} {_DIRECTIVE_REGISTRY[d]}")

                cls.directives = directives
                _DIRECTIVE_REGISTRY[d] = cls

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


class OpBaseExpression(OpBase, directives=None):

    """Base class for operations evaluating an expression.

    Typically by ``eval()`` or ``exec()``.
    """

    def __init__(
            self,
            directive: str,
            expression: str,
            /,
            variable,
            stream_variable,
            scope
    ):
        """
        :param str directive:
            See parent implementation.
        :param str variable:
            Operations executing expressions with Python's ``eval()`` should
            place data in this variable in the scope.
        :param str stream_variable:
            Like ``variable`` but for referencing the full stream of data.
        :param dict scope:
            Operations executing expressions with Python's ``eval(0)`` should
            use this global scope.
        """

        super().__init__(directive)

        self.expression = expression
        self.variable = variable
        self.stream_variable = stream_variable
        self.scope = scope

    def compiled_expression(self, mode):

        """Compile a Python expression using the builtin ``compile()``."""

        try:
            return builtins.compile(self.expression, '<string>', mode)
        except SyntaxError as e:
            raise SyntaxError(
                f"expression {repr(self.expression)} contains a syntax error:"
                f" {e.text}"
            )


class OpEval(OpBaseExpression, directives=('%eval', '%stream', '%exec')):

    """Evaluate a Python expression with Python's ``eval()``.

    This operation receives special treatment in ``compile()``, but its
    subclassers do not. When parsing the input expressions, anything not
    associated with a directive is assumed to be a generic Python expression
    that should be handled by this class.

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

    def __call__(self, stream):

        # Compile the expression before doing anything else. If 'stream' is
        # empty then some of the code below doesn't execute. Unfortunately
        # this can only happen at runtime since this operation handles both
        # 'exec()' and 'eval()'.
        if self.directive == '%exec':
            mode = 'exec'
        else:
            mode = 'eval'
        compiled_expression = self.compiled_expression(mode)

        if self.directive == '%stream':

            # This method can receive any object, but convert it to an iterator
            # to provide consistency before passing to the expression.
            stream = (i for i in stream)

            yield from builtins.eval(
                compiled_expression,
                self.scope,
                {self.stream_variable: stream}
            )

        elif self.directive == '%eval':

            for item in stream:
                yield builtins.eval(
                    compiled_expression,
                    self.scope,
                    {self.variable: item}
                )

        elif self.directive == '%exec':

            # Unlike 'eval()', 'exec()' executes statements, meaning that it
            # updates the scope in place. The current item must be extracted
            # from the scope after calling 'exec()'. BUT! It is possible for
            # 'exec()' to delete the variable, so we cannot assume it
            # exists in the local scope later. Possibly supporting this
            # behavior is bad, and we should instead produce an error if this
            # happens.

            local_scope = {}
            for item in stream:

                local_scope[self.variable] = item
                builtins.exec(
                    compiled_expression,
                    self.scope,
                    local_scope
                )

                # It is possible to 'del variable'!
                if self.variable in local_scope:
                    yield local_scope[self.variable]

        else:  # pragma no cover
            raise DirectiveError(self.directive)


class OpEvalIf(OpBaseExpression, directives=('%evalif', '%execif')):

    """Like ``OpEval()``, but for optionally executing an expression.

    Does not filter. If the sentinel expression evaluates as ``False``, the
    item is emitted without evaluating the expression.
    """

    def __init__(
            self,
            directive: str,
            sentinel_expression: str,
            expression: str,
            /,
            variable,
            stream_variable,
            scope
    ):

        """See base class for most parameters.

        :param str sentinel_expression:
            Determines if ``expression`` should be evaluated.
        """

        super().__init__(
            directive,
            expression,
            variable=variable,
            stream_variable=stream_variable,
            scope=scope
        )

        self.sentinel_expression = sentinel_expression

    def __call__(self, stream):

        selection, stream = it.tee(stream, 2)

        selector = OpEval(
            '%eval',
            self.sentinel_expression,
            variable=self.variable,
            stream_variable=self.stream_variable,
            scope=self.scope
        )

        evaluator = OpEval(
            self.directive[:-2],
            self.expression,
            variable=self.variable,
            stream_variable=self.stream_variable,
            scope=self.scope
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


class OpFilter(OpBaseExpression, directives=('%filter', '%filterfalse')):

    """Filter data based on a Python expression.

    These are equivalent:

      %filter "i > 2"
      %filterfalse "i <= 2"
    """

    def __call__(self, stream):

        # Can't just use 'filter()' and 'it.filterfalse()' directly since we
        # have to evaluate a Python expression somewhere. Instead, fork the
        # stream and use one copy for evaluating expressions, and one copy
        # for values to emit.

        is_none = self.expression.lower() == 'none'

        # Just use 'filter()'. Hard to express as interactions with the
        # parent 'OpEval()' class.
        if is_none and self.directive == '%filter':
            return filter(None, stream)

        # Just use 'itertools.filterfalse()'. Hard to express as interactions
        # with the parent 'OpEval()' class.
        elif is_none and self.directive == '%filterfalse':
            return it.filterfalse(None, stream)

        # Implement via 'itertools.compress()'. Equivalent to:
        #   filter(lambda i: <expression>, stream)
        # which is extremely hard to structure. Instead, just rely on Python's
        # 'truthy' checks.
        elif self.directive in ('%filter', '%filterfalse'):

            stream, selection = it.tee(stream, 2)

            selection = (
                builtins.eval(
                    self.compiled_expression('eval'),
                    self.scope,
                    {self.variable: item}
                )
                for item in selection
            )
            if self.directive == '%filterfalse':
                selection = (not s for s in selection)

            return it.compress(stream, selection)

        else:  # pragma no cover
            raise DirectiveError(self.directive)


class OpAccumulate(OpBase, directives=('%accumulate', )):

    """Accumulate the entire stream into a single object."""

    def __call__(self, stream):

        # At first glance the simplest implemenation is:
        #   yield list(stream)
        # however, if 'stream' is empty this is equivalent to:
        #   yield []
        # which converts the contents of 'stream' into a single empty list.
        stream = list(stream)
        if stream:
            yield stream


class OpChain(OpBase, directives=('%chain', )):

    """Flatten the stream by one level – like ``itertools.chain()``."""

    def __call__(self, stream):

        return it.chain.from_iterable(stream)


class OpJSON(OpBase, directives=('%json', )):

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


class OpCSVDict(OpBase, directives=('%csvd', )):

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


class OpReversed(OpBase, directives=('%rev', '%revstream')):

    """Reverse item/stream."""

    def __call__(self, stream):

        # Python's 'reversed()' is kind of weird, and seems to only work well
        # when the object is immediately iterated over. So, to be more helpful,
        # we have some very extra special handling here.

        # Reverse each item
        if self.directive in ('%rev', '%reversed'):

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

        # Reverse entire stream
        elif self.directive in ('%revstream', '%reversedstream'):

            # Popping items off of the queue avoids having two copies of the
            # input data in-memory.
            stream = deque(stream)
            while stream:
                yield stream.pop()

        else:  # pragma no cover
            raise DirectiveError(self.directive)


class OpBatched(OpBase, directives=('%batched', )):

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


class OpStrNoArgs(OpBase, directives=(
        '%split', '%lower', '%upper', '%strip', '%lstrip', '%rstrip')):

    """Text processing that doesn't require an argument.

    Implements several directives mapping directly to ``str`` methods.
    """

    def __call__(self, stream):

        return map(op.methodcaller(self.directive[1:]), stream)


class OpStrOneArg(OpBase, directives=(
        '%join', '%splits',
        '%partition', '%rpartition',
        '%strips', '%lstrips', '%rstrips')):

    # Possibly differentiating between things like '%strip' and '%strips' is
    # too much, and instead we should just have '%strip string'?

    """Like ``OpStrNoArgs()`` but for methods requiring one argument.

    Directives map directly to ``str`` methods. Note that some of these
    directives are very similar to those implemented by ``OpStrNoArgs()``,
    but without a default value.
    """

    def __init__(self, directive: str, argument: str, /, **kwargs):

        """
        :param str directive:
            Working with this directive.
        :param str argument:
            For ``str`` method.
        :param **kwargs kwargs:
            For parent implementation.
        """

        super().__init__(directive, **kwargs)

        self.argument = argument

    def __call__(self, stream):

        mapping = {
            '%strips': 'strip',
            '%lstrips': 'lstrip',
            '%rstrips': 'rstrip',
            '%splits': 'split',
            '%lsplits': 'lsplit',
            '%rsplits': 'rsplit',
        }

        method_name = mapping.get(self.directive, self.directive[1:])

        if method_name == 'join':
            return map(self.argument.join, stream)

        else:
            func = op.methodcaller(method_name, self.argument)
            return map(func, stream)


class OpReplace(OpBase, directives=('%replace', )):

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


class OpCast(OpBase, directives=(
        '%bool', '%dict', '%float', '%int', '%list', '%set', '%str', '%tuple')):

    """Cast to a builtin Python type."""

    def __call__(self, stream):
        func = getattr(builtins, self.directive[1:])
        return map(func, stream)


class OpISlice(OpBase, directives=('%islice', )):

    """Take at most the first N items from the stream."""

    def __init__(self, directive: str, count: int, /, **kwargs):
        super().__init__(directive, **kwargs)
        self.count = count

    def __call__(self, stream):
        return it.islice(stream, self.count)


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
        type=argparse.FileType('r'),
        default='-',
        help="Read input from this file. Use '-' for stdin (the default)."
    )

    aparser.add_argument(
        '-o', '--outfile',
        metavar='PATH',
        type=argparse.FileType('w'),
        default='-',
        help="Write to this file. Use '-' for stdout (the default)."
    )
    aparser.add_argument(
        '--linesep',
        metavar='string',
        default=os.linesep,
        help=f"Write this after every line. Defaults to: {repr(os.linesep)}."
    )
    aparser.add_argument(
        '-s', '--setup', action='append', metavar='EXPR',
        help="Execute one or more Python statements to pre-initialize objects,"
             " import objects with new names, etc."
    )
    aparser.add_argument(
        '--variable',
        metavar='EXPR',
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
            try:
                code = builtins.compile(statement, '<string>', 'exec')
            except SyntaxError as e:
                raise SyntaxError(
                    f"setup statement contains a syntax error:"
                    f" {e.text.strip()}"
                )
            exec(code, scope, local_scope)
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

    args = argparse_parser().parse_args(args=rawargs)

    try:
        exit_code = main(**vars(args))

    # User interrupted with '^C' most likely, but technically this is just
    # a SIGINT. Somehow this shows up in the coverage report generated by
    # '$ pytest --cov'. No idea how that works!!
    except KeyboardInterrupt:
        print()  # Don't get a trailing newline otherwise
        exit_code = 128 + signal.SIGINT

    except Exception as e:

        exit_code = 1

        # A 'RuntimeError()' indicates a problem that should have been caught
        # during testing. We want a full traceback in these cases.
        if 'PYIN_FULL_TB' in os.environ or isinstance(e, RuntimeError):
            message = ''.join(traceback.format_exc()).rstrip()
        else:
            message = f"ERROR: {str(e)}"

        print(message, file=sys.stderr)

    # If the input and/or file points to a file descriptor and is not 'stdin',
    # close it. Avoids a Python warning about an unclosed resource.
    for attr in ('infile', 'outfile'):
        f = getattr(args, attr)
        try:
            fileno = getattr(f, 'fileno', lambda: None)()
        except io.UnsupportedOperation:
            continue

        if fileno not in (None, 0, 1, 2):
            f.close()

    exit(exit_code)


if __name__ == '__main__':
    _cli_entrypoint()  # pragma no cover

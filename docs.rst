####
pyin
####

Like `sed <https://www.gnu.org/software/sed/>`_, but Python!

A personal project.

.. warning::

    This project makes heavy use of Python's builtin `eval() <https://docs.python.org/3/library/functions.html#eval>`_
    function, and comes with same set of security considerations. Mostly this
    means only executing trusted strings, but be sure to read the relevant
    Python documentation.

.. contents::
    :depth: 3

Command-Line Interface
======================

The primary interface to ``pyin`` is the ``$ pyin`` command-line utility. It
seeks to provide shorthand for the little scripts we developers write when
quickly transforming small amounts of data. It can be quite flexible and
powerful, but at a certain point the expressions become difficult to read and
edit.

Quoting
-------

Some (most? all?) shells (posix?) disable variable expansion inside of single
quotes. Keep this in mind when writing expressions.

Introduction
------------

This Python snippet:

.. code:: python

    >>> import itertools as it
    >>> with open('LICENSE.txt') as f:
    ...     line = next(f)
    >>> line = line.strip()
    >>> line = line.lower()
    >>> line.count('n')
    2

is equivalent to:

.. code::

    $ head -1 LICENSE.txt | pyin 'i.lower()' 'i.count("n")'
    2

Generating Data
---------------

``$ pyin`` is primarily designed to read data from ``stdin`` or a file,
however in some cases it is necessary to generate your own data:

.. code::

    $ pyin --gen 'range(3)'
    0
    1
    2

The ``--gen`` flag's only requirement is that it produce an iterable object:

.. code::

    $ pyin --gen '{"key": "value"}'
    key

Directives
----------

A ``directive`` is a special shorthand for a pre-defined operation. All
directives start with the ``%`` character. Directives are split into two
categores: `Item Directives`_ and `Stream Directives`_. The former modifies
each item in the ``stream``, and the latter has the ability to completely
change the ``stream`` itself. For example, `%json`_ is an
`Item Directive <Item Directives>`_, and `%csvd`_ is a
`Stream Directive <Stream Directives>`_.

A ``directive`` takes the place of a Python expression:

.. code::

    $ echo '[1, 2, 3]' | pyin %json 'sum(i)'
    6

In some cases a ``directive`` has different behavior depending on what is
passed to it. In this example the first `%json`_ call is decoding JSON data to
a Python object, and the second is encoding:

.. code::

    $ echo '[1, 2, 3]' | pyin %json %json
    [1, 2, 3]

A list of all directives and their use appears later in this document.

Modifying the Stream
--------------------

Expressions are typically executed against each element in the stream, but it
is also possible to modify the underlying data stream directly:

.. code:

    $ pyin --gen 'range(3)' %stream '[[i ** 2] * 2 for i in s]'
    [0, 0]
    [1, 1]
    [4, 4]

Importing Objects
-----------------

All Python expressions are parsed for importable objects and automatically
imported:

.. code::

    $ echo 'LICENSE.txt' | pyin 'os.path.exists(i)'
    True

An expression containing a reference to an invalid object will fail to execute:

.. code::

    $ echo 'LICENSE.txt' | pyin 'os.path.ex(i)'
    ERROR: module 'posixpath' has no attribute 'ex'

Complex Example
---------------

A more complex example mixing directives, expressions, etc.:

.. code::

    $ head -4 LICENSE.txt \
      | pyin \
        %filter i \
        'i.split()' \
        'i[::2]' \
        %stream '[" ".join(i) for i in s]'
    New License
    Copyright 2015-2023, D.
    All reserved.

is equivalent to the Python code:

.. code::

    >>> import itertools as it
    >>> with open('LICENSE.txt') as f:
    ...     # Take first 4 lines
    ...     for i in it.islice(f, 4):
    ...         # Remove lines only containing whitespace
    ...         i = i.strip()
    ...         if not i:
    ...             continue
    ...         # Take every-other word
    ...         i = i.split()
    ...         i = i[::2]
    ...         print(" ".join(i))
    New License
    Copyright 2015-2023, D.
    All reserved.

Scope
-----

``pyin`` makes use of Python's builtin ``eval()``, which executes code within
a ``scope`` with ``local`` and ``global`` variables. ``pyin`` only places the
data being evaluated within the ``local`` variables, but provides a full
``global`` scope containing all of the normal Python builtins plus some aliases
to potentially useful modules and functions. This scope is somewhat hidden
but can be investigated:

.. code::

    $ pyin \
        --gen 'range(1)' \
        %stream '_scope.items()' \
        %filterfalse 'i[0].startswith("_")' \
        'f"{i[0]} {type(i[1])} {i[1].__name__}"'
    it <class 'module'> itertools
    op <class 'module'> operator
    reduce <class 'builtin_function_or_method'> reduce

This is admittedly very hard to read, but rebuilding the command one expression
at a time should reveal what is happening.

Directives
==========

A ``directive`` is a special operation that may or may not be possible to
express as a Python expression. The ``%json`` directive is an example of one
that is easy to re-implement, and the ``%csv`` directive is one that would be
extremely difficult.

Some directives require one or more arguments. They are noted as:

::

  %directive argument

and are described below each notation.

Text Directives
---------------

``%join``
^^^^^^^^^

::

  %join string

Equivalent to:

::

  '<string>.join(i)'

``%lower``
^^^^^^^^^^

Equivalent to:

::

  'i.lower()'

``%lstrip``
^^^^^^^^^^^

Equivalent to:

::

  'i.strip()'

See also `%lstrips`_.

``%lstrips``
^^^^^^^^^^^^

::

  %lstrips string

Equivalent to:

::

  'i.lstrip(<string>)'

See also `%lstrip`_.

``%partition``
^^^^^^^^^^^^^^

::

  %partition string

Equivalent to:

::

  'i.partition(<string>)'

``%replace``
^^^^^^^^^^^^

::

  %replace old new

Equivalent to:

::

  'i.replace(<old>, <new>)'

``%rpartition``
^^^^^^^^^^^^^^^

::

  %rpartition string

Equivalent to:

::

  'i.rpartition(<string>)'

``%rstrip``
^^^^^^^^^^^

Equivalent to:

::

  'i.rstrip()'

See also `%rstrips`_.

``%rstrips``
^^^^^^^^^^^^

::

  %rstrips string

Equivalent to:

::

  'i.rstrip(<string>)'

See also `%rstrip`_.

``%split``
^^^^^^^^^^

Equivalent to:

::

  'i.split()'

See also `%splits`_.

``%splits``
^^^^^^^^^^^

::

  %splits string

Equivalent to:

::

  'i.split(<string>)'

See also `%split`_.

``%strip``
^^^^^^^^^^

Equivalent to:

::

  'i.strip()'

``%strips``
^^^^^^^^^^^

::

  %strips string

Equivalent to:

::

  'i.strip(<string>)'

See also `%strip`_.

``%upper``
^^^^^^^^^^

Equivalent to:

::

  'i.upper()'

Item Directives
---------------

``%eval``
^^^^^^^^^

::

  %eval <expression>

Mostly users do not need to be aware of this directive. Internally, ``pyin``
assumes that any expression not associated with a ``directive`` belongs to
``%eval``. In code terms, these are equivalent:

::

  'i + 1'
  %eval 'i + 1'

``%rev``
^^^^^^^^

In theory this is equivalent to ``"reversed(i)"``, but in practice often
equivalent to ``"i[::-1]"``. Calling ``reversed()`` on a string produces a
``reversed object``, but reversing a string with slicing like ``string[::-1]``
does produce a string. Same for lists and tuples. ``pyin`` know about a few
of these special cases and attempts to preserve type. It will sometimes be
wrong.

Stream Directives
-----------------

``%accumulate``
^^^^^^^^^^^^^^^

Accumulate all elements in the stream into a single iterable object. Equivalent
to ``%stream '[list(s)]'``.

``%batched N``
^^^^^^^^^^^^^^

::

  %stream 'itertools.batched(s, N)'

For Python 3.12 onward, this is equivalent to
``%stream 'itertools.batched(s, <N>)'``. For older versions of Python:

.. code::

    >>> from itertools import islice
    >>> def batched(stream, N):
    ...     stream = iter(stream)
    ...     while chunk := tuple(it.islice(stream, N)):
    ...         yield tuple(chunk)
    >>> result = batched(range(5), 2)
    >>> print(list(result))
    [(0, 1), (2, 3), (4,)]

``%chain``
^^^^^^^^^^

Equivalent to:

::

  %stream 'itertools.chain(s)'

``%csvd``
^^^^^^^^^

Encode/decode a CSV. If the input is a stream it is read with
``csv.DictReader()`` in a manner that is equivalent to:
``%stream 'csv.DictReader(s)'``.

If the input data is a dictionary, first a header row is written with all
fields, and then all records are written with ``csv.QUOTE_ALL``. It is not
feasible to recreate this behavior with an expression.

``%filter``
^^^^^^^^^^^

::

  %filter <expression>

Include items matching the expression. Equivalent to:

::

  %stream 'filter(<expression>, s)'

``%filterfalse``
^^^^^^^^^^^^^^^^

::

  %filterfalse <expression>

Exclude items matching the expression. Equivalent to:

::

  %stream 'itertools.filterfalse(<expression>, s)'

``%json``
^^^^^^^^^

Encode and decode JSON data. If the input is a string, this is equivalent to:

::

  'json.loads(i)'

otherwise:

::

  'json.dumps(i)'

``%revstream``
^^^^^^^^^^^^^^

Reverse the entire stream. Done in a memory efficient manner. Equivalent to
both of the snippets below. See `%rev`_ for more details.

::

  %stream 'reversed(stream)'
  %stream 's[::-1]'

``%stream``
^^^^^^^^^^^

::

  %stream <expression>

Evaluate an expression on the stream itself.

Library Reference
=================

Manual for the ``pyin`` Python library. `pyin.eval()`_ is mostly what users
should interact with.

``pyin.eval()``
---------------

Evaluate one or more Python ``expressions`` against a ``stream`` of data. This
snippet:

.. code::

    >>> import pyin
    >>> stream = range(3)
    >>> expressions = ['i + 1', '[i] * 3', '%json']
    >>> for item in pyin.eval(expressions, stream):
    ...     print(item)
    [1, 1, 1]
    [2, 2, 2]
    [3, 3, 3]

is equivalent to:

.. code::

    $ pyin --gen 'range(3)' 'i + 1' '[i] * 3' %json
    [1, 1, 1]
    [2, 2, 2]
    [3, 3, 3]

``pyin.main()``
---------------

Entrypoint to the CLI for use within Python. Does not catch all exceptions.
A compliant argument parser is available via the ``argparse_parser()``
function.

.. code::

    >>> import pyin
    >>> parser = pyin.argparse_parser()
    >>> args = parser.parse_args(['--gen', 'range(3)', 'i + 1'])
    >>> assert pyin.main(**vars(args)) == 0
    1
    2
    3

While not part of the official API, the ``_cli_entrypoint()`` function may be
worth referencing. It contains an additional layer of error handling for the
``$ pyin`` utility and exists to bridge the gap between the shell and
``main()``.

``pyin.argparse_parser()``
--------------------------

An ``argparse.ArgumentParser()`` compatible with ``main()``.

``pyin.compile()``
------------------

Parses expressions and constructs the ``operation`` objects necessary to
execute them. Users should not need to interact with this function.

``pyin.importer()``
-------------------

Parses expressions and attempts to import the objects they reference into a
single global scope. Users should not need to interact with this function.

``pyin.OpBase()``
-----------------

Base class for implementing an ``operation``. One ``operation`` implements one
or more ``directives``. See section below on `Implementing an Operation`_.

Implementing an Operation
=========================

An ``operation`` is a single class containing the code implementing one or more
``directives``. Each ``operation`` class can implement multiple ``directives``.

In theory this is pluggable...

Naming a Directive
------------------

A directive should ideally map directly to a Python function or common shell
utility. For example, the ``%rev`` directive is identical to the ``$ rev``
utility. ``%reversed`` would also be an acceptable name, but is probably too
long. However, directives should have one name and one name only - it is not
OK to register both ``%rev`` and ``%reversed`` and use one as an alias for
the other. Stick with the Zen of Python:

.. code::

    $ python -m this | grep "There should be one"
    There should be one-- and preferably only one --obvious way to do it.

Subclassing `pyin.OpBase()`_
----------------------------

An ``operation`` must subclass ``pyin.OpBase()`` and implement at least the
``__call__()`` method. The ``operation`` lists which ``directives`` it
supports, at call time knows which ``directive`` it is executing, and receives
a global scope to execute within. See the ``pyin.OpBase()`` class's source
code for more information. ``pyin.OpEval()`` and ``pyin.OpJSON()`` are also
good references.

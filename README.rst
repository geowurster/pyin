====
pyin
====

It's like sed, but Python!

.. image:: https://travis-ci.org/geowurster/pyin.svg?branch=master
    :target: https://travis-ci.org/geowurster/pyin

.. image:: https://coveralls.io/repos/geowurster/pyin/badge.svg?branch=master
    :target: https://coveralls.io/r/geowurster/pyin?branch=master


Why?
====

There are plenty of Unix tools, like ``sed`` and ``awk`` for processing text
data from stdin or a file on disk, but the syntax can be unfriendly and
sometimes its just easier to write a really simple script with a for loop
and some if statements.  This project seeks to drop you in the middle of that
for loop and let you write your own Python expressions to quickly get the job
done without actually writing a script, handle I/O, etc.


Command Line Interface
======================

This project is intended to be used from the included utility ``pyin``, although
the underlying ``pyin.core.pmap()`` function could be used elsewhere with
non-string objects.

.. code-block:: console

    $ pyin --help
    Usage: pyin [OPTIONS] EXPRESSIONS...

      It's like sed, but Python!

      Map Python expressions across lines of text.  If an expression evaluates as
      'False' or 'None' then the current line is thrown away.  If an expression
      evaluates as 'True' then the next expression is evaluated.  If a list or
      dictionary is encountered it is JSON encoded.  All other objects are cast
      to string.

      Newline characters are stripped from the end of each line before processing
      and are added on write unless disabled with '--no-newline'.

      This utility employs 'eval()' internally but uses a limited scope to help
      prevent accidental side effects, but there are plenty of ways to get around
      this so don't pass anything through pyin that you wouldn't pass through
      'eval()'.

      Remove lines that do not contain a specific word:

          $ cat INFILE | pyin "'word' in line"

      Capitalize lines containing a specific word:

          $ cat INFILE | pyin "line.upper() if 'word' in line else line"

      Only print every other word from lines that contain a specific word:

          $ cat INFILE | pyin "'word' in line" "' '.join(line[::2])"

      For a more in-depth explanation about exactly what's going on under the
      hood, see the the docstring in 'pyin.core.pmap()':

          $ python -c "help('pin.core.pmap')"

    Options:
      --version           Show the version and exit.
      -i, --infile PATH   Input text file. [default: stdin]
      -o, --outfile PATH  Output text file. [default: stdout]
      --no-newline        Don't ensure each line ends with a newline character.
      --help              Show this message and exit.


Installing
==========

Via pip:

.. code-block:: console

    $ pip install pyin

From master branch:

.. code-block:: console

    $ git clone https://github.com/geowurster/pyin
    $ cd pyin && python setup.py install


What about `py -x <https://github.com/Russell91/pythonpy>`_?
============================================================

Most of this project was written with very little knowledge of ``py`` and no
knowledge of ``py -x``, which serves almost exactly the same purpose.  The
primary difference between the two projects is that ``pyin`` requires I/O and
has some smarter filtering for expressions that evaluate as ``True`` or
``False``.


Developing
==========

Install:

.. code-block:: console

    $ git clone https://github.com/geowurster/pyin
    $ cd pyin
    $ virtualenv venv && source venv/bin/activate
    $ pip install -e .\[dev\]
    $ py.test tests --cov pyin --cov-report term-missing


License
=======

See ``LICENSE.txt``
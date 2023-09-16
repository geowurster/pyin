====
pyin
====

It's like sed, but Python! A personal project.


Why?
====

There are plenty of Unix tools, like ``sed`` and ``awk`` for processing text
data from stdin or a file on disk, but the syntax can be unfriendly and
sometimes its just easier to write a really simple script with a for loop
and some if statements.  This project seeks to drop you in the middle of that
``for`` loop and let you write your own Python expressions to quickly get the
job done without actually writing a script, handle I/O, etc.


Installing
==========

.. code-block:: console

    $ python3 -m pip install git+https://github.com/geowurster/pyin


What about `py -x <https://github.com/Russell91/pythonpy>`_?
============================================================

Most of this project was written with very little knowledge of ``py`` and no
knowledge of ``py -x``, which serves almost exactly the same purpose.  The
primary difference between the two projects is that ``pyin`` requires I/O and
has some smarter filtering for expressions that evaluate as ``True`` or
``False``.


Developing
==========

.. code-block:: console

    $ git clone https://github.com/geowurster/pyin
    $ cd pyin
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ (venv) pip install -e ".[dev]"
    $ (venv) pytest --cov pyin --cov-report term-missing

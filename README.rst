####
pyin
####

Like sed, but Python! A personal project.

.. contents::
    :depth: 2

Documentation
=============

See `docs.rst <docs.rst>`_.

Documentation is built with `docutils <http://www.docutils.org>`_, which is
much lighter than Sphinx, but also has far fewer directives. It does support
rendering a single reStructuredText file as a single HTMl file though. The
project provides a helpful `cheatsheet <https://docutils.sourceforge.io/docs/user/rst/cheatsheet.txt>`_.

Installing
==========

.. code:: console

    $ python3 -m pip install git+https://github.com/geowurster/pyin

Developing
==========

.. code:: console

    # Set up workspace
    $ git clone https://github.com/geowurster/pyin
    $ cd pyin
    $ python3 -m venv venv
    $ source venv/bin/activate

    # Upgrade packaging tools
    $ (venv) pip install pip setuptools --upgrade

    # Dev and test dependencies
    $ (venv) pip install -r requirements-dev.txt -e ".[test]"

    # Run tests
    $ (venv) pytest --cov pyin --cov-report term-missing

    # Optionally, 'tox' can be used to test on multiple Python versions
    $ (venv) tox

    # Lint
    $ (venv) pycodestyle
    $ (venv) pydocstyle

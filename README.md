pyin
====

[![Build Status](https://travis-ci.org/geowurster/pyin.svg?branch=master)](https://travis-ci.org/geowurster/pyin) [![Coverage Status](https://coveralls.io/repos/geowurster/pyin/badge.svg?branch=master)](https://coveralls.io/r/geowurster/pyin?branch=master)

Perform Python operations on every line read from `stdin`.  Every line is
evaluated individually and available via a variable called `line`.


Installing
----------

Via pip:

    $ pip install git+https://github.com/geowurster/pyin.git

From master branch:
    
    $ git clone https://github.com/geowurster/pyin
    $ pip install -e .


Examples
--------

Change newline character in a CSV.

    $ more sample-data/csv-with-header.csv | pyin "line.replace('\n', '\r\n')" > output.csv


Developing
----------

Install:

    $ pip install virtualenv
    $ git clone https://github.com/geowurster/pyin
    $ cd pyin
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements-dev.txt
    $ pip install -e .

Test:
    
    $ nosetests

Coverage:

    $ nosetests --with-coverage

Lint:

    $ pep8 --max-line-length=120 pyin.py

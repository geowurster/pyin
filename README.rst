====
pyin
====

It's like sed, but Python!

.. image:: https://travis-ci.org/geowurster/pyin.svg?branch=0.4
    :target: https://travis-ci.org/geowurster/pyin

.. image:: https://coveralls.io/repos/geowurster/pyin/badge.svg?branch=master
    :target: https://coveralls.io/r/geowurster/pyin?branch=master


Examples
========

See the `Cookbook <https://github.com/geowurster/pyin/blob/master/Cookbook.rst>`__ for more examples.

Change newline character in a CSV.

.. code-block:: console

    $ more sample-data/csv-with-header.csv | pyin "line.replace('\n', '\r\n')" > output.csv

Extract a BigQuery schema from an existing table and pretty print it:

.. code-block:: console
    $ bq show --format=json ${DATASET}.${TABLE} | pyin -m json -m pprint "pprint.pformat(json.loads(line)['schema']['fields'])"
    [{u'mode': u'NULLABLE', u'name': u'mmsi', u'type': u'STRING'},
    {u'mode': u'NULLABLE', u'name': u'longitude', u'type': u'FLOAT'},
    {u'mode': u'NULLABLE', u'name': u'latitude', u'type': u'FLOAT'}
    ...]

Read the first 100K lines of a CSV and write only the lines where column
'Msg type' is equal to 5.

.. code-block:: console

    $ pyin -i ${INFILE} -o ${OUTFILE} \
        --true \
        --lines 100000 \
        --reader csv.DictReader \
        --import csv \
        --import newlinejson \
        --writer newlinejson.Writer
        "line['Msg type'] == '5'"


Installing
==========

Via pip:

    $ pip install git+https://github.com/geowurster/pyin.git

From master branch:

    $ git clone https://github.com/geowurster/pyin
    $ python setup.py install


Gotchas
=======

It's easy to completely modify the line content:

.. code-block:: console

    $ pyin -i sample-data/csv-with-header.csv "'operation'"
    operationoperationoperationoperationoperationoperation

Forgetting to use ``-t`` to only get lines that evaluate as ``True``:

.. code-block:: console

    $ pyin -i LICENSE.txt "'are' in line"
    FalseFalseFalseFalseFalseFalseTrueFalseFalseFalseFalseFalseFalseFalseFalseFalseTrueFalseFalseFalseFalseFalseFalseFalseFalseFalseFalseFalse
    
    $ pyin -i LICENSE.txt "'are' in line" -t
    modification, are permitted provided that the following conditions are met:
      derived from this software without specific prior written permission.

The ``--reader-option key=val`` values are parsed to their Python type but if the user wants to
specify something like which JSON library to use for a ``newlinejson.Reader()``
instance then they must do that via the ``--statement`` option:

.. code-block:: console

    $ pyin -i ${INFILE} -o ${OUTFILE}
        --true
        --import newlinejson \
        --import ujson
        --reader newlinejson.Reader \
        --writer newlinejson.Writer \
        --statement "newlinejson.JSON = ujson" \
        "'type' in line and line['type'] is 5"


Developing
==========

Install:

.. code-block:: console

    $ git clone https://github.com/geowurster/pyin
    $ cd pyin
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements-dev.txt
    $ pip install -e .
    $ nosetests --with-coverage
    $ pep8 --max-line-length=120 pyin.py

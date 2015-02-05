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

Extract a BigQuery schema from an existing table and pretty print it:

```console
$ bq show --format=json ${DATASET}.${TABLE} | pyin -m json -m pprint "pprint.pformat(json.loads(line)['schema']['fields'])"
[{u'mode': u'NULLABLE', u'name': u'mmsi', u'type': u'STRING'},
{u'mode': u'NULLABLE', u'name': u'longitude', u'type': u'FLOAT'},
{u'mode': u'NULLABLE', u'name': u'latitude', u'type': u'FLOAT'}
...]
```

Read the first 100K lines of a CSV and write the 

head -100000 ${INFILE} | pyin -r csv.DictReader -m csv "line['Msg type'] == '5'" -n -t -l '' -w newlinejson.Writer -m newlinejson -wm writerow > ~/github/VesselInfo/Data/100K-Sample-Type5.json




Gotchas
-------

It's easy to completely modify the line content:

    $ pyin -i sample-data/csv-with-header.csv "'operation'"
    operationoperationoperationoperationoperationoperation

Forgetting to use `-t` to only get lines that evaluate as `True`:

    $ pyin -i LICENSE.txt "'are' in line"
    FalseFalseFalseFalseFalseFalseTrueFalseFalseFalseFalseFalseFalseFalseFalseFalseTrueFalseFalseFalseFalseFalseFalseFalseFalseFalseFalseFalse
    
    $ pyin -i LICENSE.txt "'are' in line" -t
    modification, are permitted provided that the following conditions are met:
      derived from this software without specific prior written permission.

Specifying JSON:

    $ -ro fieldnames='["field1","field2"]'



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

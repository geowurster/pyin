========
Cookbook
========

The ``pyin`` utility can be used for a lot of different tasks, especially when
data is read and written with specific readers and writers but just because you
can use it to do a transformation doesn't mean you should.  Keep in mind that
the intended use is for simple text transforms and filtering.  Regardless,
examples can be found below with both the Python code necessary to complete the
task and the equivalent ``pyin`` command.

Things to remember:
- ``pyin`` uses ``eval()`` and ``exec()``.  See the `README <https://github.com/geowurster/pyin/blob/master/README.rst>`__ for more information.
- Data can be piped in via ``stdin`` instead of using the ``-i`` option.
- The examples below may not work if blindly pasted into a console or interpreter.
- You really shouldn't use ``pyin`` for some of this stuff...


Copy/Paste on a Mac
~~~~~~~~~~~~~~~~~~~

First copy something to the clipboard.

.. code-block:: console

    $ pbpaste | pyin "line.upper()" | pbcopy


Extract every other word
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    import sys

    with open(infile) as f:
        for line in f:
            sys.stdout.write(' '.join(line.split()[::2]) + os.linesep)

.. code-block:: console

    $ pyin -i ${INFILE} \
        "' '.join(line.split()[::2])"


Fix incorrect linesep for platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os

    with open(infile) as f:
        sys.stdout.write(f.read().replace(bad_linesep, os.linesep))

.. code-block:: console

    $ pyin -i ${INFILE} \
        --block \
        "line.replace(${BAD_LINESEP}, os.linesep)"


Change linesep character
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    import sys

    with open(infile) as f:
        for line in f:
            sys.stdout.write(line.strip(os.linesep, new_linesep))

.. code-block:: console

    $ pyin -i ${INFILE} \
        --import os \
        "line.strip(os.linesep, ${NEW_LINESEP})"


Extract columns from a CSV
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import csv
    import sys

    fieldnames = ['field2', 'field3']
    with open(infile) as f:
        reader = csv.DictReader(f, fieldnames=fieldnames)
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
        for line in reader:
            writer.writerow(line)

.. code-block:: console

    $ FIELDNAMES='["field2","field3"]'
    $ pyin -i ${INFILE} \
        --import csv \
        --reader csv.DictReader \
        --writer csv.DictWriter \
        --write-method writerow \
        --reader-option fieldnames=${FIELDNAMES} \
        --writer-option fieldnames=${FIELDNAMES} \
        --writer-option extrasaction=ignore \
        line


Convert a CSV to newline delimited JSON and extract a field subset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import csv
    import json

    with open(infile) as f:
        for line in csv.DictReader(f)
            sys.stdout.write(json.dumps({k: v for k,v in line.items() if k in ['field2', 'field3']}))

.. code-block:: console

    $ pyin -i ${INFILE} \
        --import csv \
        --import json \
        --reader csv.DictReader \
        "json.dumps(json.dumps({k: v for k,v in line.items() if k in ['field2', 'field3']})"


Only write lines containing a specific word
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    with open(infile) as f:
        for line in f:
            if 'word' in line:
                sys.stdout.write(line)

.. code-block:: console

    $ pyin -i ${INFILE} -o ${OUTFILE} \
        --write-true \
        "'word' in line"


Only write lines containing a specific word but also capitalize them
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    with open(infile) as f:
        for line in f:
            if 'word' in line:
                sys.stdout.write(line.upper())

.. code-block:: console

    $ pyin -i ${INFILE} -o ${OUTFILE} \
        --write-true \
        --on-true "line.upper()" \
        "'word' in line"


Extract newline JSON field subset and rename fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    import newlinejson

    from <module> import FIELD_MAP

    with open(infile) as i_f, open(outfile, 'w') as o_f:
        writer = newlinejson.Writer(o_f)
        for line in newlinejson.Reader(i_f):
            writer.write({FIELD_MAP[f]: line[f] for f in FIELD_MAP})

.. code-block:: console

    $ pyin -i ${INFILE} -o ${OUTFILE} \
          --import field_map=<module>.FIELD_MAP \
          --import newlinejson \
          --reader newlinejson.Reader \
          --writer newlinejson.Writer \
           "{field_map[key]: val for key, val in line.items() if key in field_map}"

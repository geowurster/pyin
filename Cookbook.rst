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
- ``pyin`` uses ``eval()`` and ``exec()``.  See the ``README`` for more information.
- The ``-i ${INFILE}`` option can be replaced with ``cat ${INFILE} | pyin``.
- ``pbcopy`` and ``pbpaste``on a Mac can be pretty powerful when combined with pipe.
- The examples below may not work if blindly pasted into a console or interpreter.
- You really shouldn't use ``pyin`` for some of this stuff...


Extract every other word
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    import sys

    with open(infile) as f:
        for line in f:
            sys.stdout.write(' '.join(line.split()[::2]) + os.linesep)

.. code-block:: console

    $ pyin -i ${INFILE} "' '.join(line.split()[::2])"


Fix incorrect linesep for platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os

    with open(infile) as f:
        sys.stdout.write(f.read().replace(bad_linesep, os.linesep))

.. code-block:: console

    $ pyin -i ${INFILE} --block "line.replace(${BAD_LINESEP}, os.linesep)"


Change linesep character
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    import sys

    with open(infile) as f:
        for line in f:
            sys.stdout.write(line.strip(os.linesep, new_linesep))

.. code-block:: console

    $ pyin -i ${INFILE} --import os "line.strip(os.linesep, ${NEW_LINESEP})"


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
        --reader csv.DictReader
        --writer csv.DictWriter
        --write-method writerow
        --reader-option fieldnames=${FIELDNAMES}
        --writer-option fieldnames=${FIELDNAMES}
        --writer-option extrasaction=ignore
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
        --import csv
        --import json
        --reader csv.DictReader
        "json.dumps(json.dumps({k: v for k,v in line.items() if k in ['field2', 'field3']})"


Only write lines containing a specific word
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    with open(infile) as f:
        for line in f:
            if 'word' in line:
                sys.stdout.write(line)

.. code-block:: console

    $ pyin -i ${INFILE} --write-true "'word' in line"


Only write lines containing a specific word but also capitalize them
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    with open(infile) as f:
        for line in f:
            if 'word' in line:
                sys.stdout.write(line.upper())

.. code-block:: console

    $ pyin -i ${INFILE} --write-true "'word' in line" --on-true "line.upper()"


Change Newline Delimited JSON Field Names
-----------------------------------------

Example fieldmap:

```json
{
  "field1": "FIELD1",
  "field2": "something-else"
}
```

Command:

``` console
$ pyin -i newline.json \
      -im module.FIELD_MAP \
      -im newlinejson \
      -r newlinejson.Reader \
      -w newlinejson.Writer \
       "{module.FIELD_MAP[key]: val for key, val in line.iteritems() if key in module.FIELD_MAP}"
```

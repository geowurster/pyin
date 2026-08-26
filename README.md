# pyin

Like sed, but Python! A personal project.

## Documentation

See [docs.rst](docs.rst).

Documentation is built with [`docutils`](http://www.docutils.org), which is  much lighter than Sphinx, but also has far fewer directives. It does support rendering a single reStructuredText file as a single HTMl file though. The project provides a helpful [cheatsheet](https://docutils.sourceforge.io/docs/user/rst/cheatsheet.txt).

## Installing

```
python3 -m pip install git+https://github.com/geowurster/pyin
```

## Developing

1. Clone the repository, and change into its directory.
2. Create and activate a virtual environment.

Install:

```
python3 -m pip install pip install -e '.[test]'
```

Run the tests with:

```
pytest --cov pyin --cov-report term-missing --cov-fail-under 100
```

`tox` can be used to run against other Python versions:

```
python3 -m pip install tox
tox
```

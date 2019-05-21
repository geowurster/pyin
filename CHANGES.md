Changelog
=========


Next
----

- Tested on Python 2.7, 3.5, 3.6, 3.7, and nightly build.  Set appropriate classifiers.
- [PEP 440](https://www.python.org/dev/peps/pep-0440/)
- Test on all supported versions of [`click`](https://github.com/pallets/click).
- Compile expressions to bytecode prior to executing for a performance boost.

0.5.4 (2015-08-03)
------------------

- Small documentation improvements


0.5.3 (2015-08-03)
------------------

- Added `--block` flag to process all input text as a single unit - #36


0.5.2 (2015-08-03)
------------------

- Actually fixed a critical packaging bug


0.5.1 (2015-08-03)
------------------

- Fixed a critical packaging bug


0.5 (2015-08-02)
----------------

- Removed support for external readers and writers - #30
- Added ability to chain multiple expressions together - # 19
- External modules are automatically imported
- Streamlined UI

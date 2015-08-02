#!/usr/bin/env python


"""
Setup script for pyin
"""


import os

import setuptools


with open('README.rst') as f:
    readme_content = f.read().strip()


version = None
author = None
email = None
source = None
with open(os.path.join('pyin', '__init__.py')) as f:
    for line in f:
        if line.strip().startswith('__version__'):
            version = line.split('=')[1].strip().replace('"', '').replace("'", '')
        elif line.strip().startswith('__author__'):
            author = line.split('=')[1].strip().replace('"', '').replace("'", '')
        elif line.strip().startswith('__email__'):
            email = line.split('=')[1].strip().replace('"', '').replace("'", '')
        elif line.strip().startswith('__source__'):
            source = line.split('=')[1].strip().replace('"', '').replace("'", '')
        elif None not in (version, author, email, source):
            break


setuptools.setup(
    name='pyin',
    author=author,
    author_email=email,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Text Processing :: Filters',
        'Topic :: Text Processing :: General',
        'Topic :: Utilities'
    ],
    description="basic streaming text processing",
    entry_points="""
        [console_scripts]
        pyin=pyin.cli:main
    """,
    extras_require={
        'dev': [
            'pytest',
            'pytest-cov',
            'coveralls'
        ]
    },
    include_package_data=True,
    install_requires=[
        'click>=3',
    ],
    license="MIT",
    long_description=readme_content,
    py_modules=['pyin'],
    url=source,
    version=version,
    zip_safe=True,
)

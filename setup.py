#!/usr/bin/env python


"""
Setup script for pyin
"""


import os

from setuptools import find_packages
from setuptools import setup


with open('README.rst') as f:
    readme_content = f.read().strip()


version = author = email = source = None
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
        elif all((version, author, email, source)):
            break


setup(
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
    description="It's like sed, but Python!",
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
    license="New BSD",
    long_description=readme_content,
    packages=find_packages(exclude=['tests']),
    url=source,
    version=version,
    zip_safe=True
)

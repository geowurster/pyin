#!/usr/bin/env python


"""
Setup script for pyin
"""


import setuptools

import pyin


with open('README.md') as f:
    readme = f.read().strip()

with open('requirements.txt') as f:
    install_requires = f.read().strip()


setuptools.setup(
    author=pyin.__author__,
    author_email=pyin.__email__,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Text Processing :: Filters',
        'Topic :: Text Processing :: General',
        'Topic :: Utilities'
    ],
    description="streaming text processing",
    entry_points="""
        [console_scripts]
        pyin=pyin:main
    """,
    include_package_data=True,
    install_requires=install_requires,
    license=pyin.__license__,
    long_description=readme,
    name=pyin.__name__,
    py_modules=['pyin'],
    url=pyin.__source__,
    version=pyin.__version__,
    zip_safe=True,
)

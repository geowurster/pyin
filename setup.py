#!/usr/bin/env python


"""
Setup script for str2type
"""


import setuptools


setuptools.setup(
    name='pyin',
    py_modules=['pyin'],
    zip_safe=True,
    entry_points="""
        [console_scripts]
        pyin=pyin:main
    """,
)

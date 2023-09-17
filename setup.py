#!/usr/bin/env python


"""
Setup script for pyin
"""


from setuptools import setup


with open('README.rst') as f:
    readme_content = f.read().strip()


with open('pyin.py') as f:
    for line in f:
        if '__version__' in line:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            break
    else:
        raise RuntimeError("Could not find '__version__'")


setup(
    name='pyin',
    author='Kevin Wurster',
    author_email='wursterk@gmail.com',
    classifiers=[
        'Development Status :: 7 - Inactive',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Topic :: Text Processing :: Filters',
        'Topic :: Text Processing :: General',
        'Topic :: Utilities',
    ],
    description="It's like sed, but Python!",
    entry_points="""
        [console_scripts]
        pyin=pyin:_cli_entrypoint
    """,
    extras_require={
        'test': [
            'pytest',
            'pytest-cov'
        ]
    },
    include_package_data=True,
    license="New BSD",
    long_description=readme_content,
    py_modules=["pyin"],
    python_requires=">=3.5",
    url='https://github.com/geowurster/pyin',
    version=version,
    zip_safe=True
)

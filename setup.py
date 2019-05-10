#!/usr/bin/env python

import os
from setuptools import setup, find_packages


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

here = os.path.dirname(os.path.abspath(__file__))
version_ns = {}
with open(os.path.join(here, 'geebap', '_version.py')) as f:
    exec(f.read(), {}, version_ns)

# the setup
setup(
    name='geebap',
    version=version_ns['__version__'],
    description='Generate a "Best Available Pixel (BAP)" composite in Google '\
                'Earth Engine (GEE)',
    # long_description=read('README'),
    url='',
    author='Rodrigo E. Principe',
    author_email='rprincipe@ciefap.org.ar',
    license='GNU',
    keywords='google earth engine raster image processing gis satelite',
    packages=find_packages(exclude=('docs', 'bap_env')),
    include_package_data=True,
    install_requires=['requests',
                      'simpleeval',
                      'numpy',
                      'geetools>=0.2.2'],
    extras_require={
    'dev': [],
    'docs': [],
    'testing': [],
    },
    classifiers=['Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'License :: OSI Approved :: MIT License',],
    )

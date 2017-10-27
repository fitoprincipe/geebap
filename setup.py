#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from BestAvailablePixel import __version__


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# the setup
setup(
    name='BestAvailablePixel',
    version="0.1",
    description='Generate a "Best Available Pixel" image in Google Earth Engine',
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
                      'numpy'],
    extras_require={
    'dev': [],
    'docs': [],
    'testing': [],
    },
    classifiers=['Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7'],
    )

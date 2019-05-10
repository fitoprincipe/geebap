# -*- coding: utf-8 -*-
"""
Package to generate a "Best Available Pixel" image in Google Earth Engine
"""

from __future__ import absolute_import, division, print_function
from ._version import __version__

__all__ = (
    "__title__", "__summary__", "__uri__", "__version__", "__author__",
    "__email__", "__license__", "__copyright__",
)

__title__ = "BestAvailablePixel"
__summary__ = "Generate a 'Best Available Pixel' image in Google Earth Engine"
__uri__ = "https://github.com/fitoprincipe/geebap"
__author__ = "Rodrigo E. Principe"
__email__ = "rprincipe@ciefap.org.ar"

__license__ = "GNU GENERAL PUBLIC LICENSE, Version 3"
__copyright__ = "Rodrigo E. Principe"

try:
    from . import bap, date, expgen, expressions, filters, functions,\
        ipytools, masks, regdec, scores, season, sites

    from .bap import Bap
    from .priority import SeasonPriority
    from .season import Season
except ImportError:
    pass
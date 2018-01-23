#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Module holding custom filters for image collections """
import ee.data
if not ee.data._initialized: ee.Initialize()

import satcol
from abc import ABCMeta, abstractmethod
from regdec import *

__all__ = []
factory = {}


class Filter(object):
    ''' Abstract Base class for filters '''
    __metaclass__ = ABCMeta
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def apply(self, colEE, **kwargs):
        pass

@register(factory)
@register_all(__all__)
class CloudsPercent(Filter):
    """ Cloud cover percentage filter

    :param percent: all values over this will be filtered. Goes from 0
        to 100
    :type percent: int
    :param kwargs:
    """
    def __init__(self, percent=70, **kwargs):
        super(CloudsPercent, self).__init__(**kwargs)
        self.percent = percent

    def apply(self, colEE, **kwargs):
        """ Apply the filter

        :param colEE: the image collection to apply the filter
        :type colEE: ee.ImageCollection
        :param col: if the collection is given, it will take the name of the
            attribute holding the 'cloud cover' information
        :type col: satcol.Collection
        :param prop: if the collection is not given, the name of the attribute
            holding the 'cloud cover' information can be given
        :type prop: str
        :param kwargs:
        :return:
        """
        col = kwargs.get("col")
        if col.clouds_fld:
            return colEE.filterMetadata(col.clouds_fld, "less_than", self.percent)
        elif kwargs.has_key('prop'):
            prop = kwargs.get('prop')
            return colEE.filterMetadata(prop, 'less_than', self.percent)
        else:
            return colEE


@register(factory)
@register_all(__all__)
class MaskPercent(Filter):
    """ This mask can only be used AFTER computing mask percentage score
    (`scores.MaskPercent`). This score writes an attribute to the image
    which contains 'mask percentage' of the given area (see score's docs).
    This filter uses this value to apply a filter. I's similar to common
    'cloud cover' filter, but takes account only the given area and not
    the whole scene.

    :param percent: all values over this will be filtered. Goes from 0 to 1
    :type percent: float
    :param prop: name of the property containing the 'mask percentage'
    :param prop: str
    :param kwargs:
    """
    def __init__(self, percent=0.7, prop="score-maskper", **kwargs):
        super(MaskPercent, self).__init__(**kwargs)
        self.percent = percent
        self.prop = prop

    def apply(self, colEE, **kwargs):
        """ Apply the filter

        :param colEE: the image collection to apply the filter
        :type colEE: ee.ImageCollection
        :return:
        """
        return colEE.filterMetadata(self.prop, "less_than", self.percent)

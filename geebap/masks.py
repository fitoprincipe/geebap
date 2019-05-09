# -*- coding: utf-8 -*-
""" Common masks to use in BAP process """
from geetools import cloud_mask

def _get_function(col, band, option, renamed=False):
    """ Get mask function for given band and option """
    band_options = col.bitOptions(renamed)
    f = lambda img: img
    if band in band_options:
        bit_options = band_options[band]
        if option in bit_options:
            f = lambda img: col.applyMask(img, band, [option],
                                           renamed=renamed)
    return f


class Mask(object):
    """ Compute common masks regarding the given collection. Looks for
    pixel_qa, BQA, sr_cloud_qa and QA60 bands in that order """
    def __init__(self, options=('cloud', 'shadow', 'snow')):
        self.options = options
        self.bands = ['pixel_qa', 'BQA', 'sr_cloud_qa', 'QA60']

    def map(self, collection, **kwargs):
        """ Map the mask function over a collection

        :param collection: the ImageCollection
        :type collection: ee.ImageCollection
        :param renamed: whether the collection is renamed or not
        :type renamed: bool
        :param col: the EE Collection
        :type col: geetools.collection.Collection
        :return: the ImageCollection with all images masked
        :rtype: ee.ImageCollection
        """
        col = kwargs.get('col')
        renamed = kwargs.get('renamed', False)
        for opt in self.options:
            for band in self.bands:
                f = _get_function(col, band, opt, renamed)
                collection = collection.map(f)

        return collection


class Hollstein(object):
    """ Compute Hollstein mask for Sentinel 2 """
    def __init__(self, options=('cloud', 'shadow', 'snow')):
        self.options = options

    def map(self, collection, **kwargs):
        """ Map the mask function over a collection

        :param collection: the ImageCollection
        :type collection: ee.ImageCollection
        :param renamed: whether the collection is renamed or not
        :type renamed: bool
        :param col: the EE Collection
        :type col: geetools.collection.Collection
        :return: the ImageCollection with all images masked
        :rtype: ee.ImageCollection
        """
        col = kwargs.get('col')
        renamed = kwargs.get('renamed', False)

        bands = []
        for band in ['aerosol', 'blue', 'green', 'red_edge_1', 'red_edge_2',
                     'red_edge_3', 'red_edge_4', 'water_vapor', 'cirrus',
                     'swir']:
            if renamed:
                bands.append(band)
            else:
                bands.append(col.get_band(band, 'name').id)

        if 'hollstein' in col.algorithms:
            f = lambda img: cloud_mask.applyHollstein(img, self.options,
                                                       *bands)
            return collection.map(f)
        else:
            return lambda img: img
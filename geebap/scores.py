# -*- coding: utf-8 -*-
"""
Module to implement scores in the Bap Image Composition.

Scores can be computed using a single image, for example a score for percentage
of masked pixels, or using a collection, for example a score for outliers.

Each score must have an `apply` method which first argument must be an
ImageCollection and must return the collection with score computed in each
image. This method should be an staticmethod and not depend on any external
library except Earth Engine API.

Each score must have an `compute` method which first argument must be an Image
and return the resulting score as an Image with one band. This method should be
an staticmethod and not depend on any external library except Earth Engine API.

If the `compute` method is borrowed from another package it can be passed by
overwriting it. It should be use only internally by `apply` method, and `apply`
method should be the only one used by the BAP process.

The `map` method is designed to be used in the BAP method only, it takes an
ImageCollections as first argument and can use the following keyword arguments
(kwargs):

- col: a satcol.Collection object instance
- year: the given year
- geom: a geometry
- any other keyword argument

"""
import ee

from . import priority
from . import season as season_module
from geetools import tools, composite

from .expressions import Expression
from abc import ABCMeta, abstractmethod
from .regdec import *

from uuid import uuid4

__all__ = []
factory = {}

KERNELS_DISTANCE = {
    "euclidean": ee.Kernel.euclidean,
    "manhattan": ee.Kernel.manhattan,
    "chebyshev": ee.Kernel.chebyshev
}

KERNELS_BOOL = {
    "circle": ee.Kernel.circle,
    "cross": ee.Kernel.cross,
    "diamond": ee.Kernel.diamond,
    "octagon": ee.Kernel.octagon,
    "plus": ee.Kernel.plus,
    "square": ee.Kernel.square
}


class Score(object):
    ''' Abstract Base class for scores '''
    __metaclass__ = ABCMeta

    def __init__(self, name="score", range_in=None, range_out=(0, 1), sleep=0,
                 **kwargs):
        """ Abstract Base Class for scores

        :param name: score's name
        :type name: str
        :param range_in: score's range
        :type range_in: tuple
        :param sleep: time to wait until to compute the next score
        :type sleep: int
        :param formula: formula to use for computing the score
        :type formula: Expression
        :param range_out: Adjust the output to this range
        :type range_out: tuple
        """
        self.name = name
        self.range_in = range_in
        self.range_out = range_out
        self.sleep = sleep
        self._normalize = True

    @property
    def normalize(self):
        return self._normalize

    @normalize.setter
    def normalize(self, value):
         self._normalize = value

    @property
    def max(self):
        return self.range_out[1]

    @property
    def min(self):
        return self.range_out[0]

    def adjust(self):
        if self.range_out != (0, 1):
            return lambda img: tools.image.parametrize(img, (0, 1),
                                                       self.range_out,
                                                       [self.name])
        else:
            return lambda x: x

    @abstractmethod
    def map(self, collection, **kwargs):
        """ Abstract map method to use in ImageCollection.map() """
        return collection

    @staticmethod
    def compute(img, **kwargs):
        """ Compute method. This method is supposed to be the one to
        compute the score
        """
        def wrap(img):
            return img
        return wrap

    @staticmethod
    def apply(collection, **kwargs):
        return collection

    def empty(self, img):
        """ Make an empty score band. All pixels will have zero value """
        i = ee.Image.constant(0).select([0], [self.name]).toFloat()
        return img.addBands(i)

    def _map(self, collection, **kwargs):
        """ Internal map function for applying adjust """
        newcollection = self.map(collection, **kwargs)

        return newcollection.map(self.adjust())


@register(factory)
@register_all(__all__)
class CloudScene(Score):
    """ Cloud cover percent score for the whole scene. Default name for the
    resulting band will be 'score-cld-esc'.

    :param name: name of the resulting band
    :type name: str
    """
    def __init__(self, name="score-cld-scene", **kwargs):
        super(CloudScene, self).__init__(**kwargs)
        self.range_in = (0, 100)
        self.name = name

        self.formula = Expression.Exponential(rango=self.range_in,
                                              normalizar=self.normalize,
                                              **kwargs)

    @staticmethod
    def compute(img, **kwargs):
        formula = kwargs.get('formula')
        fmap = kwargs.get('fmap')
        name = kwargs.get('name')
        cloud_cover = kwargs.get('cloud_cover')

        func = formula.map(name, prop=cloud_cover, map=fmap)
        return func(img)

    @staticmethod
    def apply(collection, **kwargs):
        return collection.map(lambda img: CloudScene.compute(img, **kwargs))

    def map(self, collection, **kwargs):
        """ Map function to use in BAP

        :param col: collection
        :type col: satcol.Collection
        """
        col = kwargs.get('col')

        if col.cloud_cover:
            return collection.map(
                lambda img: self.compute(img, cloud_cover=col.cloud_cover))
        else:
            return collection.map(self.empty)


@register(factory)
@register_all(__all__)
class CloudDist(Score):
    """ Score for the distance to the nearest cloud. Default name will be
    'score-cld-dist'

    :param unit: Unit to use in the distance kernel. Options: meters,
        pixels
    :type unit: str
    :param dmax: Maximum distance to calculate the score. If the pixel is
        further than dmax, the score will be 1.
    :type dmax: int
    :param dmin: Minimum distance.
    :type dmin: int
    """
    def __init__(self, dmin=0, dmax=None, name="score-cld-dist", **kwargs):
        super(CloudDist, self).__init__(**kwargs)
        self.dmax = dmax
        self.dmin = dmin
        self.name = name
        self.range_in = (dmin, dmax)
        # Extra params
        self.sleep = kwargs.get("sleep", 10)
        self.kernel = kwargs.get("kernel", "euclidean")
        self.units = kwargs.get('units', 'meters')

    # GEE
    @property
    def dminEE(self):
        return ee.Image.constant(self.dmin)

    def kernelEE(self, radius):
        fkernel = KERNELS_DISTANCE[self.kernel]
        return fkernel(radius=radius, units=self.units)

    @staticmethod
    def compute(img, **kwargs):
        """ Compute Cloud Distance score.

        :param kernel: a kernel
        :type kernel: ee.Kernel
        :param dmax: Maximum distance to calculate the score. If the pixel is
            further than dmax, the score will be 1.
        :type dmax: int
        :param dmin: Minimum distance.
        :type dmin: int
        :param bandmask: the band that contains the mask. Defaults to the first
            band of the image
        :type bandmask: str
        :param bandname: the name of the resulting band. Defaults to
            'cloud_dist'
        :type bandname: str
        :param units: units for the kernel. Can be 'pixels' or 'meters'. Defaults to the latter
        :type units: str
        """
        kernel = kwargs.get('kernel')
        dmax = ee.Number(kwargs.get('dmax'))
        dmin = ee.Number(kwargs.get('dmin'))
        bandmask = kwargs.get('bandmask', 0)
        bandname = kwargs.get('bandname', 'cloud_dist')
        units = kwargs.get('units', 'meters')
        factor = kwargs.get('factor', 0.2)

        if not kernel:
            kernel = ee.Kernel.euclidean(radius=dmax, units=units)
        else:
            kernel = kernel(radius=dmax, units=units)

        cloud_mask = img.mask().select([bandmask])

        # Compute distance to the mask (inverse)
        distance = cloud_mask.Not().distance(kernel)

        # Mask out pixels that are further than d_max
        clip_max_masc = distance.lte(dmax)
        distance = distance.updateMask(clip_max_masc)

        # Mask out initial mask
        distance = distance.updateMask(cloud_mask)

        dmaxi = ee.Image(dmax)
        dmini = ee.Image(dmin)
        factori = ee.Image(factor)

        # Compute score
        pjeDist = ee.Image().expression('1-exp((-dist+dmin)/(dmax*factor))',
                                        {
                                            'dist': distance,
                                            'dmin': dmini,
                                            'dmax': dmaxi,
                                            'factor': factori
                                        }).rename(bandname)

        # Inverse mask to add later
        masc_inv = pjeDist.mask().Not()

        # apply mask2zero (all masked pixels are converted to 0)
        pjeDist = pjeDist.unmask()

        # Add the inverse mask to the distance image
        pjeDist = pjeDist.add(masc_inv)

        # Apply the original mask
        pjeDist = pjeDist.updateMask(cloud_mask)

        return pjeDist.rename(bandname)

    @staticmethod
    def apply(collection, **kwargs):
        return collection.map(lambda img: CloudDist.compute(img, **kwargs))

    def map(self, collection, **kwargs):
        """ Map function to use in BAP

        :param col: collection
        :type col: geetools.collection.Collection
        """
        col = kwargs.get('col')
        first_band = col.bands[0]
        scale = min([band.scale for band in col.bands])

        maxdist = (scale/2)*510

        # Truncate dmax if goes over the 512 pixels limit
        if self.dmax is None:
            dmax = maxdist
        elif self.dmax > maxdist and self.unit == 'meters':
            dmax = maxdist
        else:
            dmax = self.dmax

        params = dict(
            bandmask = first_band.name,
            kernel = KERNELS_DISTANCE[self.kernel],
            dmin = self.dmin,
            dmax = dmax,
            bandname = self.name,
            units = self.units
        )

        def wrap(img):
            score_img = self.compute(img, **params)

            adjusted_score = self.adjust()(score_img)
            return img.addBands(adjusted_score)

        return collection.map(wrap)


@register(factory)
@register_all(__all__)
class Doy(Score):
    """ Score for the 'Day of the Year (DOY)'

    :param best_doy: the date (MM-DD) that will be prioritized
    :type best_doy: str
    :param season: the season
    :type season: season.Season
    :param name: name for the resulting band
    :type name: str
    """
    def __init__(self, best_doy, season, name="score-best_doy",
                 function='linear', stretch=1, **kwargs):
        super(Doy, self).__init__(**kwargs)
        self.name = name
        self.function = function
        self.stretch = stretch
        self.best_doy = best_doy
        self.season = season

    def adjust(self):
        return lambda img: img

    @staticmethod
    def apply(collection, **kwargs):
        """ Apply best_doy score to every image in a collection.

        :param best_doy: day of year
        :type best_doy: ee.Date
        :param function: the function to use. Can be one of
            'linear' or 'gauss'
        :type function: str
        :return: the parsed collection with a new property called by parameter
            `name` (defaults to 'best_doy').
        :rtype: ee.ImageCollection
        """
        doy = kwargs.get('best_doy')  # ee.Date
        function = kwargs.get('function', 'linear')
        name = kwargs.get('name', 'doy_score')
        stretch = kwargs.get('stretch', 1)
        output_min = kwargs.get('output_min', 0)
        output_max = kwargs.get('output_max', 1)

        # temporary distance property name
        uid = uuid4()
        distance_name = 'distance_{}'.format(uid)

        # function to compute distance
        def distance(img):
            idate = ee.Date(img.date())
            dist = idate.difference(doy, 'day')
            return img.set(distance_name, dist)

        # compute distance to best_doy
        collection = collection.map(distance)

        if function == 'linear':
            result = tools.imagecollection.linearFunctionProperty(
                collection,
                distance_name,
                mean=0,
                output_min= output_min,
                output_max= output_max,
                name=name)

        if function == 'gauss':
            result = tools.imagecollection.gaussFunctionProperty(
                collection,
                distance_name,
                mean=0,
                output_min= output_min,
                output_max= output_max,
                stretch=stretch,
                name=name
            )

        def addBand(img):
            doyn = ee.Number(img.get(name))
            doyband = ee.Image.constant(doyn).rename(name).toFloat()
            return img.addBands(doyband)

        return result.map(addBand)

    def map(self, collection, **kwargs):
        """ Map function to use in BAP

        :param year: the analysing year. Must match the year of the bap
        :type year: int
        """
        range_out = self.range_out
        year = kwargs.get('year')
        date_range = self.season.add_year(year)
        doy = ee.Date(season_module.SeasonDate(self.best_doy).add_year(year))
        doy2 = ee.Date(season_module.SeasonDate(self.best_doy).add_year(year-1))
        condition = date_range.contains(doy)
        best = ee.Number(ee.Algorithms.If(condition, doy, doy2))

        return self.apply(collection, best_doy=best, name=self.name,
                          output_min=range_out[0], output_max=range_out[1],
                          function=self.function, stretch=self.stretch)


@register(factory)
@register_all(__all__)
class AtmosOpacity(Score):
    """ Score for 'Atmospheric Opacity'

    :param range_in: Range of variation for the atmos opacity
    :type range_in: tuple
    :param formula: Distribution formula
    :type formula: Expression
    """
    def __init__(self, range_in=(100, 300), formula=Expression.Exponential,
                 name="score-atm-op", **kwargs):
        super(AtmosOpacity, self).__init__(**kwargs)
        self.range_in = range_in
        self.formula = formula
        self.name = name

    @property
    def expr(self):
        expresion = self.formula(rango=self.range_in)
        return expresion

    def map(self, collection, **kwargs):
        """ Map the score over a collection

        :param col: collection
        :type col: satcol.Collection
        """
        col = kwargs.get('col')
        band = col.getBand('atmos_opacity', 'name')
        if band:
            f = self.expr.map(name=self.name,
                              band=band.name,
                              map=self.adjust(),
                              **kwargs)
        else:
            f = self.empty

        return collection.map(f)


@register(factory)
@register_all(__all__)
class MaskPercent(Score):
    """ This score represents the 'masked pixels cover' for a given area.
    It uses a ee.Reducer so it can consume much EE capacity

    :param band: band of the image that holds the masked pixels
    :type band: str
    :param maxPixels: same param of ee.Reducer
    :type maxPixels: int
    :param include_zero: include pixels with zero value as mask
    :type include_zero: bool
    """
    @staticmethod
    def compute(image, **kwargs):
        """ Core function for Mask Percent Score. Has no dependencies in geebap
        module

        :param image: ee.Image holding the mask
        :type image: ee.Image
        :param geometry: the score will be computed inside this geometry
        :type geometry: ee.Geometry or ee.Feature
        :param scale: the scale of the mask
        :type scale: int
        :param band_name: the name of the resulting band
        :type band_name: str
        :return: An image with one band that holds the percentage of pixels
            with value 0 (not 1) over the total pixels inside the geometry, and
            a property with the same name as the assigned for the band with the
            same percentage
        :rtype: ee.Image
        """
        geometry = kwargs.get('geometry')
        scale = kwargs.get('scale', 1000)
        band_name = kwargs.get('band_name', 'score-maskper')
        max_pixels = kwargs.get('max_pixels', 1e13)
        count_zeros = kwargs.get('count_zeros', False)

        # get band name
        band = ee.String(image.bandNames().get(0))

        # get projection
        projection = image.select([band]).projection()

        # Make an image with all ones
        ones_i = ee.Image.constant(1).reproject(projection).rename(band)

        # manage geometry types
        if isinstance(geometry, (ee.Feature, ee.FeatureCollection)):
            geometry = geometry.geometry()

        # Get total number of pixels
        ones = ones_i.reduceRegion(
            reducer= ee.Reducer.count(),
            geometry= geometry,
            scale= scale,
            maxPixels= max_pixels).get(band)
        ones = ee.Number(ones)

        # select first band, unmask and get the inverse
        mask_image = image.select([band])
        if count_zeros:
            zeros = mask_image.eq(0)
            mask_image = mask_image.updateMask(zeros.Not())

        mask = mask_image.mask()
        mask_not = mask.Not()
        image_to_compute = mask.updateMask(mask_not)

        # Get number of zeros in the given mask_image
        zeros_in_mask =  image_to_compute.reduceRegion(
            reducer= ee.Reducer.count(),
            geometry= geometry,
            scale= scale,
            maxPixels= max_pixels).get(band)
        zeros_in_mask = ee.Number(zeros_in_mask)

        percentage = tools.number.trimDecimals(zeros_in_mask.divide(ones), 4)

        # Make score inverse to percentage
        score = ee.Number(1).subtract(percentage)

        percent_image = ee.Image.constant(score) \
                          .select([0], [band_name])\
                          .set(band_name, score).toFloat()

        return percent_image.clip(geometry)

    def __init__(self, band=None, name="score-maskper", maxPixels=1e13,
                 count_zeros=False, **kwargs):
        super(MaskPercent, self).__init__(**kwargs)
        self.band = band
        self.maxPixels = maxPixels
        self.name = name
        self.count_zeros = count_zeros
        self.sleep = kwargs.get("sleep", 30)

    def map(self, collection, **kwargs):
        """ Map the score over a collection

        :param col: collection
        :type col: satcol.Collection
        :param geom: boundaries geometry
        :type geom: ee.Geometry or ee.Feature
        """
        col = kwargs.get('col')
        geom = kwargs.get('geom')
        minscale = min([band.scale for band in col.bands])
        def wrap(img):
            score = self.compute(img, geometry=geom, scale=minscale,
                                 count_zeros=self.count_zeros)
            prop = score.get(self.name)
            return img.addBands(score).set(self.name, prop)

        return collection.map(wrap)


class MaskPercentKernel(Score):
    """ Mask percent score using a kernel """
    def __init__(self, kernel='square', distance=255, units='pixels',
                 name="score-maskper-kernel", **kwargs):
        """ Initialize score with kernel, distance and units """
        super(MaskPercentKernel, self).__init__(**kwargs)

        self.kernel = kernel
        self.distance = distance
        if self.distance > 255:
            self.distance = 255

        self.units = units
        self.name = name

    @staticmethod
    def _make_kernel(name, radius, units):
        fkernel = KERNELS_BOOL[name]
        return fkernel(radius=radius, units=units)

    @staticmethod
    def compute(img, **kwargs):
        """ Compute kernel mask percent score. Uses the mask of the first band

        :param kernel: the kernel to use (the class, not instance)
        :type kernel: ee.Kernel
        :param size: the kernel size
        :type size: int
        :param: units: units for the kernel ('pixels' or 'meters')
        :type units: str
        :param name: the name of the resulting band
        :type name: str
        """
        kernel = kwargs.get('kernel', 'square')
        size = kwargs.get('size', 255)
        units = kwargs.get('units', 'pixels')
        count_zeros = kwargs.get('count_zeros', False)
        name = kwargs.get('name', 'mask-kernel')

        if units == 'pixels' and size > 255:
            size = 255

        distance = (size*2+1)**2

        Kernel = MaskPercentKernel._make_kernel(kernel, size, units)

        maskband = img.select([0])

        if count_zeros:
            mask = maskband.eq(0).Not()
            maskband = maskband.updateMask(mask)

        count = maskband.reduceNeighborhood(
            'count', Kernel).rename(maskband.bandNames())

        return count.divide(distance).rename(name)

    def map(self, collection, **kwargs):
        def wrap(img):
            score = self.compute(
                img,
                kernel=self.kernel,
                size=self.distance,
                units=self.units,
                name=self.name
            )
            return img.addBands(score)

        return collection.map(wrap)


@register(factory)
@register_all(__all__)
class Satellite(Score):
    """ Score for the satellite

    :param rate: 'amount' of the score that will be taken each step of the
        available satellite list
    :type rate: float
    """
    def __init__(self, ratio=0.05, name="score-sat", **kwargs):
        super(Satellite, self).__init__(**kwargs)
        self.name = name
        self.ratio = ratio

    @staticmethod
    def compute(image, **kwargs):
        colid = kwargs.get('collection_id') # ej: 'COPERNICUS/S2'
        year = kwargs.get('year')
        rate = kwargs.get('ratio', 0.05)
        name = kwargs.get('name', 'sat-score')

        year_str = ee.Number(year).format()
        # List of satellite priority according to year
        prior_list = ee.List(priority.SeasonPriority.ee_relation.get(year_str))

        # Get index of current satellite into the list
        index = prior_list.indexOf(colid)

        # catch if item not in list
        exists = ee.Number(index).neq(-1)

        # 1 - (0.05 * index)
        # EJ: [1, 0.95, 0.9]
        factor = ee.Number(rate).multiply(index)
        factor = ee.Number(ee.Algorithms.If(exists, factor, 1))
        sat_score = ee.Number(1).subtract(factor)

        # Create the score band
        score_img = ee.Image.constant(sat_score).rename(name).toFloat()

        # Write score as an Image Property
        score_img = score_img.set(name.upper(), sat_score)

        return score_img

    def map(self, collection, **kwargs):
        """
        :param col: Collection
        :type col: satcol.Collection
        """
        col = kwargs.get('col')
        year = kwargs.get('year')

        def wrap(img):
            y = ee.Number(year) if year else img.date().get('year')
            score = self.compute(img, collection_id=col.id, year=y,
                                 rate=self.ratio, name=self.name)
            return img.addBands(score).set(self.name, score.get(self.name))

        return collection.map(wrap)


@register(factory)
@register_all(__all__)
class Outliers(Score):
    """ Score for outliers

    Compute a pixel based score regarding to its 'outlier' condition. It
    can use more than one band.

    To see an example, run `test_outliers.py`

    :param bands: name of the bands to compute the outlier score
    :type bands: tuple
    :param process: Statistic to detect the outlier
    :type process: str
    :param dist: 'distance' to be considered outlier. If the chosen process
        is 'mean' the distance is in 'standar deviation' else if it is
        'median' the distance is in 'percentage/100'. Example:

        dist=1 -> min=0, max=100

        dist=0.5 -> min=25, max=75

        etc

    :type dist: int
    """
    def __init__(self, bands, process="median", dist=0.7, name="score-outlier",
                 **kwargs):
        super(Outliers, self).__init__(**kwargs)

        # TODO: param bands is related to the collection used
        self.bands = bands
        self.process = process

        # TODO: distribution
        self.dist = dist
        self.range_in = (0, 1)
        self.name = name
        self.sleep = kwargs.get("sleep", 10)

        # TODO: create `min` and `max` properties depending on the chosen process

    @property
    def bands_ee(self):
        return ee.List(self.bands)

    @property
    def bandslength(self):
        return float(len(self.bands))

    @property
    def increment(self):
        return float(1 / self.bandslength)

    @staticmethod
    def apply(collection, **kwargs):
        """ Determine if pixels are outliers given a collection and parameters

        :param bands: the bands to use for determination
        :type bands: list
        :param reducer: the reducer to use. Can be 'mean' or 'median'
        :type reducer: str
        :param amount: how many stdDev (mean) or percentage (median) to
            determine the upper and lower limit
        :type amount: float
        """
        bands = kwargs.get('bands')
        reducer = kwargs.get('reducer')
        amount = kwargs.get('amount')

        if reducer is None:
            reducer = 'mean'

        if amount is None:
            if reducer == 'mean':
                amount = 0.7
            elif reducer == 'median':
                amount = 0.5

        # MASK PIXELS = 0 OUT OF EACH IMAGE OF THE COLLECTION
        col = collection.map(lambda img: img.selfMask())

        if bands is None:
            bands = ee.Image(col.first()).bandNames()

        # Collection with selected bands only
        selected = col.select(bands)

        # get statistics for mean process
        if reducer == "mean":
            mean = ee.Image(selected.mean())
            std = ee.Image(selected.reduce(ee.Reducer.stdDev()))
            distance = std.multiply(amount)

            mmin = mean.subtract(distance).rename(bands)
            mmax = mean.add(distance).rename(bands)

        # get statistics for median process
        elif reducer == "median":
            mmin = ee.Image(selected.reduce(ee.Reducer.percentile([50-(50*amount)])))
            mmin = mmin.rename(bands)
            mmax = ee.Image(selected.reduce(ee.Reducer.percentile([50+(50*amount)])))
            mmax = mmax.rename(bands)

        def wrap(img):
            # select bands
            bands_i = img.select(bands)

            # condition inside
            condition = bands_i.gte(mmin) \
                .And(bands_i.lte(mmax))

            if reducer == 'median':
                # condition = condition.select(condition.bandNames(), img.bandNames())
                condition = condition.rename(bands)

            condition = condition.Not()
            pout = tools.image.addSuffix(condition, '_outlier')

            return img.addBands(pout) \
                .set('SCORE_OUTLIER_REDUCER', reducer) \
                .set('SCORE_OUTLIER_AMOUNT', amount)

        return collection.map(wrap)


    def map(self, collection, **kwargs):
        """
        :return:
        :rtype: ee.Image
        """
        name = self.name
        increment = self.increment
        reducer = self.process
        amount = self.dist

        outliers = self.apply(collection, bands=self.bands, reducer=reducer,
                              amount=amount)

        pattern = self.bands_ee.map(
            lambda name: ee.String(name).cat('_outlier'))

        def wrap(img):
            out = img.select(pattern)
            # As apply method returns 1 for outliers and the score should be 0
            # for it, turn it upside down
            out = out.Not()
            suma = tools.image.sumBands(out, name)
            final = suma.select(name) \
                .multiply(ee.Image(increment)).rename(name)

            no_out = tools.image.removeBands(img, pattern)

            return no_out.addBands(final)

        return outliers.map(wrap)


@register(factory)
@register_all(__all__)
class Index(Score):
    """ Score for a vegetation index. As higher the index value, higher the
    score.

    :param index: name of the vegetation index. Can be 'ndvi', 'evi' or 'nbr'
    :type index: str
    """
    def __init__(self, index="ndvi", target=0.8, name="score-index",
                 function='linear', stretch=1, **kwargs):
        super(Index, self).__init__(**kwargs)
        self.index = index
        self.range_in = kwargs.get("range_in", (0, 1))
        self.name = name
        self.function = function
        self.target = target
        self.stretch = stretch

    def adjust(self):
        return lambda img: img

    @staticmethod
    def compute(image, **kwargs):
        """ Compute Index Score. Parameters:

        - index (str): the name of the index
        - target (float): the value of the index that will be the output
          maximum
        - range_min (float): the minmum value of the index range
        - range_max (float): the maximum value of the index range
        - out_min (float): the minmum value of the expected output. Defaults to
          zero
        - out_max (float): the maximum value of the expected output. Defaults
          to one
        - function (str): can be 'linear' or 'gauss'. Defaults to 'linear'
        - stretch (float): a stretching value for the normal distribution
        """
        index = kwargs.get('index')
        target = kwargs.get('target')
        range_min = kwargs.get('range_min')
        range_max = kwargs.get('range_max')
        out_min = kwargs.get('out_min', 0)
        out_max = kwargs.get('out_max', 1)
        function = kwargs.get('function', 'linear')
        stretch = kwargs.get('stretch', 1)
        name = kwargs.get('name')

        if function == 'linear':
            result = tools.image.linearFunction(image, index,
                                                 range_min=range_min,
                                                 range_max=range_max,
                                                 mean=target,
                                                 output_min=out_min,
                                                 output_max=out_max,)

        elif function == 'gauss':
            result = tools.image.gaussFunction(image, index,
                                                range_min=range_min,
                                                range_max=range_max,
                                                mean=target,
                                                output_min=out_min,
                                                output_max=out_max,
                                                stretch=stretch)
        else:
            raise ValueError('function parameter must be "linear" or "gauss"')

        return result.rename(name)

    def map(self, collection, **kwargs):
        def wrap(img):
            result = self.compute(img, index=self.index,
                                  function=self.function,
                                  name=self.name,
                                  range_min=self.range_in[0],
                                  range_max=self.range_in[1],
                                  target=self.target,
                                  out_min=self.range_out[0],
                                  out_max=self.range_out[1],
                                  stretch=self.stretch
                                  )
            return img.addBands(result)

        return collection.map(wrap)


@register(factory)
@register_all(__all__)
class MultiYear(Score):
    """ Score for a multiyear (multiseason) composite. Suppose you create a
    single composite for 2002 but want to use images from 2001 and 2003. To do
    that you have to indicate in the creation of the Bap object, but you want
    to prioritize the central year (2002). To do that you have to include this
    score in the score's list.

    :param main_year: central year
    :type main_year: int
    :param season: main season
    :type season: season.Season
    :param ratio: how much score will be taken each year. In the example would
        be 0.95 for 2001, 1 for 2002 and 0.95 for 2003
    :type ration: float
    """

    def __init__(self, main_year, season, ratio=0.05, function='linear',
                 stretch=1, name="score-multi", **kwargs):
        super(MultiYear, self).__init__(**kwargs)
        self.main_year = main_year
        self.season = season
        self.ratio = ratio
        self.function = function
        self.name = name
        self.stretch = stretch
        self.year_property = kwargs.get('year_property', 'YEAR_BAP')

    def adjust(self):
        """ redefine adjust method for NOT adjusting """
        return lambda img: img

    @staticmethod
    def apply(collection, **kwargs):
        """ Apply multi year score to every image in a collection.

        :param target_year: target year
        :type target_year: int
        :param function: the function to use. Can be one of
            'linear' or 'gauss'
        :type function: str
        :param name: name for the resulting band
        :type name: str
        :param stretch: stretch parameter for the Gauss function
        :type stretch: float
        :param output_min: minimum desired value for the output
        :type output_min: float
        :param output_max: maximum desired value for the output
        :type output_max: float
        :param year_property: the name of the property that holds the date. If
            None, it will compute the year taken from the image date
        :param year_property: str
        :return: the parsed collection with a new property called by parameter
            `name` (defaults to 'year_score').
        :rtype: ee.ImageCollection
        """
        year = ee.Number(kwargs.get('target_year'))
        function = kwargs.get('function', 'linear')
        name = kwargs.get('name', 'year_score')
        stretch = kwargs.get('stretch', 1)
        output_min = kwargs.get('output_min', 0)
        output_max = kwargs.get('output_max', 1)
        year_property = kwargs.get('year_property')

        # temporary distance property name
        uid = uuid4()
        distance_name = 'distance_{}'.format(uid)

        # function to compute distance
        def distance(img):
            if year_property:
                iyear = ee.Number(img.get(year_property))
            else:
                iyear = ee.Date(img.date()).get('year')

            dist = year.subtract(ee.Number(iyear))
            return img.set(distance_name, dist)

        # compute distance to best_doy
        collection = collection.map(distance)

        if function == 'linear':
            result = tools.imagecollection.linearFunctionProperty(
                collection,
                distance_name,
                mean=0,
                output_min= output_min,
                output_max= output_max,
                name=name)

        elif function == 'gauss':
            result = tools.imagecollection.gaussFunctionProperty(
                collection,
                distance_name,
                mean=0,
                output_min= output_min,
                output_max= output_max,
                stretch=stretch,
                name=name
            )

        else:
            raise ValueError("function must be 'linear' or 'gauss'")

        def addBand(img):
            score = ee.Number(img.get(name))
            scoreband = ee.Image.constant(score).rename(name).toFloat()
            return img.addBands(scoreband)

        final = result.map(addBand)
        return final

    def map(self, collection, **kwargs):
        """ This method keeps only the images included in the seasons

        :param years: the list of all years
        :type years: list
        """
        year = self.main_year
        range_out = self.range_out

        # Use YEAR_BAP property that is set in the BAP process
        return self.apply(collection, target_year=year, name=self.name,
                          output_min=range_out[0], output_max=range_out[1],
                          function=self.function, stretch=self.stretch,
                          year_property=self.year_property)


@register(factory)
@register_all(__all__)
class Threshold(Score):
    def __init__(self, bands=None, name='score-thres',
                 **kwargs):
        """ Threshold score """
        super(Threshold, self).__init__(**kwargs)

        self.bands = bands
        self.name = name

    @staticmethod
    def compute(img, **kwargs):
        """ Compute the threshold score

        :param thresholds: a dictionary of threshold values for each band. The
            keys of the dict must be the name of the bands, and the value for
            each band MUST be a dict with 2 keys: `min` and `max`. For example:

            ``` python
            threshold = {'B1': {'min': 1000, 'max': 3000}}
            ```
        :type thresholds: dict
        :param name: the name of the resulting band
        :type name: str
        :rtype: ee.Image
        """
        thresholds = kwargs.get('thresholds')
        name = kwargs.get('name', 'score-threshold')

        # Cast
        thresholds = ee.Dictionary(thresholds)

        bands_ee = ee.List(thresholds.keys())
        relation_ee = ee.Dictionary(thresholds)
        length = ee.Number(bands_ee.size())

        def compute_score(band, first):
            score_complete = ee.Image(first)
            img_band = img.select([band])
            min = ee.Dictionary(relation_ee.get(band)).get('min')  # could be None
            max = ee.Dictionary(relation_ee.get(band)).get('max')  # could be None

            score_min = img_band.gte(ee.Image.constant(min))
            score_max = img_band.lte(ee.Image.constant(max))

            final_score = score_min.And(score_max)  # Image with one band

            return tools.image.replace(score_complete, band, final_score)

        scores = ee.Image(bands_ee.iterate(compute_score,
                                           tools.image.empty(0, bands_ee)))

        final_score = tools.image.sumBands(scores, name=name) \
            .divide(ee.Image.constant(length))

        return final_score.select(name)

    def map(self, collection, **kwargs):
        """ map the score over a collection

        :param col: the collection
        :type col: satcol.Collection
        """
        print('score not available temporarely')
        return collection


@register(factory)
@register_all(__all__)
class Medoid(Score):
    def __init__(self, bands=None, discard_zeros=True, name='score-medoid',
                 **kwargs):
        super(Medoid, self).__init__(**kwargs)
        self.name = name
        self.bands = bands
        self.discard_zeros = discard_zeros

    @staticmethod
    def apply(collection, **kwargs):
        return composite.medoidScore(collection, **kwargs)

    def map(self, collection, **kwargs):

        return self.apply(collection, bands=self.bands,
                          discard_zeros=self.discard_zeros,
                          bandname=self.name,
                          normalize=self.normalize)


@register(factory)
@register_all(__all__)
class Brightness(Score):
    def __init__(self, target=1, bands=None, name='score-brightness',
                 function='linear', **kwargs):
        """ Brightness score

        :param target: a percentage target. For exampĺe, target=0.8 means that
            the top score will be for the 80 percent of the maximum brightness
        :type target: float
        """
        super(Brightness, self).__init__(**kwargs)
        if not bands:
            bands = ['green', 'blue', 'red', 'nir', 'swir']
        self.bands = bands
        self.name = name
        self.function = function
        self.target = target

    def adjust(self):
        return lambda img: img

    @staticmethod
    def compute(image, **kwargs):
        """ Compute a brightness score.

        :param bands: the bands to use for brightness
        :type bands: list
        :param target: the brighness value that will take the top score
        :type target: float
        :param function: the function that will be used for computing brighness
            score. Can be 'linear' or 'gauss'
        :type function: str
        :param min_value: minimum value that takes each band
        :type min_value: float
        :param min_value: maximum value that takes each band
        :type min_value: float

        """
        bands = kwargs.get('bands')
        min_value = kwargs.get('min_value')
        max_value = kwargs.get('max_value')
        max_brighness = kwargs.get('max_brightness')
        min_brighness = kwargs.get('min_brightness')
        function = 'linear'
        target = kwargs.get('target')
        output_min = kwargs.get('output_min', 0)
        output_max = kwargs.get('output_max', 1)
        name = kwargs.get('name')
        stretch = kwargs.get('stretch')

        if not bands:
            bands = image.bandNames()

        bands = ee.List(bands)
        length = ee.Number(bands.size())
        img = image.select(bands)

        if min_brighness is not None:
            allmin = ee.Number(min_brighness)
        elif min_value is not None and min_brighness is None:
            min_value = ee.Number(min_value)
            allmin = min_value.multiply(length)
        else:
            msg = "You must specify a minimum value for brightness, either" \
                  " using `min_value` parameter or `min_brightness` parameter"
            raise ValueError(msg)

        if max_brighness:
            allmax = ee.Number(max_brighness)
        elif max_value and not max_brighness:
            max_value = ee.Number(max_value)
            allmax = max_value.multiply(length)
        else:
            msg = "You must specify a maximum value for brightness, either" \
                  " using `max_value` parameter or `max_brightness` parameter"
            raise ValueError(msg)

        brightness = img.reduce('sum')

        if function == 'linear':
            result = tools.image.linearFunction(
                image=brightness,
                band='sum',
                range_min=allmin,
                range_max=allmax,
                mean=target,
                name=name,
                output_min=output_min,
                output_max=output_max
            )
        elif function == 'gauss':
            result = tools.image.gaussFunction(
                image=brightness,
                band='sum',
                range_min=allmin,
                range_max=allmax,
                mean=target,
                name=name,
                output_min=output_min,
                output_max=output_max,
                stretch=stretch
            )

        return result

    def map(self, collection, **kwargs):
        """ Map score over a collection.

        :param col: collection
        :type col: satcol.Collection
        """
        col = kwargs.get('col')

        mx = max([b.max for b in col.bands if b.name in self.bands])

        length = len(self.bands)

        target = mx * length * self.target

        def wrap(img):
            score = self.compute(
                image=img,
                target=target,
                bands=self.bands,
                max_value=mx,
                min_value=0,
                function=self.function,
                name=self.name,
                output_min=self.range_out[0],
                output_max=self.range_out[1],
            )

            return img.addBands(score)

        newcol = collection.map(wrap)
        return newcol
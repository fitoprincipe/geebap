# -*- coding: utf-8 -*-
""" Main module holding the Bap Class and its methods """

from geetools import collection, tools
from . import scores, priority, functions, utils, __version__
import ee


class Bap(object):
    def __init__(self, season, range=(0, 0), colgroup=None, scores=None,
                 masks=None, filters=None, target_collection=None, brdf=False,
                 harmonize=True, **kwargs):
        self.range = range
        self.scores = scores
        self.masks = masks
        self.filters = filters
        self.season = season
        self.colgroup = colgroup
        self.brdf = brdf
        self.harmonize = harmonize

        if target_collection is None:
            target_collection = collection.Landsat8SR()
        self.target_collection = target_collection

        self.score_name = kwargs.get('score_name', 'score')

        # Band names in case user needs different names
        self.bandname_col_id = kwargs.get('bandname_col_id', 'col_id')
        self.bandname_date = kwargs.get('bandname_date', 'date')

    @property
    def score_names(self):
        if self.scores:
            punt = [p.name for p in self.scores]
            return functions.replace_duplicate(punt)
        else:
            return []

    @property
    def max_score(self):
        """ gets the maximum score it can get """
        maxpunt = 0
        for score in self.scores:
            maxpunt += score.max
        return maxpunt

    def year_range(self, year):
        try:
            i = year - abs(self.range[0])
            f = year + abs(self.range[1]) + 1

            return range(i, f)
        except:
            return None

    def time_start(self, year):
        """ Get time start property """
        return ee.Date('{}-{}-{}'.format(year, 1, 1))

    def make_proxy(self, image, collection, year):
        """ Make a proxy collection """

        size = collection.size()

        # unmask all bands
        unmasked = image.unmask()

        proxy_date = ee.Date('{}-01-01'.format(year))

        bands = image.bandNames()
        empty = tools.image.empty(0, bands)
        proxy = unmasked.where(unmasked, empty)

        proxy = proxy.set('system:time_start', proxy_date.millis())

        proxy_col = ee.ImageCollection.fromImages([proxy])

        return ee.ImageCollection(ee.Algorithms.If(size.gt(0),
                                                   collection,
                                                   proxy_col))


    def compute_scores(self, year, site, indices=None, **kwargs):
        """ Add scores and merge collections

        :param add_individual_scores: adds the individual scores to the images
        :type add_individual_scores: bool
        :param buffer: make a buffer before cutting to the given site
        :type buffer: float
        """
        add_individual_scores = kwargs.get('add_individual_scores', False)
        buffer = kwargs.get('buffer', None)

        all_collections = ee.List([])

        # TODO: get common bands for col of all years
        if self.colgroup is None:
            colgroup = priority.SeasonPriority(year).colgroup
            all_col = []
            for year in self.year_range(year):
                _colgroup = priority.SeasonPriority(year).colgroup
                for col in _colgroup.collections:
                    all_col.append(col)
        else:
            all_col = self.colgroup.collections
            colgroup = self.colgroup

        common_bands = collection.getCommonBands(*all_col, match='name')

        # add col_id to common bands
        common_bands.append(self.bandname_col_id)

        # add date band to common bands
        common_bands.append(self.bandname_date)

        # add score names if 'add_individual_scores'
        if add_individual_scores:
            for score_name in self.score_names:
                common_bands.append(score_name)

        # add indices to common bands
        if indices:
            for i in indices:
                common_bands.append(i)

        # add score band to common bands
        common_bands.append(self.score_name)

        # create an empty score band in case no score is parsed
        empty_score = ee.Image.constant(0).rename(self.score_name).toUint8()

        # List to store all used images
        used_images = []

        for col in colgroup.collections:
            col_ee_bounds = col.collection

            # Filter bounds
            if isinstance(site, ee.Feature): site = site.geometry()
            col_ee_bounds = col_ee_bounds.filterBounds(site)

            for year in self.year_range(year):
                daterange = self.season.add_year(year)

                # filter date
                col_ee = col_ee_bounds.filterDate(daterange.start(),
                                                  daterange.end())

                # some filters
                if self.filters:
                    for filt in self.filters:
                        if filt.name in ['CloudCover']:
                            col_ee = filt.apply(col_ee, col=col)

                # BRDF
                if self.brdf:
                    if 'brdf' in col.algorithms.keys():
                        col_ee = col_ee.map(lambda img: col.brdf(img))

                # Proxy in case size == 0
                col_ee = self.make_proxy(col.collection.first(), col_ee, year)

                # store used images
                imlist = ee.List(col_ee.toList(col_ee.size()).map(
                    lambda img:
                    ee.String(col.id).cat('/').cat(ee.Image(img).id())))
                used_images.append(imlist)

                # clip with site
                if buffer is not None:
                    site = site.buffer(buffer)
                col_ee = col_ee.map(lambda img: img.clip(site))

                # Add year as a property (YEAR_BAP)
                col_ee = col_ee.map(lambda img: img.set('YEAR_BAP', year))

                # Catch SLC off
                slcoff = False
                if col.spacecraft == 'LANDSAT' and col.number == 7:
                    if year in priority.SeasonPriority.l7_slc_off:
                        # Convert masked values to zero
                        col_ee = col_ee.map(lambda img: img.unmask())
                        slcoff = True

                # Apply masks
                if self.masks:
                    for mask in self.masks:
                        col_ee = mask.map(col_ee, col=col)

                # Rename
                col_ee = col_ee.map(lambda img: col.rename(img))

                # Rescale
                col_ee = col_ee.map(
                    lambda img: collection.rescale(
                        img, col, self.target_collection, renamed=True))

                # Indices
                if indices:
                    for i in indices:
                        f = getattr(col, i)
                        def addindex(img):
                            ind = f(img, renamed=True)
                            return img.addBands(ind)
                        col_ee = col_ee.map(addindex)

                # Apply scores
                if self.scores:
                    for score in self.scores:
                        zero = False if slcoff and isinstance(score, (scores.MaskPercent, scores.MaskPercentKernel)) else True
                        col_ee = score._map(
                            col_ee,
                            col=col,
                            year=year,
                            colEE=col_ee,
                            geom=site,
                            include_zero=zero)

                # Mask all bands with mask
                col_ee = col_ee.map(lambda img: img.updateMask(img.select([0]).mask()))

                # Get an image before the filter to catch all bands for proxy image
                col_ee_image = col_ee.first()

                # Filter Mask Cover
                if self.filters:
                    for filt in self.filters:
                        if filt.name in ['MaskCover']:
                            col_ee = filt.apply(col_ee)

                # col_ee = self.make_proxy(col, col_ee, year, True)
                col_ee = self.make_proxy(col_ee_image, col_ee, year)

                # Add col_id band
                # Add col_id to the image as a property
                def addBandID(img):
                    col_id = functions.get_col_id(col)
                    col_id_img = functions.get_col_id_image(col)
                    return img.addBands(col_id_img).set(
                        self.bandname_col_id.upper(),
                        col_id)
                col_ee = col_ee.map(addBandID)

                # Add date band
                def addDateBand(img):
                    date = img.date()
                    year = date.get('year').format()

                    # Month
                    month = date.get('month')
                    month_str = month.format()
                    month = ee.String(ee.Algorithms.If(
                        month.gte(10),
                        month_str,
                        ee.String('0').cat(month_str)))

                    # Day
                    day = date.get('day')
                    day_str = day.format()
                    day = ee.String(ee.Algorithms.If(
                        day.gte(10),
                        day_str,
                        ee.String('0').cat(day_str)))

                    date_str = year.cat(month).cat(day)
                    newdate = ee.Number.parse(date_str)
                    newdate_img = ee.Image.constant(newdate) \
                        .rename(self.bandname_date).toUint32()
                    return img.addBands(newdate_img)
                col_ee = col_ee.map(addDateBand)

                # Harmonize
                if self.harmonize:
                    # get max value for the needed bands

                    if 'harmonize' in col.algorithms.keys():
                        col_ee = col_ee.map(
                            lambda img: col.harmonize(img, renamed=True))

                col_ee_list = col_ee.toList(col_ee.size())

                all_collections = all_collections.add(col_ee_list).flatten()

        all_collection = ee.ImageCollection.fromImages(all_collections)

        # get all used images
        used_images = ee.List(used_images).flatten()

        # Compute final score
        # ftotal = tools.image.sumBands("score", scores)
        if self.scores:
            def compute_score(img):
                score = img.select(self.score_names).reduce('sum') \
                    .rename('score').toFloat()
                return img.addBands(score)
        else:
            def compute_score(img):
                return img.addBands(empty_score)

        all_collection = all_collection.map(compute_score)

        # Select common bands
        # all_collection = functions.select_match(all_collection)
        final_collection = all_collection.map(
            lambda img: img.select(common_bands))

        # set used images to the collection
        final_collection = final_collection.set('BAP_USED_IMAGES', used_images)

        return final_collection

    def build_composite_best(self, year, site, indices=None, **kwargs):
        """ Build the a composite with best score

        :param add_individual_scores: adds the individual scores to the images
        :type add_individual_scores: bool
        :param buffer: make a buffer before cutting to the given site
        :type buffer: float
        """
        # TODO: pass properties
        col = self.compute_scores(year, site, indices, **kwargs)
        mosaic = col.qualityMosaic(self.score_name)

        return self.set_properties(mosaic, year, col)

    def build_composite_reduced(self, year, site, indices=None, **kwargs):
        """ Build the composite where

        :param add_individual_scores: adds the individual scores to the images
        :type add_individual_scores: bool
        :param buffer: make a buffer before cutting to the given site
        :type buffer: float
        """
        # TODO: pass properties
        nimages = kwargs.get('set', 5)
        reducer = kwargs.get('reducer', 'interval_mean')
        col = self.compute_scores(year, site, indices, **kwargs)
        mosaic = reduce_collection(col, nimages, reducer, self.score_name)

        return self.set_properties(mosaic, year)

    def set_properties(self, mosaic, year, col):
        """ Set some BAP common properties to the given mosaic """
        # USED IMAGES
        used_images = col.get('BAP_USED_IMAGES')
        mosaic = mosaic.set('BAP_USED_IMAGES', used_images)

        # DATE
        date = self.time_start(year).millis()
        mosaic = mosaic.set('system:time_start', date)

        # BAP Version
        mosaic = mosaic.set('BAP_VERSION', __version__)
        bap_params = {}
        for score in self.scores:
            bap_params = utils.serialize(score, score.name, bap_params)

        # BAP Parameters
        mosaic = mosaic.set('BAP_PARAMETERS', bap_params)

        # FOOTPRINT
        geom = tools.imagecollection.mergeGeometries(col)
        mosaic = mosaic.set('system:footprint', geom)

        # Seasons
        for year in self.year_range(year):
            yearstr = ee.Number(year).format()
            daterange = self.season.add_year(year)
            start = daterange.start().format('yyyy-MM-dd')
            end = daterange.end().format('yyyy-MM-dd')
            string = start.cat(' to ').cat(end)
            propname = ee.String('BAP_SEASON_').cat(yearstr)
            mosaic = mosaic.set(propname, string)

        return mosaic


def reduce_collection(collection, set=5, reducer='mean',
                      scoreband='score'):
    """ Reduce the collection and get a statistic from a set of pixels

    Transform the collection to a 2D array

    * axis 1 (horiz) -> bands
    * axis 0 (vert) -> images

    ====== ====== ===== ===== ======== =========
       \     B2    B3    B4     index    score
    ------ ------ ----- ----- -------- ---------
     img1
     img2
     img3
    ====== ====== ===== ===== ======== =========

    :param reducer: Reducer to use for the set of images. Options are:
        'mean', 'median', 'mode', 'intervalMean'(default)
    :type reducer: str || ee.Reducer
    :param collection: collection that holds the score
    :type collection: ee.ImageCollection
    :return: An image in which every pixel is the reduction of the set of
        images with best score
    :rtype: ee.Image
    """
    reducers = {'mean': ee.Reducer.mean(),
                'median': ee.Reducer.median(),
                'mode': ee.Reducer.mode(),
                'interval_mean': ee.Reducer.intervalMean(50, 90),
                'first': ee.Reducer.first(),
                }

    if reducer in reducers.keys():
        selected_reducer = reducers[reducer]
    elif isinstance(reducer, ee.Reducer):
        selected_reducer = reducer
    else:
        raise ValueError('Reducer {} not recognized'.format(reducer))

    # Convert masked pixels to 0 value
    # collection = collection.map(tools.mask2zero)
    collection = collection.map(lambda img: img.unmask())

    array = collection.toArray()

    # Axis
    bands_axis = 1
    images_axis = 0

    # band names
    bands = ee.Image(collection.first()).bandNames()

    # index of score
    score_index = bands.indexOf(scoreband)

    # get only scores band
    score = array.arraySlice(axis= bands_axis,
                             start= score_index,
                             end= score_index.add(1))

    # Sort the array (ascending) by the score band
    sorted_array = array.arraySort(score)

    # total longitud of the array image (number of images)
    longitud = sorted_array.arrayLength(0)

    # Cut the Array
    # lastvalues = arrayOrdenado.arraySlice(self.ejeImg,
    # longitud.subtract(self.set), longitud)
    lastvalues = sorted_array.arraySlice(axis=images_axis,
                                          start=longitud.subtract(set),
                                          end=longitud)

    # Cut score axis
    solopjes = lastvalues.arraySlice(axis=bands_axis,
                                     start=score_index,
                                     end= score_index.add(1))

    #### Process ####
    processed = lastvalues.arrayReduce(selected_reducer,
                                       ee.List([images_axis]))

    # Transform the array to an Image
    result_image = processed.arrayProject([bands_axis]) \
                            .arrayFlatten([bands])

    return result_image
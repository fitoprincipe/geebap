# -*- coding: utf-8 -*-
""" Main module holding the Bap Class and its methods """

from geetools import tools, collection
from . import scores, priority, functions, __version__
import ee


class Bap(object):
    def __init__(self, year=None, range=(0, 0), colgroup=None, scores=None,
                 masks=None, filters=None, season=None, target_collection=None,
                 brdf=True, harmonize=True, **kwargs):
        self.year = year
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
    def date_range(self):
        try:
            i = self.year - abs(self.range[0])
            f = self.year + abs(self.range[1]) + 1

            return range(i, f)
        except:
            return None

    @property
    def score_names(self):
        if self.scores:
            punt = [p.name for p in self.scores]
            return functions.replace_duplicate(punt)
        else:
            return []

    def max_score(self):
        """ gets the maximum score it can get """
        maxpunt = 0
        for score in self.scores:
            maxpunt += score.max
        return maxpunt

    def compute_scores(self, site, indices=None, **kwargs):
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
            colgroup = priority.SeasonPriority(self.year).colgroup
            all_col = []
            for year in self.date_range:
                _colgroup = priority.SeasonPriority(year).colgroup
                for col in _colgroup.collections:
                    all_col.append(col)
        else:
            all_col = self.colgroup.collections
            colgroup = self.colgroup

        common_bands = collection.get_common_bands(*all_col, match='name')
        # common_bands = self.colgroup.common_bands(match='name')

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

        for col in colgroup.collections:
            col_ee = col.collection

            # Filter bounds
            if isinstance(site, ee.Feature): site = site.geometry()
            col_ee = col_ee.filterBounds(site)

            for year in self.date_range:
                daterange = self.season.add_year(year)

                # filter date
                col_ee = col_ee.filterDate(daterange.start(), daterange.end())

                # some filters
                if self.filters:
                    for filt in self.filters:
                        if filt.name in ['CloudCover']:
                            col_ee = filt.apply(col_ee, col=col)

                size = col_ee.size()

                # Proxy image in case filters return 0
                proxy_date = ee.Date('{}-01-01'.format(year))
                proxy_i = col.proxy_image().set('system:time_start',
                                                proxy_date.millis())
                proxy = ee.ImageCollection.fromImages([proxy_i])

                col_ee = ee.ImageCollection(ee.Algorithms.If(size.gt(0),
                                                             col_ee, proxy))

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
                # TODO: modify scores to match new collection module
                if self.scores:
                    for score in self.scores:
                        zero = False if slcoff and isinstance(score, scores.MaskPercent) else True
                        col_ee = score._map(
                            col_ee,
                            col=col,
                            year=year,
                            colEE=col_ee,
                            geom=site,
                            include_zero=zero)

                # Add date band
                # col_ee = col_ee.map(date.Date.map())

                # Filter Mask Cover
                if self.filters:
                    for filt in self.filters:
                        if filt.name in ['MaskCover']:
                            col_ee = filt.apply(col_ee)

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
                    month = date.get('month').format()
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

                # TODO: see what happened with BRDF Algorithm in geetools
                # BRDF
                # if self.brdf:
                #     if 'brdf' in col.algorithms.keys():
                #         col_ee = col_ee.map(col.brdf())

                # Harmonize
                if self.harmonize:
                    if 'harmonize' in col.algorithms.keys():
                        col_ee = col_ee.map(col.harmonize())

                col_ee_list = col_ee.toList(col_ee.size())

                all_collections = all_collections.add(col_ee_list).flatten()

        all_collection = ee.ImageCollection.fromImages(all_collections)

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

        return final_collection

    def build_composite_best(self, site, indices=None, **kwargs):
        """ Build the a composite with best score

        :param add_individual_scores: adds the individual scores to the images
        :type add_individual_scores: bool
        :param buffer: make a buffer before cutting to the given site
        :type buffer: float
        """
        # TODO: pass properties
        col = self.compute_scores(site, indices, **kwargs)
        mosaic = col.qualityMosaic(self.score_name)

        return self.set_properties(mosaic)

    def build_composite_reduced(self, site, indices=None, **kwargs):
        """ Build the composite where

        :param add_individual_scores: adds the individual scores to the images
        :type add_individual_scores: bool
        :param buffer: make a buffer before cutting to the given site
        :type buffer: float
        """
        # TODO: pass properties
        nimages = kwargs.get('set', 5)
        reducer = kwargs.get('reducer', 'interval_mean')
        col = self.compute_scores(site, indices, **kwargs)
        mosaic = reduce_collection(col, nimages, reducer, self.score_name)

        return self.set_properties(mosaic)

    def time_start(self):
        """ Get time start property """
        return ee.Date('{}-{}-{}'.format(self.year, 1, 1))

    def set_properties(self, mosaic):
        """ Set some BAP common properties to the given mosaic """
        # DATE
        date = self.time_start().millis()
        mosaic = mosaic.set('system:time_start', date)
        # BAP Version
        mosaic = mosaic.set('BAP_version', __version__)

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
# -*- coding: utf-8 -*-
""" Main module holding the Bap Class and its methods """

from geetools import collection, tools
from . import scores, priority, functions, utils, __version__
import ee
import json


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

        # list to 'collect' collections
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
        used_images = dict()

        for col in colgroup.collections:
            col_ee_bounds = col.collection

            # Filter bounds
            if isinstance(site, ee.Feature): site = site.geometry()
            col_ee_bounds = col_ee_bounds.filterBounds(site)

            # Collection ID
            col_id = functions.get_col_id(col)
            col_id_img = functions.get_col_id_image(col)

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
                        col_ee = col_ee.map(lambda img: functions.unmask_slc_off(img))
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
                    return img.addBands(col_id_img).set(
                        self.bandname_col_id.upper(), col_id)
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

                # store used images
                # Property name for storing images as properties
                prop_name = 'BAP_IMAGES_COLID_{}_YEAR_{}'.format(col_id, year)
                # store used images
                imlist = ee.List(col_ee.toList(col_ee.size()).map(
                    lambda img:
                    ee.String(col.id).cat('/').cat(ee.Image(img).id())))
                used_images[prop_name] = imlist

                col_ee_list = col_ee.toList(col_ee.size())
                all_collections = all_collections.add(col_ee_list).flatten()

        all_collection = ee.ImageCollection.fromImages(all_collections)

        # Compute final score
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

        self._used_images = used_images

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

        return self._set_properties(mosaic, year, col)

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

        return self._set_properties(mosaic, year, col)

    def _set_properties(self, mosaic, year, col):
        """ Set some BAP common properties to the given mosaic """
        # # USED IMAGES
        # used_images = self._used_images
        # for prop, value in used_images.items():
        #     mosaic = mosaic.set(prop, str(value))

        # SCORES
        bap_scores = []
        for score in self.scores:
            pattern = utils.object_init(score)
            bap_scores.append(pattern)
        mosaic = mosaic.set('BAP_SCORES', str(bap_scores))

        # MASKS
        bap_masks = []
        for mask in self.masks:
            pattern = utils.object_init(mask)
            bap_masks.append(pattern)
        mosaic = mosaic.set('BAP_MASKS', str(bap_masks))

        # FILTERS
        bap_filters = []
        for filter in self.filters:
            pattern = utils.object_init(filter)
            bap_filters.append(pattern)
        mosaic = mosaic.set('BAP_FILTERS', str(bap_filters))
        
        # DATE
        date = self.time_start(year).millis()
        mosaic = mosaic.set('system:time_start', date)

        # BAP Version
        mosaic = mosaic.set('BAP_VERSION', __version__)

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

    def to_file(self, filename, path=None):
        """ Make a configuration file (JSON) to be able to reconstruct the
        object """
        import os
        def make_name(filename):
            split = filename.split('.')
            if len(split) == 1:
                filename = '{}.json'.format(filename)
            else:
                ext = split[-1]
                if ext != 'json':
                    name = '.'.join(split[:-1])
                    filename = '{}.json'.format(name)
            return filename
        filename = make_name(filename)
        path = '' if path == None else path
        path = os.path.join(os.getcwd(), path, filename)
        serial = utils.serialize(self, 'config')['config (Bap)']
        with open(path, 'w') as thefile:
            json.dump(serial, thefile, indent=2)


def load(filename, path=None):
    """ Create a Bap object using a config file """
    from . import season, masks, filters, scores
    from geetools import collection
    import os
    if path is None:
        path = os.getcwd()
    split = filename.split('.')
    if split[-1] != 'json':
        filename = '{}.json'.format(filename)
    obj = json.load(open(os.path.join(path, filename)))

    # HELPER
    def get_number(param_dict, name):
        if name != '':
            params = ['{} (int)', '{} (float)']
        else:
            params = ['{}(int)', '{}(float)']

        for param in params:
            result = param_dict.get(param.format(name))
            if result is not None:
                return result
        return None

    # SEASON
    seas = obj['season (Season)']
    start = seas['_start (SeasonDate)']['date (str)']
    end = seas['_end (SeasonDate)']['date (str)']
    season_param = season.Season(start, end)

    # RANGE
    ran = obj.get('range (tuple)') or obj.get('range (list)')
    range_param = (ran[0]['(int)'], ran[1]['(int)'])

    # MASKS
    mask_list = []
    for mask in obj.get('masks (tuple)') or obj.get('masks (list)') or []:
        mask_class = list(mask.keys())[0]
        params = mask[mask_class]
        if mask_class == '(Mask)':
            options = [opt['(str)'] for opt in params.get('options (list)') or params.get('options (tuple)')]
            mask_param = masks.Mask(options)
        elif mask_class == '(Hollstein)':
            options = [opt['(str)'] for opt in params.get('options (list)') or params.get('options (tuple)')]
            mask_param = masks.Hollstein(options)
        else:
            continue
        mask_list.append(mask_param)

    # FILTERS
    filter_list = []
    for filter in obj.get('filters (tuple)') or obj.get('filters (list)') or []:
        filter_class = list(filter.keys())[0]
        params = filter[filter_class]
        if filter_class == '(CloudCover)':
            percent = get_number(params, 'percent')
            filter_param = filters.CloudCover(percent)
        elif filter_class == 'MaskCover':
            percent = get_number(params, 'percent')
            filter_param = filters.MaskCover(percent)
        else:
            continue
        filter_list.append(filter_param)

    # COLGROUP
    colgroup = obj.get('colgroup (CollectionGroup') or obj.get('colgroup (NoneType)')
    if colgroup:
        collections = []
        collections_param = colgroup.get('collections (tuple)') or colgroup.get('collections (list)')
        for col in collections_param:
            sat = list(col.keys())[0]
            params = col[sat]
            satid = params['_id (str)']
            instance = collection.fromId(satid)
            collections.append(instance)
        colgroup_param = collection.CollectionGroup(collections)
    else:
        colgroup_param = None


    # TARGET COLLECTION
    target_collection = obj.get('target_collection (Landsat)') or \
                        obj.get('target_collection (Sentinel)')

    target_id = target_collection.get('id (str)')
    target_param = collection.fromId(target_id)

    # SCORES
    score_list = []
    for score in obj.get('scores (list)') or obj.get('scores (tuple)') or []:
        score_class = list(score.keys())[0]
        params = score[score_class]
        # RANGE OUT
        range_out_param = params.get('range_out (tuple)') or params.get('range_out (list)')
        if range_out_param:
            range_out_0 = range_out_param[0]
            range_out_1 = range_out_param[1]
            range_out = (get_number(range_out_0, ''), get_number(range_out_1, ''))
        else:
            range_out = None

        # RANGE IN
        range_in_param = params.get('range_in (tuple)') or params.get('range_in (list)')
        if range_in_param:
            range_in_0 = range_in_param[0]
            range_in_1 = range_in_param[1]
            range_in = (get_number(range_in_0, ''), get_number(range_in_1, ''))
        else:
            range_in = None

        # NAME
        name = params.get('name (str)')
        sleep = get_number(params, 'sleep')
        if score_class == '(CloudScene)':
            continue
        if score_class == '(CloudDist)':
            dmax = get_number(params, 'dmax')
            dmin = get_number(params, 'dmin')
            kernel = params.get('kernel (str)')
            units = params.get('units (str)')
            score_param = scores.CloudDist(dmin, dmax, name, kernel=kernel, units=units)
        elif score_class == '(Doy)':
            best_doy = params.get('best_doy (str)')
            doy_season_param = params.get('season (Season)')
            start = doy_season_param['_start (SeasonDate)']['date (str)']
            end = doy_season_param['_end (SeasonDate)']['date (str)']
            Season = season.Season(start, end)
            function = params.get('function (str)')
            stretch = get_number(params, 'stretch')
            score_param = scores.Doy(best_doy, Season, name, function, stretch)
        elif score_class == '(AtmosOpacity)':
            continue
        elif score_class == '(MaskPercent)':
            band = params.get('band (str)')
            maxPixels = params.get('maxPixels (int)')
            count_zeros = params.get('count_zeros (bool)')
            score_param = scores.MaskPercent(band, name, maxPixels, count_zeros)
        elif score_class == '(MaskPercentKernel)':
            kernel = params.get('kernel (str)')
            distance = get_number(params, 'distance')
            units = params.get('units (str)')
            score_param = scores.MaskPercentKernel(kernel, distance, units, name)
        elif score_class == '(Satellite)':
            ratio = get_number(params, 'ratio')
            score_param = scores.Satellite(ratio, name)
        elif score_class == '(Outliers)':
            bands = params.get('bands (tuple)') or params.get('bands (list)')
            bandlist = [band['(str)'] for band in bands]
            process = params.get('process (str)')
            dist = get_number(params, 'dist')
            score_param = scores.Outliers(bandlist, process, dist, name)
        elif score_class == '(Index)':
            index = params.get('index (str)')
            target = get_number(params, 'target')
            function = params.get('function (str)')
            stretch = get_number(params, 'stretch')
            score_param = scores.Index(index, target, name, function, stretch)
        elif score_class == '(MultiYear)':
            main_year = params.get('main_year (int)')
            my_season_param = params.get('season (Season)')
            start = my_season_param['_start (SeasonDate)']['date (str)']
            end = my_season_param['_end (SeasonDate)']['date (str)']
            Season = season.Season(start, end)
            ratio = get_number(params, 'ratio')
            function = params.get('function (str)')
            stretch = get_number(params, 'stretch')
            score_param = scores.MultiYear(main_year, Season, ratio, function, stretch, name)
        elif score_class == '(Threshold)':
            continue
        elif score_class == '(Medoid)':
            bands = params.get('bands (list)') or params.get('bands (tuple)')
            discard_zeros = params.get('discard_zeros (bool)')
            score_param = scores.Medoid(bands, discard_zeros, name)
        elif score_class == '(Brightness)':
            target = get_number(params, 'target')
            bands = params.get('bands (list)') or params.get('bands (tuple)')
            function = params.get('function (str)')
            score_param = scores.Brightness(target, bands, name, function)
        else:
            continue

        score_param.sleep = sleep
        score_param.range_out = range_out
        score_param.range_in = range_in
        score_list.append(score_param)

    # MISC
    score_name_param = obj.get('score_name (str)')
    bandname_date_param = obj.get('bandname_date (str)')
    brdf_param = obj.get('brdf (bool)')
    harmonize_param = obj.get('harmonize (bool)')
    bandname_col_id_param = obj.get('bandname_col_id (str)')

    return Bap(season_param, range_param, colgroup_param, score_list,
               mask_list, filter_list, target_param, brdf_param,
               harmonize_param, score_name=score_name_param,
               bandname_date=bandname_date_param,
               bandname_col_id=bandname_col_id_param)


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
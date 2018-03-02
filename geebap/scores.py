#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Module to implement scores in the Bap Image Composition """
import ee

import ee.data
if not ee.data._initialized: ee.Initialize()

import satcol
import functions
from geetools import tools
import season
# from functions import execli
from geetools.tools import execli
from expressions import Expression
from abc import ABCMeta, abstractmethod
from regdec import *

__all__ = []
factory = {}


class Score(object):
    ''' Abstract Base class for scores '''
    __metaclass__ = ABCMeta
    def __init__(self, name="score", range_in=None, formula=None,
                 range_out=(0, 1), sleep=0, **kwargs):
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
        self.formula = formula
        self.range_out = range_out
        self.sleep = sleep

    @property
    def normalize(self):
        return True

    @property
    def max(self):
        return self.range_out[1]

    @property
    def min(self):
        return self.range_out[0]

    def adjust(self):
        if self.range_out != (0, 1):
            return tools.parameterize((0, 1), self.range_out, [self.name])
        else:
            return lambda x: x

    @abstractmethod
    def map(self, **kwargs):
        """ Funcion para usar en ImageCollection.map(), que se deberá
        sobreescribir en los puntjaes personalizados """
        def wrap(img):
            return img
        return wrap

    def empty(self, img):
        """ Metodo comun para todos los puntajes. Agrega una band a cada
        imagen con el name del puntaje y ceros en todos sus pixeles
        """
        i = ee.Image.constant(0).select([0], [self.name]).toFloat()
        return img.addBands(i)


@register(factory)
@register_all(__all__)
class CloudScene(Score):
    """ Cloud cover percent score for the whole scene. Default name for the
    resulting band will be 'score-cld-esc'.

    :param name: name of the resulting band
    :type name: str
    """
    def __init__(self, name="score-cld-esc", **kwargs):
        super(CloudScene, self).__init__(**kwargs)
        # self.normalize = normalize  # heredado
        # self.adjust = adjust  # heredado
        self.range_in = (0, 100)
        self.name = name

        self.formula = Expression.Exponential(rango=self.range_in,
                                              normalizar=self.normalize,
                                              **kwargs)

    def map(self, col, **kwargs):
        """

        :param col: collection
        :type col: satcol.Collection
        """
        if col.nubesFld:
            # fmap = Expression.adjust(self.name, self.adjust)
            fmap = self.adjust()
            return self.formula.map(self.name,
                                    prop=col.nubesFld,
                                    map=fmap,
                                    **kwargs)
        else:
            return self.empty


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
    kernels = {"euclidean": ee.Kernel.euclidean,
               "manhattan": ee.Kernel.manhattan,
               "chebyshev": ee.Kernel.chebyshev
               }

    def __init__(self, dmax=600, dmin=0, unit="meters", name="score-cld-dist",
                 kernel='euclidean', **kwargs):
        super(CloudDist, self).__init__(**kwargs)
        self.kernel = kernel  # kwargs.get("kernel", "euclidean")
        self.unit = unit
        self.dmax = dmax
        self.dmin = dmin
        self.name = name
        self.range_in = (dmin, dmax)
        self.sleep = kwargs.get("sleep", 10)

    # GEE
    @property
    def dmaxEE(self):
        return ee.Image.constant(self.dmax)

    @property
    def dminEE(self):
        return ee.Image.constant(self.dmin)

    def kernelEE(self):
        fkernel = CloudDist.kernels[self.kernel]
        return fkernel(radius=self.dmax, units=self.unit)

    def generate_score(self, image, bandmask):
        # ceros = image.select([0]).eq(0).Not()

        cloud_mask = image.mask().select(bandmask)

        # COMPUTO LA DISTANCIA A LA MASCARA DE NUBES (A LA INVERSA)
        distancia = cloud_mask.Not().distance(self.kernelEE())

        # BORRA LOS DATOS > d_max (ESTO ES PORQUE EL KERNEL TOMA LA DIST
        # DIAGONAL TAMB)
        clip_max_masc = distancia.lte(self.dmaxEE)
        distancia = distancia.updateMask(clip_max_masc)

        # BORRA LOS DATOS = 0
        distancia = distancia.updateMask(cloud_mask)

        # AGREGO A LA IMG LA BANDA DE DISTANCIAS
        # img = img.addBands(distancia.select([0],["dist"]).toFloat())

        # COMPUTO EL PUNTAJE (WHITE)

        c = self.dmaxEE.subtract(self.dminEE).divide(ee.Image(2))
        b = distancia.min(self.dmaxEE)
        a = b.subtract(c).multiply(ee.Image(-0.2)).exp()
        e = ee.Image(1).add(a)

        pjeDist = ee.Image(1).divide(e)

        # TOMA LA MASCARA INVERSA PARA SUMARLA DESP
        masc_inv = pjeDist.mask().Not()

        # TRANSFORMA TODOS LOS VALORES ENMASCARADOS EN 0
        pjeDist = pjeDist.mask().where(1, pjeDist)

        # SUMO LA MASC INVERSA A LA IMG DE DISTANCIAS
        pjeDist = pjeDist.add(masc_inv)

        # VUELVO A ENMASCARAR LAS NUBES
        pjeDist = pjeDist.updateMask(cloud_mask)

        return pjeDist

    def map(self, col, **kwargs):
        """ Mapping function

        :param col: Collection
        :type col: satcol.Collection
        """
        nombre = self.name
        # bandmask = self.bandmask
        bandmask = col.bandmask
        kernelEE = self.kernelEE()
        dmaxEE = self.dmaxEE
        dminEE = self.dminEE
        ajuste = self.adjust()

        def wrap(img):
            """ calcula el puntaje de distancia a la nube.

            Cuando d >= dmax --> pdist = 1
            Propósito: para usar en la función map() de GEE
            Objetivo:

            :return: la propia imagen con una band agregada llamada 'pdist'
            :rtype: ee.Image
            """
            # Selecciono los pixeles con valor distinto de cero
            ceros = img.select([0]).eq(0).Not()

            masc_nub = img.mask().select(bandmask)

            # COMPUTO LA DISTANCIA A LA MASCARA DE NUBES (A LA INVERSA)
            distancia = masc_nub.Not().distance(kernelEE)

            # BORRA LOS DATOS > d_max (ESTO ES PORQUE EL KERNEL TOMA LA DIST
            # DIAGONAL TAMB)
            clip_max_masc = distancia.lte(dmaxEE)
            distancia = distancia.updateMask(clip_max_masc)

            # BORRA LOS DATOS = 0
            distancia = distancia.updateMask(masc_nub)

            # AGREGO A LA IMG LA BANDA DE DISTANCIAS
            # img = img.addBands(distancia.select([0],["dist"]).toFloat())

            # COMPUTO EL PUNTAJE (WHITE)

            c = dmaxEE.subtract(dminEE).divide(ee.Image(2))
            b = distancia.min(dmaxEE)
            a = b.subtract(c).multiply(ee.Image(-0.2)).exp()
            e = ee.Image(1).add(a)

            pjeDist = ee.Image(1).divide(e)

            # TOMA LA MASCARA INVERSA PARA SUMARLA DESP
            masc_inv = pjeDist.mask().Not()

            # TRANSFORMA TODOS LOS VALORES ENMASCARADOS EN 0
            pjeDist = pjeDist.mask().where(1, pjeDist)

            # SUMO LA MASC INVERSA A LA IMG DE DISTANCIAS
            pjeDist = pjeDist.add(masc_inv)

            # VUELVO A ENMASCARAR LAS NUBES
            pjeDist = pjeDist.updateMask(masc_nub)

            # DE ESTA FORMA OBTENGO VALORES = 1 SOLO DONDE LA DIST ES > 50
            # DONDE LA DIST = 0 ESTA ENMASCARADO

            newimg = img.addBands(pjeDist.select([0], [nombre]).toFloat())
            newimg_masked = newimg.updateMask(ceros)

            return ajuste(newimg_masked)
        return wrap

    def mask_kernel(self, img):
        """ Mask out pixels within `dmin` and `dmax` properties of the score."""
        masc_nub = img.mask().select(self.bandmask)

        # COMPUTO LA DISTANCIA A LA MASCARA DE NUBES (A LA INVERSA)
        distancia = masc_nub.Not().distance(self.kernelEE())

        # BORRA LOS DATOS > d_max (ESTO ES PORQUE EL KERNEL TOMA LA DIST
        # DIAGONAL TAMB)
        # clip_max_masc = distancia.lte(self.dmaxEE())
        # distancia = distancia.updateMask(clip_max_masc)

        # BORRA LOS DATOS = 0
        distancia = distancia.updateMask(masc_nub)

        # TRANSFORMO TODOS LOS PIX DE LA DISTANCIA EN 0 PARA USARLO COMO
        # MASCARA BUFFER
        buff = distancia.gte(ee.Image(0))
        buff = buff.mask().where(1, buff)
        buff = buff.Not()

        # APLICO LA MASCARA BUFFER
        return img.updateMask(buff)


@register(factory)
@register_all(__all__)
class Doy(Score):
    """ Score for the 'Day of the Year (DOY)'

    :param formula: Formula to use
    :type formula: Expression
    :param season: Growing season (holds a `doy` attribute)
    :type season: season.Season
    :param name: name for the resulting band
    :type name: str
    """
    def __init__(self, formula=Expression.Normal, name="score-doy",
                 season=season.Season.Growing_South(), **kwargs):
        super(Doy, self).__init__(**kwargs)
        # PARAMETROS
        self.doy_month = season.doy_month
        self.doy_day = season.doy_day

        self.ini_month = season.ini_month
        self.ini_day = season.ini_day

        # FACTOR DE AGUSADO DE LA CURVA GAUSSIANA
        # self.ratio = float(ratio)

        # FORMULA QUE SE USARA PARA EL CALCULO
        self.exp = formula

        self.name = name

    # DOY
    def doy(self, year):
        """ DOY: Day Of Year. Most representative day of the year for the
        growing season

        :param year: Year
        :type year: int
        :return: the doy
        :rtype: ee.Date
        """
        d = "{}-{}-{}".format(year, self.doy_month, self.doy_day)
        return ee.Date(d)

    def ini_date(self, year):
        """ Initial date

        :param year: Year
        :type year: int
        :return: initial date
        :rtype: ee.Date
        """
        d = "{}-{}-{}".format(year - 1, self.ini_month, self.ini_day)
        return ee.Date(d)

    def end_date(self, year):
        """ End date

        :param year: Year
        :type year: int
        :return: end date
        :rtype: ee.Date
        """
        dif = self.doy(year).difference(self.ini_date(year), "day")
        return self.doy(year).advance(dif, "day")

    def doy_range(self, year):
        """ Number of days since `ini_date` until `end_date`

        :param year: Year
        :type year: int
        :return: Doy range
        :rtype: ee.Number
        """
        return self.end_date(year).difference(self.ini_date(year), "day")

    def sequence(self, year):
        return ee.List.sequence(1, self.doy_range(year).add(1))

    # CANT DE DIAS DEL AÑO ANTERIOR
    def last_day(self, year):
        return ee.Date.fromYMD(ee.Number(year - 1), 12, 31).getRelative(
            "day", "year")

    def mean(self, year):
        """ Mean

        :return: Valor de la mean en un objeto de Earth Engine
        :rtype: ee.Number
        """
        return ee.Number(self.sequence(year).reduce(ee.Reducer.mean()))

    def std(self, year):
        """ Standar deviation

        :return:
        :rtype: ee.Number
        """
        return ee.Number(self.sequence(year).reduce(ee.Reducer.stdDev()))

    def distance_to_ini(self, date, year):
        """ Distance in days between the initial date and the given date for
        the given year (season)

        :param date: date to compute the 'relative' position
        :type date: ee.Date
        :param year: the year of the season
        :type year: int
        :return: distance in days between the initial date and the given date
        :rtype: int
        """
        ini = self.ini_date(year)
        return date.difference(ini, "day")

    # VARIABLES DE EE
    # @property
    # def castigoEE(self):
    #    return ee.Number(self.castigo)

    def ee_year(self, year):
        return ee.Number(year)

    def map(self, year, **kwargs):
        """

        :param year: central year
        :type year: int
        """
        media = execli(self.mean(year).getInfo)()
        std = execli(self.std(year).getInfo)()
        ran = execli(self.doy_range(year).getInfo)()
        self.rango_in = (1, ran)

        # exp = Expression.Normal(mean=mean, std=std)
        expr = self.exp(media=media, std=std,
                        rango=self.rango_in, normalizar=self.normalize, **kwargs)

        def transform(prop):
            date = ee.Date(prop)
            pos = self.distance_to_ini(date, year)
            return pos

        return expr.map(self.name, prop="system:time_start", eval=transform,
                        map=self.adjust(), **kwargs)


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

    def map(self, col, **kwargs):
        """

        :param col: collection
        :type col: satcol.Collection
        """
        if col.ATM_OP:
            return self.expr.map(name=self.name,
                                 band=col.ATM_OP,
                                 map=self.adjust(),
                                 **kwargs)
        else:
            return self.empty


@register(factory)
@register_all(__all__)
class MaskPercent(Score):
    """ This score represents the 'masked pixels cover' for a given area.
    It uses a ee.Reducer so it can be consume much EE capacity

    :param band: band of the image that holds the masked pixels
    :type band: str
    :param maxPixels: same param of ee.Reducer
    :type maxPixels: int
    :param include_zero: include pixels with zero value as mask
    :type include_zero: bool
    """
    def __init__(self, band=None, name="score-maskper", maxPixels=1e13,
                 include_zero=True, **kwargs):
        super(MaskPercent, self).__init__(**kwargs)
        self.band = band
        self.maxPixels = maxPixels
        self.name = name
        self.include_zero = include_zero  # TODO
        self.sleep = kwargs.get("sleep", 30)

    # TODO: ver param geom, cambiar por el área de la imagen
    def map(self, col, geom=None, **kwargs):
        """
        :param col: collection
        :type col: satcol.Collection
        :param geom: geometry of the area
        :type geom: ee.Geometry, ee.Feature
        :return:
        """
        scale = col.scale
        nombre = self.name
        banda = self.band if self.band else col.bandmask
        ajuste = self.adjust()

        if banda:
            def wrap(img):

                # Selecciono los pixeles con valor distinto de cero
                ceros = img.select([0]).eq(0).Not()

                g = geom if geom else img.geometry()
                img0 = img.select(banda)

                # OBTENGO LA MASCARA
                mask = img0.neq(0)
                # i = img0.updateMask(mask)

                total = g.area(10).divide(
                    ee.Number(scale).multiply(ee.Number(scale)))

                # CUENTO LA CANT DE PIXELES SIN ENMASCARAR
                imagen = mask.reduceRegion(reducer= ee.Reducer.sum(),
                                           geometry= g,
                                           scale= scale,
                                           maxPixels= self.maxPixels).get(banda)

                # EN UN NUMERO
                numpor = ee.Number(imagen).divide(total)
                # por = ee.Number(1).subtract(numpor)

                # CALCULO EL PORCENTAJE DE PIXELES ENMASCARADOS (imagen / total)
                imgpor = ee.Image(ee.Image.constant(imagen)).divide(ee.Image.constant(total))
                # imgpor = ee.Image.constant(1).subtract(imgpor)

                # RENOMBRO LA BANDA PARA QUE SE LLAME pnube Y LA CONVIERTO A Float
                imgpor = imgpor.select([0], [nombre]).toFloat()

                return ajuste(img.addBands(imgpor).updateMask(ceros).set(nombre, numpor))
        else:
            wrap = self.empty

        return wrap


@register(factory)
@register_all(__all__)
class Satellite(Score):
    """ Score for the satellite

    :param rate: 'amount' of the score that will be taken each step of the
        available satellite list
    :type rate: float
    """
    def __init__(self, rate=0.05, name="score-sat", **kwargs):
        super(Satellite, self).__init__(**kwargs)
        self.name = name
        self.rate = rate

    def map(self, col, **kwargs):
        """
        :param col: Collection
        :type col: satcol.Collection
        """
        nombre = self.name
        theid = col.ID
        ajuste = self.adjust()

        def wrap(img):
            # CALCULA EL PUNTAJE:
            # (tamaño - index)/ tamaño
            # EJ: [1, 0.66, 0.33]
            # pje = size.subtract(index).divide(size)
            ##

            # Selecciono los pixeles con valor distinto de cero
            ceros = img.select([0]).eq(0).Not()

            a = img.date().get("year")

            # LISTA DE SATELITES PRIORITARIOS PARA ESE AÑO
            # lista = season.PriorTempLandEE(ee.Number(a)).listaEE
            lista = season.SeasonPriority.ee_relation.get(a.format())
            # UBICA AL SATELITE EN CUESTION EN LA LISTA DE SATELITES
            # PRIORITARIOS, Y OBTIENE LA POSICION EN LA LISTA
            index = ee.List(lista).indexOf(ee.String(theid))

            ## OPCION 2
            # 1 - (0.05 * index)
            # EJ: [1, 0.95, 0.9]
            factor = ee.Number(self.rate).multiply(index)
            pje = ee.Number(1).subtract(factor)
            ##

            # ESCRIBE EL PUNTAJE EN LOS METADATOS DE LA IMG
            img = img.set(nombre, pje)

            # CREA LA IMAGEN DE PUNTAJES Y LA DEVUELVE COMO RESULTADO
            pjeImg = ee.Image(pje).select([0], [nombre]).toFloat()
            return ajuste(img.addBands(pjeImg).updateMask(ceros))
        return wrap


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

    def __init__(self, bands, process="median", name="score-outlier",
                 dist=0.7, **kwargs):
        super(Outliers, self).__init__(**kwargs)

        # TODO: el param bands esta mas relacionado a la coleccion... pensarlo mejor..
        # if not (isinstance(bands, tuple) or isinstance(bands, list)):
        #    raise ValueError("El parametro 'bands' debe ser una tupla o lista")
        self.bands = bands
        self.bands_ee = ee.List(bands)

        # self.col = col.select(self.bands)
        self.process = process
        # self.distribution = kwargs.get("distribution", "discreta")
        # TODO: distribution
        self.dist = dist
        '''
        self.minVal = kwargs.get("min", 0)
        self.maxVal = kwargs.get("max", 1)
        self.rango_final = (self.minVal, self.maxVal)
        self.rango_orig = (0, 1)
        '''
        self.range_in = (0, 1)
        # self.bandslength = float(len(bands))
        # self.increment = float(1/self.bandslength)
        self.name = name
        self.sleep = kwargs.get("sleep", 10)

        # TODO: create `min` and `max` properties depending on the chosen process

    @property
    def dist(self):
        return self._dist

    @dist.setter
    def dist(self, val):
        val = 0.7 if val is not isinstance(val, float) else val
        if self.process == 'mean':
            self._dist = val
        elif self.process == 'median':
            # Normalize distance to median
            val = 0 if val < 0 else val
            val = 1 if val > 1 else val
            self._dist = int(val*50)

    @property
    def bandslength(self):
        return float(len(self.bands))

    @property
    def increment(self):
        return float(1 / self.bandslength)

    def map(self, colEE, **kwargs):
        """
        :param colEE: Earth Engine collection to process
        :type colEE: ee.ImageCollection
        :return:
        :rtype: ee.Image
        """
        nombre = self.name
        bandas = self.bands_ee
        rango_orig = self.range_in
        rango_fin = self.range_out
        incremento = self.increment
        col = colEE.select(bandas)
        process = self.process

        # MASK PIXELS = 0 OUT OF EACH IMAGE OF THE COLLECTION
        def masktemp(img):
            m = img.neq(0)
            return img.updateMask(m)
        coltemp = col.map(masktemp)

        if process == "mean":
            media = ee.Image(coltemp.mean())
            std = ee.Image(col.reduce(ee.Reducer.stdDev()))
            stdXdesvio = std.multiply(self.dist)

            mmin = media.subtract(stdXdesvio)
            mmax = media.add(stdXdesvio)

        elif process == "median":
            # mediana = ee.Image(col.median())
            min = ee.Image(coltemp.reduce(ee.Reducer.percentile([50-self.dist])))
            max = ee.Image(coltemp.reduce(ee.Reducer.percentile([50+self.dist])))

            mmin = min
            mmax = max

        # print(mmin.getInfo())
        # print(mmax.getInfo())

        def wrap(img):

            # Selecciono los pixeles con valor distinto de cero
            # ceros = img.select([0]).eq(0).Not()
            ceros = img.neq(0)

            # ORIGINAL IMAGE
            img_orig = img

            # SELECT BANDS
            img_proc = img.select(bandas)

            # CONDICION
            condicion_adentro = (img_proc.gte(mmin)
                                 .And(img_proc.lte(mmax)))

            pout = functions.simple_rename(condicion_adentro, suffix="pout")

            suma = tools.sumBands(nombre)(pout)

            final = suma.select(nombre).multiply(ee.Image(incremento))

            parametrizada = tools.parametrize(rango_orig,
                                              rango_fin)(final)

            return img_orig.addBands(parametrizada)#.updateMask(ceros)
        return wrap


@register(factory)
@register_all(__all__)
class Index(Score):
    """ Score for a vegetation index. As higher the index value, higher the
    score.

    :param index: name of the vegetation index. Can be 'ndvi', 'evi' or 'nbr'
    :type index: str
    """
    def __init__(self, index="ndvi", name="score-index", **kwargs):
        super(Index, self).__init__(**kwargs)
        self.index = index
        self.range_in = kwargs.get("range_in", (-1, 1))
        self.name = name

    def map(self, **kwargs):
        ajuste = self.adjust()
        def wrap(img):
            ind = img.select([self.index])
            p = tools.parametrize(self.range_in, self.range_out)(ind)
            p = p.select([0], [self.name])
            return ajuste(img.addBands(p))
        return wrap


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

    def __init__(self, main_year, season, ratio=0.05, name="score-multi",
                 **kwargs):
        super(MultiYear, self).__init__(**kwargs)
        self.main_year = main_year
        self.season = season
        self.ratio = ratio
        self.name = name

    def map(self, **kwargs):
        a = self.main_year
        ajuste = self.adjust()

        def wrap(img):

            # Selecciono los pixeles con valor distinto de cero
            ceros = img.select([0]).eq(0).Not()

            # FECHA DE LA IMAGEN
            imgdate = ee.Date(img.date())

            diff = ee.Number(self.season.year_diff_ee(imgdate, a))

            pje1 = ee.Number(diff).multiply(ee.Number(self.ratio))
            pje = ee.Number(1).subtract(pje1)

            imgpje = ee.Image.constant(pje).select([0], [self.name])

            # return funciones.pass_date(img, img.addBands(imgpje))
            return ajuste(img.addBands(imgpje).updateMask(ceros))
        return wrap

@register(factory)
@register_all(__all__)
class Threshold(Score):
    def __init__(self, band=None, threshold=None, name='score-thres',
                 **kwargs):
        super(Threshold, self).__init__(**kwargs)

        self.band = band
        self.threshold = threshold
        self.name = name

    def map(self, **kwargs):
        min = self.threshold[0]
        max = self.threshold[1]

        # TODO: handle percentage values like ('10%', '20%')

        if isinstance(min, int) or isinstance(min, float):
            min = ee.Number(int(min))
        elif isinstance(min, str):
            conversion = int(min)
            min = ee.Number(conversion)

        if isinstance(max, int) or isinstance(max, float):
            max = ee.Number(int(max))
        elif isinstance(max, str):
            conversion = int(max)
            max = ee.Number(conversion)

        def wrap_minmax(img):
            selected_band = img.select(self.band)
            upper = selected_band.gte(max)
            lower = selected_band.lte(min)
            
            score = selected_band.where(upper, 0)
            score = score.where(lower, 0)
            score = score.where(score.neq(0), 1)

            score = score.select([0], [self.name])
            
            return img.addBands(score)           

        def wrap_min(img):
            selected_band = img.select(self.band)            
            lower = selected_band.lte(min)

            score = selected_band.where(lower, 0)
            score = score.select([0], [self.name])

            return img.addBands(score)

        def wrap_max(img):
            selected_band = img.select(self.band)
            upper = selected_band.gte(min)

            score = selected_band.where(upper, 0)
            score = score.select([0], [self.name])

            return img.addBands(score)

        # MULTIPLE DISPATCH?

        if min and max:
            return wrap_minmax
        elif not min:
            return wrap_max
        else:
            return wrap_min
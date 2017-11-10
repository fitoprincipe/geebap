#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Module to implement scores in the Bap Image Composition """

import ee
import satcol
import functions
import season
from functions import execli
from expressions import Expression
from abc import ABCMeta, abstractmethod

ee.Initialize()

PUNTAJES = ("pnube_es", "pdist")


def addConstantBands(value=None, *names, **pairs):
    """ Adds bands with a constant value

    :param names: final names for the additional bands
    :type names: str
    :param value: constant value
    :type value: int or float
    :param pairs: keywords for the bands (see example)
    :type pairs: dict
    :return: the function for ee.ImageCollection.map()
    :rtype: function

    :Example:

    .. code:: python

        from geetools import addConstantBands
        import ee

        col = ee.ImageCollection(ID)

        # Option 1 - arguments
        addC = addConstantBands(0, "a", "b", "c")
        newcol = col.map(addC)

        # Option 2 - keyword arguments
        addC = addConstantBands(a=0, b=1, c=2)
        newcol = col.map(addC)

        # Option 3 - Combining
        addC = addC = addConstantBands(0, "a", "b", "c", d=1, e=2)
        newcol = col.map(addC)
    """
    is_val_n = type(value) is int or type(value) is float

    if is_val_n and names:
        list1 = [ee.Image.constant(value).select([0], [n]) for n in names]
    else:
        list1 = []

    if pairs:
        list2 = [ee.Image.constant(val).select([0], [key]) for key, val in pairs.iteritems()]
    else:
        list2 = []

    if list1 or list2:
        lista_img = list1 + list2
    elif value is None:
        raise ValueError("Parameter 'value' must be a number")
    else:
        return addConstantBands(value, "constant")

    img_final = reduce(lambda x, y: x.addBands(y), lista_img)

    def apply(img):
        return ee.Image(img).addBands(ee.Image(img_final))

    return apply


class Score(object):
    __metaclass__ = ABCMeta
    def __init__(self, name="score", range_in=None, formula=None,
                 range_out=(0, 1), sleep=0, **kwargs):
        """ Clase Base para los puntajes
        :param name: name del puntaje
        :type name: str
        :param rango: range de valores entre los que variará el puntaje
        :type rango: tuple
        :param normalizar: indica si se debe normalize, es decir, hacer que
            los valores varien entre 0 y 1
        :type normalizar: bool
        :param ajuste: factor de adjust o ponderacion del puntaje
        :type ajuste: float
        :param formula:
        :type formula:

        :Propiedades estáticas:
        :param max: valor maximo del range
        :param min: valor minimo del range
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
            return functions.parameterize((0, 1), self.range_out, [self.name])
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


class CloudScene(Score):
    def __init__(self, **kwargs):
        """ Score para el porcentaje de nubes de la escena completa. La band
        resultante de cualquiera de los metodos tendrá como name 'pnube_es'

        :param a: valor **a** de la funcion EXPONENCIAL
        :type a: float
        :param rango: range de valores entre los que puede oscilar la variable
        :type rango: tuple
        :param normalizar: Hacer que el resultado varie entre 0 y 1
            independientemente del range
        :type normalizar: bool
        """
        super(CloudScene, self).__init__(**kwargs)
        # self.normalize = normalize  # heredado
        # self.adjust = adjust  # heredado
        self.range_in = (0, 100)
        self.name = kwargs.get("name", "score-cld-esc")

        self.formula = Expression.Exponential(rango=self.range_in,
                                              normalizar=self.normalize,
                                              **kwargs)

    def map(self, col, **kwargs):
        if col.nubesFld:
            # fmap = Expression.adjust(self.name, self.adjust)
            fmap = self.adjust()
            return self.formula.map(self.name,
                                    prop=col.nubesFld,
                                    map=fmap,
                                    **kwargs)
        else:
            return self.empty


class CloudDist(Score):

    kernels = {"euclidean": ee.Kernel.euclidean,
               "manhattan": ee.Kernel.manhattan,
               "chebyshev": ee.Kernel.chebyshev
               }

    def __init__(self, dmax=600, dmin=0, unit="meters", **kwargs):
        """ Score para la 'distancia a la mascara'. La band
        resultante de cualquiera de los metodos tendrá como name 'pdist'

        :param bandmask: Nombre de la band enmascarada que se usara para el
            process
        :type bandmask: str
        :param kernel: Kernel que se usara. Opciones: euclidean, manhattan,
            chebyshev
        :type kernel: str
        :param unit: Unidad que se usara con el kernel. Opciones: meters,
            pixels
        :type unit: str
        :param dmax: distancia maxima para la cual se calculara el puntaje.
            Si el pixel está mas lejos de la mascar que este valor, el puntaje
            toma valor 1.
        :type dmax: int
        :param dmin: distancia minima para la cual se calculara el puntaje
        :type dmin: int
        """
        super(CloudDist, self).__init__(**kwargs)
        self.kernel = kwargs.get("kernel", "euclidean")
        self.unit = unit
        self.dmax = dmax
        self.dmin = dmin
        self.name = kwargs.get("name", "score-cld-dist")
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

    def map(self, col, **kwargs):
        """

        :param col:
        :type col: satcol.Collection
        :param kwargs:
        :return:
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

            return ajuste(img.addBands(pjeDist.select([0], [nombre]).toFloat()).updateMask(ceros))
        return wrap

    def mask_kernel(self, img):
        """
        Función para enmascarar los pixeles que están a cierta distancia
        de la mascara. Para usar en map()
        """
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


class Doy(Score):
    """ Score para el "Day Of Year" (doy). Toma una fecha central y aplica
    una funcion gaussiana

    :Opcionales:
    :param ajuste: factor para dar mas o menos prioridad al DOY, multiplicando
        la curva de priorización (gaussiana). Default: 1
    :type ajuste: int
    :param mes_doy: mes del año en el que se da el mejor Dia del Año.
    Default: 1
    :type mes_doy: int
    :param dia_doy: dia del mes mas representativo de la season. Default: 15
    :type dia_doy: int
    :param mes_ini: mes de inicio de la season. Default: 11
    :type mes_ini: int
    :param dia_ini: dia de inicio de la season. Default: 15
    :type dia_ini: int
    :param formula: Formula que se usara en el calculo del puntaje
    :type formula: Expression

    """
    def __init__(self, ratio=-0.5, formula=Expression.Normal,
                 season=season.Season.Growing_South(),
                 **kwargs):
        super(Doy, self).__init__(**kwargs)
        # PARAMETROS
        self.doy_month = season.doy_month
        self.doy_day = season.doy_day

        self.ini_month = season.ini_month
        self.ini_day = season.ini_day

        # FACTOR DE AGUSADO DE LA CURVA GAUSSIANA
        self.ratio = float(ratio)

        # FORMULA QUE SE USARA PARA EL CALCULO
        self.exp = formula

        self.name = kwargs.get("name", "score-doy")

    # DOY
    def doy(self, year):
        """ Dia mas representativo del año (de la season)

        :param year: Año
        :type year: int
        :return: el dia mas representativo de la season
        :rtype: ee.Date
        """
        d = "{}-{}-{}".format(year, self.doy_month, self.doy_day)
        return ee.Date(d)

    def ini_date(self, year):
        """
        :return: fecha ini_date
        :rtype: ee.Date
        """
        d = "{}-{}-{}".format(year - 1, self.ini_month, self.ini_day)
        return ee.Date(d)

    def end_date(self, year):
        """
        :return: fecha final
        :rtype: ee.Date
        """
        dif = self.doy(year).difference(self.ini_date(year), "day")
        return self.doy(year).advance(dif, "day")

    def doy_range(self, year):
        """
        :return: Cantidad de dias desde el inicio al final
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
        """
        :return: Valor de la mean en un objeto de Earth Engine
        :rtype: ee.Number
        """
        return ee.Number(self.sequence(year).reduce(ee.Reducer.mean()))

    def std(self, year):
        """
        :return: Valor de la mean en un objeto de Earth Engine
        :rtype: ee.Number
        """
        return ee.Number(self.sequence(year).reduce(ee.Reducer.stdDev()))

    def get_doy(self, date, year):
        """ Obtener el dia del año al que pertenece una imagen

        :param date: date para la cual se quiere calcular el dia al cual
            pertence segun el objeto creado
        :type date: ee.Date
        :param year: año (season) a la cual pertenece la imagen
        :return: el dia del año al que pretenece la imagen segun el objeto
        actual
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
        media = execli(self.mean(year).getInfo)()
        std = execli(self.std(year).getInfo)()
        ran = execli(self.doy_range(year).getInfo)()
        self.rango_in = (1, ran)

        # exp = Expression.Normal(mean=mean, std=std)
        expr = self.exp(media=media, std=std,
                        rango=self.rango_in, normalizar=self.normalize, **kwargs)

        def transform(prop):
            date = ee.Date(prop)
            pos = self.get_doy(date, year)
            return pos

        return expr.map(self.name, prop="system:time_start", eval=transform,
                        map=self.adjust(), **kwargs)


class AtmosOpacity(Score):
    def __init__(self, range_in=(100, 300), formula=Expression.Exponential,
                 **kwargs):
        """ Score por opacidad de la atmosfera

        :param rango: Rango de valores entre los que se calculara el puntaje
        :type rango: tuple
        :param formula: Formula de distribution que se usara. Debe ser un
            unbounded object
        :type formula: Expression

        :Propiedades estaticas:
        :param expr: Objeto expression, con todas sus propiedades
        """
        super(AtmosOpacity, self).__init__(**kwargs)
        self.range_in = range_in
        self.formula = formula
        self.name = kwargs.get("name", "score-atm-op")

    @property
    def expr(self):
        expresion = self.formula(rango=self.range_in)
        return expresion

    def map(self, col, **kwargs):
        if col.ATM_OP:
            return self.expr.map(name=self.name,
                                 band=col.ATM_OP,
                                 map=self.adjust(),
                                 **kwargs)
        else:
            return self.empty


class MaskPercent(Score):
    """ Score *porcentaje de mascara*

    :ARGUMENTOS:
    :param geom: geometría sobre la cual se va a calcular el index
    :type geom: ee.Feature

    :param banda: band de la imagen que contiene los pixeles enmascarados que
        se van a contar
    :type banda: str

    """

    def __init__(self, band=None, maxPixels=1e13, **kwargs):
        super(MaskPercent, self).__init__(**kwargs)
        self.band = band
        self.maxPixels = maxPixels
        self.name = kwargs.get("name", "score-maskper")
        self.sleep = kwargs.get("sleep", 30)

    # TODO: ver param geom, cambiar por el área de la imagen
    def map(self, col, geom=None, **kwargs):
        """ Calcula el puntaje para porcentaje de pixeles enmascarados. (Para
        usar en la función *map* de GEE)

        :returns: la propia imagen con una band agregada llamada 'pnube'
            (0 a 1) y una nueva propiedad llamada 'mascpor' con este valor
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


class Satellite(Score):
    """ Score según el satelite

    :param sat: name del satelite
    :type sat: str
    :param anio: año de analisis
    :type anio: int

    :METODOS:

    :map(col, year, name): funcion que mapea en una coleccion el puntaje
        del satelite segun la funcion de prioridades creada en -objetos-
        del modulo CIEFAP
    """

    def __init__(self, rate=0.05, **kwargs):
        super(Satellite, self).__init__(**kwargs)
        self.name = kwargs.get("name", "score-sat")
        self.rate = rate
    '''
    @staticmethod
    def listado(year):
        obj = season.PriorTempLandEE(ee.Number(year))
        return obj.listaEE
    '''
    def map(self, col, **kwargs):
        """ Funcion que mapea en una coleccion el puntaje del satelite
            segun la funcion de prioridades creada en -objetos- del modulo
            CIEFAP """
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


class Outliers(Score):
    """
    Objeto que se crear para la detección de valores outliers en
    la band especificada

    :Obligatorios:
    :param col: colección de la cual se extraera la serie de datos
    :type col:
    :param banda: name de la band que se usará
    :type banda: str

    :Opcionales:
    :param proceso: name del process que se usará ("mean" / "mediana")
    :type proceso: str
    :param dist: distancia al valor medio que se usará. Por ejemplo, si es
        1, se considerará outlier si cae por fuera de +-1 desvío de la mean
    :type dist: int
    :param min: puntaje mínimo que se le asignará a un outlier
    :type min: int
    :param max: puntaje máximo que se le asignará a un valor que no sea
        outlier
    :type max: int
    :param distribucion: Funcion de distribution que se usará. Puede ser
        'discreta' o 'gauss'
    :type distribucion: str
    """

    def __init__(self, bands, process="mean", **kwargs):
        """
        :param bands: Lista o tuple de bands_ee. Las bands_ee deben estar en la
            imagen.
        :type bands: tuple
        :param process: Opciones: 'mean' o 'mediana'
        :type process: str
        """
        super(Outliers, self).__init__(**kwargs)

        # TODO: el param bands esta mas relacionado a la coleccion... pensarlo mejor..
        # if not (isinstance(bands, tuple) or isinstance(bands, list)):
        #    raise ValueError("El parametro 'bands' debe ser una tupla o lista")
        self.bands = bands
        self.bands_ee = ee.List(bands)

        # self.col = col.select(self.bands)
        self.process = process
        self.distribution = kwargs.get("distribution", "discreta")
        # TODO: distribution
        self.dist = kwargs.get("dist", 1)
        '''
        self.minVal = kwargs.get("min", 0)
        self.maxVal = kwargs.get("max", 1)
        self.rango_final = (self.minVal, self.maxVal)
        self.rango_orig = (0, 1)
        '''
        self.range_in = (0, 1)
        # self.bandslength = float(len(bands))
        # self.increment = float(1/self.bandslength)
        self.name = kwargs.get("name", "score-outlier")
        self.sleep = kwargs.get("sleep", 10)

    @property
    def bandslength(self):
        return float(len(self.bands))

    @property
    def increment(self):
        return float(1 / self.bandslength)

    def map(self, colEE, **kwargs):
        """ Mapea el valor outlier de modo discreto

        Si está por fuera del valor definido como mínimo o máximo, entonces le
        asigna un puntaje de 0,5, sino 1.

        :param colEE: coleccion de EE que se quiere procesar
        :type colEE: ee.ImageCollection
        :param nombre: name que se le dará a la band
        :type nombre: str
        :return: una imagen (ee.Image) con una band cuyo name tiene la
            siguiente estructura: "pout_banda" ej: "pout_ndvi"
        :rtype: ee.Image
        """
        nombre = self.name
        bandas = self.bands_ee
        rango_orig = self.range_in
        rango_fin = self.range_out
        incremento = self.increment
        col = colEE.select(bandas)
        proceso = self.process

        def masktemp(img):
            m = img.select([0]).neq(0)
            return img.updateMask(m)
        coltemp = col.map(masktemp)

        if proceso == "mean":
            media = ee.Image(coltemp.mean())
            std = ee.Image(col.reduce(ee.Reducer.stdDev()))
            stdXdesvio = std.multiply(self.dist)

            mmin = media.subtract(stdXdesvio)
            mmax = media.add(stdXdesvio)

        elif proceso == "mediana":
            # mediana = ee.Image(col.median())
            cuarenta = ee.Image(coltemp.reduce(ee.Reducer.percentile(50-(self.dist*10))))
            sesenta = ee.Image(coltemp.reduce(ee.Reducer.percentile(50+(self.dist*10))))

            mmin = cuarenta
            mmax = sesenta

        def wrap(img):

            # Selecciono los pixeles con valor distinto de cero
            ceros = img.select([0]).eq(0).Not()

            # IMAGEN ORIGINAL
            img_orig = img

            # IMAGEN A PROCESAR
            img_proc = img.select(bandas)

            # CONDICION
            condicion_adentro = (img_proc.gte(mmin)
                                 .And(img_proc.lte(mmax)))

            pout = functions.simple_rename(condicion_adentro, suffix="pout")

            suma = functions.sumBands(nombre)(pout)

            final = suma.select(nombre).multiply(ee.Image(incremento))

            parametrizada = functions.parameterize(rango_orig,
                                                   rango_fin)(final)

            return img_orig.addBands(parametrizada).updateMask(ceros)
        return wrap


class Index(Score):
    def __init__(self, index="ndvi", **kwargs):
        super(Index, self).__init__(**kwargs)
        self.index = index
        self.range_in = kwargs.get("range_in", (-1, 1))
        self.name = kwargs.get("name", "score-index")

    def map(self, **kwargs):
        ajuste = self.adjust()
        def wrap(img):
            ind = img.select([self.index])
            p = functions.parameterize(self.range_in, self.range_out)(ind)
            p = p.select([0], [self.name])
            return ajuste(img.addBands(p))
        return wrap


class MultiYear(Score):
    """Calcula el puntaje para cada imagen cuando creo una imagen BAP a
    partir de imagenes de varios años

    :CREACION:

    :param anio: año central
    :type anio: int

    :METODOS:

    :mapsat: funcion que mapea en una coleccion el puntaje del satelite
        segun la funcion de prioridades creada en -objetos- del modulo CIEFAP

    :METODO ESTATICO:
    :mapnull: agrega la band *pmulti* con valor 0 (cero)
    """

    def __init__(self, main_year, season, ratio=0.05, **kwargs):
        super(MultiYear, self).__init__(**kwargs)
        self.main_year = main_year
        self.season = season
        self.ratio = ratio
        self.name = kwargs.get("name", "score-multi")

    def map(self, **kwargs):
        """ Funcion para agregar una band pmulti a la imagen con el puntaje
        según la distancia al año central
        """
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

if __name__ == "__main__":
    psat = Satellite()
    print psat.normalize, psat.range_out
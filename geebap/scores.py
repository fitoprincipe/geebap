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


class Puntaje(object):
    __metaclass__ = ABCMeta
    def __init__(self, nombre="puntaje", rango_in=None, formula=None,
                 rango_out=(0, 1), sleep=0, **kwargs):
        """ Clase Base para los puntajes
        :param nombre: nombre del puntaje
        :type nombre: str
        :param rango: range de valores entre los que variará el puntaje
        :type rango: tuple
        :param normalizar: indica si se debe normalize, es decir, hacer que
            los valores varien entre 0 y 1
        :type normalizar: bool
        :param ajuste: factor de ajuste o ponderacion del puntaje
        :type ajuste: float
        :param formula:
        :type formula:

        :Propiedades estáticas:
        :param max: valor maximo del range
        :param min: valor minimo del range
        """
        self.nombre = nombre
        self.rango_in = rango_in
        self.formula = formula
        self.rango_out = rango_out
        self.sleep = sleep

    @property
    def normalizar(self):
        return True

    @property
    def max(self):
        return self.rango_out[1]

    @property
    def min(self):
        return self.rango_out[0]

    def ajuste(self):
        if self.rango_out != (0, 1):
            return functions.parameterize((0, 1), self.rango_out, [self.nombre])
        else:
            return lambda x: x

    @abstractmethod
    def map(self, **kwargs):
        """ Funcion para usar en ImageCollection.map(), que se deberá
        sobreescribir en los puntjaes personalizados """
        def wrap(img):
            return img
        return wrap

    def vacio(self, img):
        """ Metodo comun para todos los puntajes. Agrega una banda a cada
        imagen con el nombre del puntaje y ceros en todos sus pixeles
        """
        i = ee.Image.constant(0).select([0], [self.nombre]).toFloat()
        return img.addBands(i)


class PnubeEs(Puntaje):
    def __init__(self, **kwargs):
        """ Puntaje para el porcentaje de nubes de la escena completa. La banda
        resultante de cualquiera de los metodos tendrá como nombre 'pnube_es'

        :param a: valor **a** de la funcion EXPONENCIAL
        :type a: float
        :param rango: range de valores entre los que puede oscilar la variable
        :type rango: tuple
        :param normalizar: Hacer que el resultado varie entre 0 y 1
            independientemente del range
        :type normalizar: bool
        """
        super(PnubeEs, self).__init__(**kwargs)
        # self.normalize = normalize  # heredado
        # self.ajuste = ajuste  # heredado
        self.rango_in = (0, 100)
        self.nombre = kwargs.get("nombre", "pnube_es")

        self.formula = Expression.Exponential(rango=self.rango_in,
                                              normalizar=self.normalizar,
                                              **kwargs)

    def map(self, col, **kwargs):
        if col.nubesFld:
            # fmap = Expression.adjust(self.nombre, self.ajuste)
            fmap = self.ajuste()
            return self.formula.map(self.nombre,
                                    prop=col.nubesFld,
                                    map=fmap,
                                    **kwargs)
        else:
            return self.vacio


class Pdist(Puntaje):

    kernels = {"euclidean": ee.Kernel.euclidean,
               "manhattan": ee.Kernel.manhattan,
               "chebyshev": ee.Kernel.chebyshev
               }

    def __init__(self, dmax=600, dmin=0, unidad="meters", **kwargs):
        """ Puntaje para la 'distancia a la mascara'. La banda
        resultante de cualquiera de los metodos tendrá como nombre 'pdist'

        :param bandmask: Nombre de la banda enmascarada que se usara para el
            process
        :type bandmask: str
        :param kernel: Kernel que se usara. Opciones: euclidean, manhattan,
            chebyshev
        :type kernel: str
        :param unidad: Unidad que se usara con el kernel. Opciones: meters,
            pixels
        :type unidad: str
        :param dmax: distancia maxima para la cual se calculara el puntaje.
            Si el pixel está mas lejos de la mascar que este valor, el puntaje
            toma valor 1.
        :type dmax: int
        :param dmin: distancia minima para la cual se calculara el puntaje
        :type dmin: int
        """
        super(Pdist, self).__init__(**kwargs)
        self.kernel = kwargs.get("kernel", "euclidean")
        self.unidad = unidad
        self.dmax = dmax
        self.dmin = dmin
        self.nombre = kwargs.get("nombre", "pdist")
        self.rango_in = (dmin, dmax)
        self.sleep = kwargs.get("sleep", 10)

    # GEE
    @property
    def dmaxEE(self):
        return ee.Image.constant(self.dmax)

    @property
    def dminEE(self):
        return ee.Image.constant(self.dmin)

    def kernelEE(self):
        fkernel = Pdist.kernels[self.kernel]
        return fkernel(radius=self.dmax, units=self.unidad)

    def map(self, col, **kwargs):
        """

        :param col:
        :type col: satcol.Collection
        :param kwargs:
        :return:
        """
        nombre = self.nombre
        # bandmask = self.bandmask
        bandmask = col.bandmask
        kernelEE = self.kernelEE()
        dmaxEE = self.dmaxEE
        dminEE = self.dminEE
        ajuste = self.ajuste()

        def wrap(img):
            """ calcula el puntaje de distancia a la nube.

            Cuando d >= dmax --> pdist = 1
            Propósito: para usar en la función map() de GEE
            Objetivo:

            :return: la propia imagen con una banda agregada llamada 'pdist'
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


class Pdoy(Puntaje):
    """ Puntaje para el "Day Of Year" (doy). Toma una fecha central y aplica
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
    def __init__(self, factor=-0.5, formula=Expression.Normal,
                 temporada=season.Season.Crecimiento_patagonia(),
                 **kwargs):
        super(Pdoy, self).__init__(**kwargs)
        # PARAMETROS
        self.mes_doy = temporada.doy_month
        self.dia_doy = temporada.doy_day

        self.mes_ini = temporada.ini_month
        self.dia_ini = temporada.ini_day

        # FACTOR DE AGUSADO DE LA CURVA GAUSSIANA
        self.factor = float(factor)

        # FORMULA QUE SE USARA PARA EL CALCULO
        self.exp = formula

        self.nombre = kwargs.get("nombre", "pdoy")

    # DOY
    def doy(self, anio):
        """ Dia mas representativo del año (de la season)

        :param anio: Año
        :type anio: int
        :return: el dia mas representativo de la season
        :rtype: ee.Date
        """
        d = "{}-{}-{}".format(anio, self.mes_doy, self.dia_doy)
        return ee.Date(d)

    def inicial(self, anio):
        """
        :return: fecha inicial
        :rtype: ee.Date
        """
        d = "{}-{}-{}".format(anio-1, self.mes_ini, self.dia_ini)
        return ee.Date(d)

    def final(self, anio):
        """
        :return: fecha final
        :rtype: ee.Date
        """
        dif = self.doy(anio).difference(self.inicial(anio), "day")
        return self.doy(anio).advance(dif, "day")

    def rango_doy(self, anio):
        """
        :return: Cantidad de dias desde el inicio al final
        :rtype: ee.Number
        """
        return self.final(anio).difference(self.inicial(anio), "day")

    def secuencia(self, anio):
        return ee.List.sequence(1, self.rango_doy(anio).add(1))

    # CANT DE DIAS DEL AÑO ANTERIOR
    def ult_dia(self, anio):
        return ee.Date.fromYMD(ee.Number(anio - 1), 12, 31).getRelative(
            "day", "year")

    def media(self, anio):
        """
        :return: Valor de la mean en un objeto de Earth Engine
        :rtype: ee.Number
        """
        return ee.Number(self.secuencia(anio).reduce(ee.Reducer.mean()))

    def std(self, anio):
        """
        :return: Valor de la mean en un objeto de Earth Engine
        :rtype: ee.Number
        """
        return ee.Number(self.secuencia(anio).reduce(ee.Reducer.stdDev()))

    def get_doy(self, fecha, anio):
        """ Obtener el dia del año al que pertenece una imagen

        :param fecha: fecha para la cual se quiere calcular el dia al cual
            pertence segun el objeto creado
        :type fecha: ee.Date
        :param anio: año (season) a la cual pertenece la imagen
        :return: el dia del año al que pretenece la imagen segun el objeto actual
        :rtype: int
        """
        ini = self.inicial(anio)
        return fecha.difference(ini, "day")

    # VARIABLES DE EE
    @property
    def castigoEE(self):
        return ee.Number(self.castigo)

    def anioEE(self, anio):
        return ee.Number(anio)

    def map(self, anio, **kwargs):
        media = execli(self.media(anio).getInfo)()
        std = execli(self.std(anio).getInfo)()
        ran = execli(self.rango_doy(anio).getInfo)()
        self.rango_in = (1, ran)

        # exp = Expression.Normal(mean=mean, std=std)
        expr = self.exp(media=media, std=std,
                       rango=self.rango_in, normalizar=self.normalizar, **kwargs)

        def transform(prop):
            date = ee.Date(prop)
            pos = self.get_doy(date, anio)
            return pos

        return expr.map(self.nombre, prop="system:time_start", eval=transform,
                        map=self.ajuste(), **kwargs)


class Pop(Puntaje):
    def __init__(self, rango_in=(100, 300), formula=Expression.Exponential,
                 **kwargs):
        """ Puntaje por opacidad de la atmosfera

        :param rango: Rango de valores entre los que se calculara el puntaje
        :type rango: tuple
        :param formula: Formula de distribucion que se usara. Debe ser un
            unbounded object
        :type formula: Expression

        :Propiedades estaticas:
        :param expr: Objeto expression, con todas sus propiedades
        """
        super(Pop, self).__init__(**kwargs)
        self.rango_in = rango_in
        self.formula = formula
        self.nombre = kwargs.get("nombre", "pop")

    @property
    def expr(self):
        expresion = self.formula(rango=self.rango_in)
        return expresion

    def map(self, col, **kwargs):
        if col.ATM_OP:
            return self.expr.map(name=self.nombre,
                                 band=col.ATM_OP,
                                 map=self.ajuste(),
                                 **kwargs)
        else:
            return self.vacio


class Pmascpor(Puntaje):
    """ Puntaje *porcentaje de mascara*

    :ARGUMENTOS:
    :param geom: geometría sobre la cual se va a calcular el indice
    :type geom: ee.Feature

    :param banda: banda de la imagen que contiene los pixeles enmascarados que
        se van a contar
    :type banda: str

    """

    def __init__(self, banda=None, maxPixels=1e13, **kwargs):
        super(Pmascpor, self).__init__(**kwargs)
        self.banda = banda
        self.maxPixels = maxPixels
        self.nombre = kwargs.get("nombre", "pmascpor")
        self.sleep = kwargs.get("sleep", 30)

    # TODO: ver param geom, cambiar por el área de la imagen
    def map(self, col, geom=None, **kwargs):
        """ Calcula el puntaje para porcentaje de pixeles enmascarados. (Para
        usar en la función *map* de GEE)

        :returns: la propia imagen con una banda agregada llamada 'pnube'
            (0 a 1) y una nueva propiedad llamada 'mascpor' con este valor
        """
        scale = col.scale
        nombre = self.nombre
        banda = self.banda if self.banda else col.bandmask
        ajuste = self.ajuste()

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
            wrap = self.vacio

        return wrap


class Psat(Puntaje):
    """ Puntaje según el satelite

    :param sat: nombre del satelite
    :type sat: str
    :param anio: año de analisis
    :type anio: int

    :METODOS:

    :map(col, year, nombre): funcion que mapea en una coleccion el puntaje
        del satelite segun la funcion de prioridades creada en -objetos-
        del modulo CIEFAP
    """

    def __init__(self, factor=0.05, **kwargs):
        super(Psat, self).__init__(**kwargs)
        self.nombre = kwargs.get("nombre", "psat")
        self.factor = factor
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
        nombre = self.nombre
        theid = col.ID
        ajuste = self.ajuste()

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
            lista = season.SeasonPriority.relacionEE.get(a.format())
            # UBICA AL SATELITE EN CUESTION EN LA LISTA DE SATELITES
            # PRIORITARIOS, Y OBTIENE LA POSICION EN LA LISTA
            index = ee.List(lista).indexOf(ee.String(theid))

            ## OPCION 2
            # 1 - (0.05 * index)
            # EJ: [1, 0.95, 0.9]
            factor = ee.Number(self.factor).multiply(index)
            pje = ee.Number(1).subtract(factor)
            ##

            # ESCRIBE EL PUNTAJE EN LOS METADATOS DE LA IMG
            img = img.set(nombre, pje)

            # CREA LA IMAGEN DE PUNTAJES Y LA DEVUELVE COMO RESULTADO
            pjeImg = ee.Image(pje).select([0], [nombre]).toFloat()
            return ajuste(img.addBands(pjeImg).updateMask(ceros))
        return wrap


class Poutlier(Puntaje):
    """
    Objeto que se crear para la detección de valores outliers en
    la banda especificada

    :Obligatorios:
    :param col: colección de la cual se extraera la serie de datos
    :type col:
    :param banda: nombre de la banda que se usará
    :type banda: str

    :Opcionales:
    :param proceso: nombre del process que se usará ("mean" / "mediana")
    :type proceso: str
    :param dist: distancia al valor medio que se usará. Por ejemplo, si es
        1, se considerará outlier si cae por fuera de +-1 desvío de la mean
    :type dist: int
    :param min: puntaje mínimo que se le asignará a un outlier
    :type min: int
    :param max: puntaje máximo que se le asignará a un valor que no sea
        outlier
    :type max: int
    :param distribucion: Funcion de distribucion que se usará. Puede ser
        'discreta' o 'gauss'
    :type distribucion: str
    """

    def __init__(self, bandas, proceso="mean", **kwargs):
        """
        :param bandas: Lista o tuple de bandas. Las bandas deben estar en la
            imagen.
        :type bandas: tuple
        :param proceso: Opciones: 'mean' o 'mediana'
        :type proceso: str
        """
        super(Poutlier, self).__init__(**kwargs)

        # TODO: el param bandas esta mas relacionado a la coleccion... pensarlo mejor..
        # if not (isinstance(bandas, tuple) or isinstance(bandas, list)):
        #    raise ValueError("El parametro 'bandas' debe ser una tupla o lista")
        self.bands = bandas
        self.bandas = ee.List(bandas)

        # self.col = col.select(self.bandas)
        self.proceso = proceso
        self.distribucion = kwargs.get("distribucion", "discreta")
        # TODO: distribucion
        self.dist = kwargs.get("dist", 1)
        '''
        self.minVal = kwargs.get("min", 0)
        self.maxVal = kwargs.get("max", 1)
        self.rango_final = (self.minVal, self.maxVal)
        self.rango_orig = (0, 1)
        '''
        self.rango_in = (0, 1)
        # self.lenbandas = float(len(bandas))
        # self.incremento = float(1/self.lenbandas)
        self.nombre = kwargs.get("nombre", "poutlier")
        self.sleep = kwargs.get("sleep", 10)

    @property
    def lenbandas(self):
        return float(len(self.bands))

    @property
    def incremento(self):
        return float(1/self.lenbandas)

    def map(self, colEE, **kwargs):
        """ Mapea el valor outlier de modo discreto

        Si está por fuera del valor definido como mínimo o máximo, entonces le
        asigna un puntaje de 0,5, sino 1.

        :param colEE: coleccion de EE que se quiere procesar
        :type colEE: ee.ImageCollection
        :param nombre: nombre que se le dará a la banda
        :type nombre: str
        :return: una imagen (ee.Image) con una banda cuyo nombre tiene la
            siguiente estructura: "pout_banda" ej: "pout_ndvi"
        :rtype: ee.Image
        """
        nombre = self.nombre
        bandas = self.bandas
        rango_orig = self.rango_in
        rango_fin = self.rango_out
        incremento = self.incremento
        col = colEE.select(bandas)
        proceso = self.proceso

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


class Pindice(Puntaje):
    def __init__(self, indice="ndvi", **kwargs):
        super(Pindice, self).__init__(**kwargs)
        self.indice = indice
        self.rango_in = kwargs.get("rango_in", (-1, 1))
        self.nombre = kwargs.get("nombre", "pindice")

    def map(self, **kwargs):
        ajuste = self.ajuste()
        def wrap(img):
            ind = img.select([self.indice])
            p = functions.parameterize(self.rango_in, self.rango_out)(ind)
            p = p.select([0], [self.nombre])
            return ajuste(img.addBands(p))
        return wrap


class Pmulti(Puntaje):
    """Calcula el puntaje para cada imagen cuando creo una imagen BAP a
    partir de imagenes de varios años

    :CREACION:

    :param anio: año central
    :type anio: int

    :METODOS:

    :mapsat: funcion que mapea en una coleccion el puntaje del satelite
        segun la funcion de prioridades creada en -objetos- del modulo CIEFAP

    :METODO ESTATICO:
    :mapnull: agrega la banda *pmulti* con valor 0 (cero)
    """

    def __init__(self, anio_central, temporada, factor=0.05, **kwargs):
        super(Pmulti, self).__init__(**kwargs)
        self.anio_central = anio_central
        self.temporada = temporada
        self.factor = factor
        self.nombre = "pmulti"

    def map(self, **kwargs):
        """ Funcion para agregar una banda pmulti a la imagen con el puntaje
        según la distancia al año central
        """
        a = self.anio_central
        ajuste = self.ajuste()

        def wrap(img):

            # Selecciono los pixeles con valor distinto de cero
            ceros = img.select([0]).eq(0).Not()

            # FECHA DE LA IMAGEN
            imgdate = ee.Date(img.date())

            diff = ee.Number(self.temporada.year_diff_ee(imgdate, a))

            pje1 = ee.Number(diff).multiply(ee.Number(self.factor))
            pje = ee.Number(1).subtract(pje1)

            imgpje = ee.Image.constant(pje).select([0], [self.nombre])

            # return funciones.pass_date(img, img.addBands(imgpje))
            return ajuste(img.addBands(imgpje).updateMask(ceros))
        return wrap

if __name__ == "__main__":
    psat = Psat()
    print psat.normalizar, psat.rango_out
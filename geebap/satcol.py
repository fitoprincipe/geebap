# -*- coding: utf-8 -*-

""" Modulo que contiene todo lo relacionado a las collections para el
armado de los compuestos BAP """

import indices
import cloud_mask as cld
import ee
from copy import deepcopy
import functions
from datetime import date

try:
    ee.Initialize()
    init = True
except:
    init = False

ACTUAL_YEAR = date.today().year

class Collection(object):

    __OPTIONS = ("LANDSAT/LM1_L1T",
                "LANDSAT/LM2_L1T",
                "LANDSAT/LM3_L1T",
                "LANDSAT/LT4_L1T_TOA_FMASK",
                "LANDSAT/LT5_SR",
                "LEDAPS/LT5_L1T_SR",
                "LANDSAT/LT5_L1T_TOA_FMASK",
                "LANDSAT/LE7_SR",
                "LANDSAT/LE7_L1T_TOA_FMASK",
                "LEDAPS/LE7_L1T_SR",
                "LANDSAT/LC8_SR",
                "LANDSAT/LC8_L1T_TOA_FMASK",
                "COPERNICUS/S2",
                "MODIS/MOD09GA",
                "MODIS/MYD09GA")

    VERROR = ValueError("Collection ID must be one of: {}".format(__OPTIONS))

    def __init__(self, **kwargs):

        # ID Privado
        self.__ID = None

        # bandid para crear una banda que identifique a la col
        self.bandID = kwargs.get("bandID", None)

        # IDENTIFICADOR DEL PROCESO
        self.process = kwargs.get("process", None)

        # FAMILIA DEL SATELITE (LANDSAT, SENTINEL, MODIS)
        self.family = kwargs.get("family", None)

        # FUNCION PARA MAPEAR LA MASCARA DE NUBES PROPIA DE LA COLECCION
        self.fclouds = kwargs.get("fclouds", None)

        # CAMPO QUE CONTIENE EL PORCENTAJE DE COBERTURA DE NUBES
        self.clouds_fld = kwargs.get("clouds_fld", None)

        # BANDA QUE CONTIENE LA MASCARA DE NUBES
        self.clouds_band = kwargs.get("clouds_band", None)

        # NOMBRE ABREVIADO PARA AGREGAR A LAS PROPIEDADES DE LAS IMGS
        self.short = kwargs.get("short", None)

        # BANDAS IMPORTANTES
        self.NIR = kwargs.get("NIR", None)
        self.SWIR = kwargs.get("SWIR", None)
        self.RED = kwargs.get("RED", None)
        self.BLUE = kwargs.get("BLUE", None)
        self.SWIR2 = kwargs.get("SWIR2", None)
        self.GREEN = kwargs.get("GREEN", None)
        self.ATM_OP = kwargs.get("ATM_OP", None)  # Atmospheric Opacity

        # UMBRALES
        self.cloud_th = kwargs.get("cloud_th", None)
        self.shadow_th = kwargs.get("shadow_th", None)

        # BANDAS ESCALABLES
        self.to_scale = kwargs.get("to_scale", None)

        # COLECCION TOA EQUIVALENTE
        self.equiv = kwargs.get("equiv", None)

        # PROPIEDADES PARA LA VISUALIZACION
        self.bandvizNSR = [self.NIR, self.SWIR, self.RED]
        self.min = kwargs.get("min", 0)
        self.max = kwargs.get("max", None)

        # ESCALA DE LAS BANDAS QUE SE USAN
        self.scale = kwargs.get("scale", None)

        # ESCALA DE LAS BANDAS (dict)
        self.bandscale = kwargs.get("bandscale", None)

        # BANDA QUE CONTIENE LA MASCARA
        self.bandmask = kwargs.get("bandmask", None)

        # TOMA LOS ARGUMENTOS DE LA CREACION
        self.kws = kwargs

        # BANDAS RENOMBRADAS?
        self._renamed = False

        # RELACION DE LAS BANDAS
        self.bandasrel_original = {"BLUE": self.BLUE,
                                   "GREEN": self.GREEN,
                                   "RED": self.RED,
                                   "NIR": self.NIR,
                                   "SWIR": self.SWIR,
                                   "SWIR2": self.SWIR2,
                                   "ATM_OP": self.ATM_OP}

        self.bandsrel = {v: k for k, v in self.bandasrel_original.iteritems() if v is not None}
        # self._bandasrel = None

        # ANIO DE LANZAMIENTO y FINAL
        self.ini = kwargs.get("ini", None)
        self.fin = kwargs.get("fin", ACTUAL_YEAR)

        # Crea los diccionarios
        self.set_dicts()

    def set_dicts(self):
        # INDICES
        self.INDICES = {"ndvi": self.ndvi,
                        "nbr": self.nbr,
                        "evi": self.evi}

    def invert_bandsrel(self):
        """ Genera un diccionario con la relacion entre las bands, en el cual
        estan solo las bands presentes en la coleccion, y estas son los keys.
        Los keys son los nombres de las bands de la coleccion.
        :return: diccionario invertido de bands presentes en la coleccion
        :rtype: dict
        """
        self.bandsrel = {v: k for k, v in self.bandsrel.iteritems() if v is not None}

    @property
    def bandIDimg(self):
        return ee.Image.constant(self.bandID).select([0], ["bandID"])

    @property
    def renamed(self):
        return self._renamed

    @property
    def ID(self):
        return self.__ID

    @ID.setter
    def ID(self, id):
        if self.__ID is not None:
            raise ValueError(
                "El Objeto ya tiene el ID '{}'".format(self.__ID) + \
                " y no puede ser modificado")

        elif id in Collection.__OPTIONS:
            self.__ID = id

        else:
            # raise Collection.VERROR
            raise ValueError(
                "El id de la coleccion debe ser una de: {}".format(
                    Collection.__OPTIONS))

    @property
    def bands(self):
        """
        :return: Nombre de las bands en una lista local
        :rtype: list
        """
        if init:
            return self.colEE.bandNames().getInfo()
        else:
            return None

    @property
    def satmask(self):
        """ FUNCION PARA AGREGAR EL CODIGO DEL SATELITE

        :return: Id unico de la Collection
        :rtype: int
        """
        try:
            # le suma 1 para que el primero sea 1 y no 0
            return Collection.__OPTIONS.index(self.ID) + 1
        except:
            raise ValueError(
                "{} no esta en {}".format(self.ID, Collection.__OPTIONS))

    @property
    def colEE(self):
        """ COLECCION ORIGINAL (COMPLETA) DE EARTH ENGINE """
        if init:
            return ee.ImageCollection(self.ID)
        else:
            return None

    # FUNCIONES PARA MAPEAR EL INDICE DE VEGETACION
    @property
    def ndvi(self):
        """ Funcion para calcular el ndvi usando map() """
        if self.NIR and self.RED and init:
            return indices.ndvi(self.NIR, self.RED)
        else:
            return None

    @property
    def nbr(self):
        """ Funcion para calcular el nbr usando map() """
        if self.NIR and self.SWIR and init:
            return indices.nbr(self.NIR, self.SWIR)
        else:
            return None

    @property
    def evi(self):
        """ Funcion para calcular el evi usando map() """
        if self.NIR and self.RED and self.BLUE and init:
            return indices.evi(self.NIR, self.RED, self.BLUE)
        else:
            return None

    # NORMAL METHOD
    def rename(self, drop=False):
        """ Renombra las bands de una coleccion por sus equivalentes

        :param img:
        :return:
        """
        # drop = drop

        # Redefine self.bandsrel
        # self.bandsrel = {v: k for k, v in self.bandsrel.iteritems() if v is not None}

        # indica que el objeto tiene las bands renombradas
        self._renamed = not self._renamed

        # print 'self.bandsrel[self.NIR]', self.bandsrel[self.NIR]
        self.NIR = self.bandsrel[self.NIR] if self.NIR else None
        self.SWIR = self.bandsrel[self.SWIR] if self.SWIR else None
        self.RED = self.bandsrel[self.RED] if self.RED else None
        self.BLUE = self.bandsrel[self.BLUE] if self.BLUE else None
        self.SWIR2 = self.bandsrel[self.SWIR2] if self.SWIR2 else None
        self.GREEN = self.bandsrel[self.GREEN] if self.GREEN else None
        self.ATM_OP = self.bandsrel[self.ATM_OP] if self.ATM_OP else None

        # Redefine to_scale
        self.to_scale = [self.bandsrel[i] for i in self.to_scale]
        self.bandmask = self.bandsrel[self.bandmask]

        # obtiene la funcion para renombrar las bands antes de inveritrlas
        frename = functions.rename_bands(self.bandsrel, drop)

        # Invierte la relacion entre las bands
        self.invert_bandsrel()

        # resetea los diccionarios
        self.set_dicts()

        def wrap(img):
            return frename(img)
        return wrap


    def do_scale(self, final_range=(0, 1)):
        if self.max:
            rango_orig = (self.min, self.max)
            def wrap(img):
                escalables = functions.list_intersection(
                    img.bandNames(), ee.List(self.to_scale))

                return functions.parametrizar(
                    rango_orig, final_range, escalables)(img)
            return wrap
        else:
            return lambda x: x


    @staticmethod
    def from_id(id):
        """ Metodo para crear un objeto a partir del ID de la coleccion

        :param id: Mismo id que en Google Earth Engine. Opciones en
            Coleccion.OPCIONES
        :type id: str
        :return: El objeto creado
        :rtype: Collection
        """
        rel = {"LANDSAT/LM1_L1T": Collection.Landsat1,
               "LANDSAT/LM2_L1T": Collection.Landsat2,
               "LANDSAT/LM3_L1T": Collection.Landsat3,
               "LANDSAT/LT4_L1T_TOA_FMASK": Collection.Landsat4TOA,
               "LANDSAT/LT5_L1T_TOA_FMASK": Collection.Landsat5TOA,
               "LANDSAT/LT5_SR": Collection.Landsat5USGS,
               "LEDAPS/LT5_L1T_SR": Collection.Landsat5LEDAPS,
               "LANDSAT/LE7_L1T_TOA_FMASK": Collection.Landsat7TOA,
               "LANDSAT/LE7_SR": Collection.Landsat7USGS,
               "LEDAPS/LE7_L1T_SR": Collection.Landsat7LEDAPS,
               "LANDSAT/LC8_L1T_TOA_FMASK": Collection.Landsat8TOA,
               "LANDSAT/LC8_SR": Collection.Landsat8USGS,
               "COPERNICUS/S2": Collection.Sentinel2,
               "MODIS/MOD09GA": Collection.ModisTerra,
               "MODIS/MYD09GA": Collection.ModisAqua
               }

        try:
            return rel[id]()
        except Exception as e:
            raise e

    @classmethod
    def Landsat1(cls):
        # id = "LANDSAT/LM1_L1T"
        escalables = ["B4", "B5", "B6", "B7"]
        bandscale = dict(B4=80, B5=80, B6=80, B7=80)
        obj = cls(GREEN="B4", RED="B5", NIR="B6", SWIR="B7", process="RAW",
                  to_scale=escalables, clouds_fld="CLOUD_COVER",
                  max=255, scale=80, bandscale=bandscale, bandmask="B4",
                  family="Landsat", ini=1972, end=1978, bandID=1,
                  short="L1")

        obj.ID = "LANDSAT/LM1_L1T"
        return obj

    @classmethod
    def Landsat2(cls):
        copy = deepcopy(Collection.Landsat1())  # L1
        copy.kws["ini"] = 1975
        copy.kws["end"] = 1983
        copy.kws["bandID"] = 2
        copy.kws["short"] = "L2"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LANDSAT/LM2_L1T"
        return obj

    @classmethod
    def Landsat3(cls):
        copy = deepcopy(Collection.Landsat1())  # L1
        copy.kws["bandscale"] = dict(B4=40, B5=40, B6=40, B7=40)
        copy.kws["scale"] = 40
        copy.kws["ini"] = 1978
        copy.kws["end"] = 1983
        copy.kws["bandID"] = 3
        copy.kws["short"] = "L3"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LANDSAT/LM3_L1T"
        return obj

    @classmethod
    def Landsat4TOA(cls):
        escalables = ["B1", "B2", "B3", "B4", "B5"]
        bandscale = dict(B1=30, B2=30, B3=30, B4=30, B5=30, B6=120, B7=30)
        obj = cls(BLUE="B1", GREEN="B2", RED="B3", NIR="B4", SWIR="B5",
                  to_scale=escalables, clouds_fld="CLOUD_COVER",
                  process="TOA", max=1, fclouds=cld.fmask, scale=30,
                  bandscale=bandscale, bandmask="B1", family="Landsat",
                  clouds_band="fmask", ini=1982, end=1993, bandID=4,
                  short="L4TOA")

        obj.ID = "LANDSAT/LT4_L1T_TOA_FMASK"
        return obj

    @classmethod
    def Landsat5TOA(cls):
        copy = deepcopy(Collection.Landsat4TOA())
        copy.kws["ini"] = 1984
        copy.kws["end"] = 2013
        copy.kws["bandID"] = 5
        copy.kws["short"] = "L5TOA"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LANDSAT/LT5_L1T_TOA_FMASK"
        return obj

    @classmethod
    def Landsat5USGS(cls):
        copy = deepcopy(Collection.Landsat5TOA())  # L5 TOA
        copy.kws["process"] = "SR"
        copy.kws["max"] = 10000
        copy.kws["fclouds"] = cld.usgs
        copy.kws["ATM_OP"] = "sr_atmos_opacity"
        copy.kws["equiv"] = "LANDSAT/LT5_L1T_TOA_FMASK"
        copy.kws["clouds_band"] = "cfmask"
        copy.kws["bandID"] = 6
        copy.kws["short"] = "L5USGS"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LANDSAT/LT5_SR"
        return obj

    @classmethod
    def Landsat5LEDAPS(cls):
        copy = deepcopy(Collection.Landsat5TOA())  # L5 TOA
        copy.kws["ATM_OP"] = "atmos_opacity"
        copy.kws["process"] = "SR"
        copy.kws["max"] = 10000
        copy.kws["fclouds"] = cld.ledaps
        copy.kws["equiv"] = "LANDSAT/LT5_L1T_TOA_FMASK"
        copy.kws["clouds_band"] = "QA"
        copy.kws["bandID"] = 7
        copy.kws["short"] = "L5LEDAPS"
        obj = cls(**copy.kws)

        # CAMBIOS
        obj.ID = "LEDAPS/LT5_L1T_SR"
        return obj

    @classmethod
    def Landsat7TOA(cls):
        copy = deepcopy(Collection.Landsat5TOA())
        copy.kws["bandscale"] = dict(B1=30, B2=30, B3=30, B4=30, B5=30, B6=60,
                                     B7=30, B8=15)
        copy.kws["ini"] = 1999
        copy.kws["bandID"] = 8
        copy.kws["short"] = "L7TOA"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LANDSAT/LE7_L1T_TOA_FMASK"
        return obj

    @classmethod
    def Landsat7USGS(cls):
        copy = deepcopy(Collection.Landsat7TOA())  # L5 USGS
        copy.kws["equiv"] = "LANDSAT/LE7_L1T_TOA_FMASK"
        copy.kws["process"] = "SR"
        copy.kws["max"] = 10000
        copy.kws["fclouds"] = cld.usgs
        copy.kws["ATM_OP"] = "sr_atmos_opacity"
        copy.kws["clouds_band"] = "cfmask"
        copy.kws["bandID"] = 9
        copy.kws["short"] = "L7USGS"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LANDSAT/LE7_SR"

        return obj

    @classmethod
    def Landsat7LEDAPS(cls):
        copy = deepcopy(Collection.Landsat5LEDAPS())  # L5 LEDAPS
        copy_TOA = deepcopy(Collection.Landsat7USGS())  # L7 USGS
        copy.kws["equiv"] = copy_TOA.equiv
        copy.kws["bandscale"] = copy_TOA.bandscale
        copy.kws["ini"] = copy_TOA.ini
        copy.kws["bandID"] = 10
        copy.kws["short"] = "L7LEDAPS"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "LEDAPS/LE7_L1T_SR"

        return obj

    @classmethod
    def Landsat8TOA(cls):
        copy = deepcopy(Collection.Landsat4TOA())  # L4 TOA
        copy.kws["bandscale"] = dict(B1=30, B2=30, B3=30, B4=30, B5=30, B6=30, B7=30,
                                     B8=15, B9=30, B10=100, B11=100)
        copy.kws["to_scale"] = ["B2", "B3", "B4", "B5", "B6", "B7"]
        copy.kws["BLUE"] = "B2"
        copy.kws["GREEN"] = "B3"
        copy.kws["RED"] = "B4"
        copy.kws["NIR"] = "B5"
        copy.kws["SWIR"] = "B6"
        copy.kws["SWIR2"] = "B7"
        copy.kws["ini"] = 2013
        copy.kws["bandmask"] = "B2"
        copy.kws["bandID"] = 11
        copy.kws["short"] = "L8TOA"
        obj = cls(**copy.kws)

        # CAMBIOS
        obj.ID = "LANDSAT/LC8_L1T_TOA_FMASK"

        return obj

    @classmethod
    def Landsat8USGS(cls):
        copy = deepcopy(Collection.Landsat8TOA())  # L8 TOA
        copy_usgs = deepcopy(Collection.Landsat5USGS())  # L5 USGS
        copy.kws["process"] = copy_usgs.process
        copy.kws["max"] = copy_usgs.max
        copy.kws["fclouds"] = cld.cfmask
        # copy.kws["ATM_OP"] = copy_usgs.ATM_OP
        copy.kws["equiv"] = "LANDSAT/LC8_L1T_TOA_FMASK"
        copy.kws["bandscale"] = copy.bandscale
        copy.kws["bandID"] = 12
        copy.kws["short"] = "L8USGS"
        obj = cls(**copy.kws)

        # CAMBIOS
        obj.ID = "LANDSAT/LC8_SR"

        return obj

    @classmethod
    def Sentinel2(cls):
        escalables = ["B2", "B3", "B4", "B8", "B11", "B12"]

        bandscale = dict(B1=60, B2=10, B3=10, B4=10, B5=20, B6=20, B7=20,
                         B8=10, B8a=20, B9=60, B10=60, B11=20, B12=20)

        obj = cls(BLUE="B2", GREEN="B3", RED="B4", NIR="B8", SWIR="B11",
                  SWIR2="B12", to_scale=escalables, process="TOA",
                  clouds_fld="CLOUD_COVERAGE_ASSESSMENT", max=10000,
                  fclouds=cld.sentinel, scale=10, bandscale=bandscale,
                  bandmask="B2", family="Sentinel", ini=2015, bandID=13,
                  short="S2")

        obj.ID = "COPERNICUS/S2"

        return obj

    @classmethod
    def ModisTerra(cls):
        bandscale = dict(sur_refl_b03=500, sur_refl_b04=500, sur_refl_b01=500,
                         sur_refl_b02=500, sur_refl_b06=500, sur_refl_b07=500)

        escalables = ["sur_refl_b01", "sur_refl_b02", "sur_refl_b03",
                      "sur_refl_b04", "sur_refl_b06", "sur_refl_b07"]

        obj = cls(BLUE="sur_refl_b03", GREEN="sur_refl_b04",
                  RED="sur_refl_b01", NIR="sur_refl_b02", SWIR="sur_refl_b06",
                  SWIR2="sur_refl_b07", process="SR", scale=500, max=5000,
                  bandscale=bandscale, bandmask="sur_refl_b06",
                  family="Modis", ini=1999, bandID=14, short="MODT",
                  to_scale=escalables, fclouds=cld.modis,)

        obj.ID = "MODIS/MOD09GA"
        return obj

    @classmethod
    def ModisAqua(cls):
        copy = deepcopy(Collection.ModisTerra())
        copy.kws["ini"] = 2002
        copy.kws["short"] = "MODAQ"
        copy.kws["bandID"] = 15
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = "MODIS/MYD09GA"

        return obj


class ColGroup(object):
    """ Colecciones Agrupadas """
    def __init__(self, collections=None, scale=None, **kwargs):
        """
        :Factory Methods:
        :Landsat: Toda la coleccion Landsat
        :Modis: Toda la coleccion Modis
        :Todas: Landsat + Sentinel

        :param scale: Escala que se usara para el conjunto de collections
        :type scale: int

        :param collections: collections agrupadas
        :type collections: tuple

        :param IDS: ids de las collections
        :type IDS: list
        """
        self.scale = scale
        self.collections = collections

    @property
    def ids(self):
        if self.collections:
            return [c.ID for c in self.collections]
        else:
            return None

    def bandsrel(self):
        """ Obtiene las bands en comun que tienen las collections del grupo

        :param use: determina si usar los keys o los values del dict bandsrel
            Opciones: "keys" o "values" (def: "keys")
        :type use: str
        :return: lista de bands
        :rtype: list
        """
        # diccionario de relaciones de la primer coleccion
        rel = self.collections[0].bandasrel_original

        # Bandas
        bandas = [k for k, v in rel.iteritems() if v is not None]
        s = set(bandas)

        for i, c in enumerate(self.collections):
            if i == 0: continue
            rel = c.bandasrel_original
            bandas = [k for k, v in rel.iteritems() if v is not None]
            s2 = set(bandas)
            s = s.intersection(s2)

        return list(s)

    def scale_min(self):
        """ Obtiene la escala minima entre las collections

        :return:
        """
        escalas = [col.scale for col in self.collections]

        return min(escalas)

    def scale_max(self):
        """ Obtiene la escala maxima entre las collections

        :return:
        """
        escalas = [col.scale for col in self.collections]

        return max(escalas)

    def family(self):
        """
        :return: family a la que pertenece la coleccion completa, si
        es mixta, devuelve 'mixta'
        :rtype: str
        """
        familias = [col.family for col in self.collections]
        if len(set(familias)) == 1:
            return familias[0]
        else:
            return "Mix"

    @property
    def IDS(self):
        lista = [c.ID for c in self.collections]
        return lista

    @classmethod
    def Landsat(cls):
        """ Todas las collections Landsat """
        col = (Collection.Landsat1(),
               Collection.Landsat2(),
               Collection.Landsat3(),
               Collection.Landsat4TOA(),
               Collection.Landsat5TOA(),
               Collection.Landsat5USGS(),
               Collection.Landsat5LEDAPS(),
               Collection.Landsat7TOA(),
               Collection.Landsat7USGS(),
               Collection.Landsat7LEDAPS(),
               Collection.Landsat8TOA(),
               Collection.Landsat8USGS())

        return cls(collections=col, scale=30)

    @classmethod
    def MSS(cls):
        """ Landsat 1,2,3 """
        col = (Collection.Landsat1(),
               Collection.Landsat2(),
               Collection.Landsat3())

        return cls(collections=col, scale=40)

    @classmethod
    def Landsat_Sentinel(cls):
        """ Todas las collections excepto Modis (Landsat + Sentinel) """
        landsat = ColGroup.Landsat()
        add = (Collection.Sentinel2(),)

        col = landsat.collections + add

        return cls(collections=col, scale=10)

    @classmethod
    def TOA(cls):
        """ TOA """
        col = (Collection.Landsat4TOA(), Collection.Landsat5TOA(),
               Collection.Landsat7TOA(), Collection.Landsat8TOA())
        return cls(collections=col, scale=30)

    @classmethod
    def SR(cls):
        """ L5 USGS y LEDAPS, L7 USGS y LEDAPS, L8 USGS"""
        col = (Collection.Landsat5USGS(), Collection.Landsat5LEDAPS(),
               Collection.Landsat7USGS(), Collection.Landsat7LEDAPS(),
               Collection.Landsat8USGS())
        return cls(collections=col, scale=30)

    @classmethod
    def Modis(cls):
        """ Todas las Modis """
        col = (Collection.ModisAqua(),
               Collection.ModisTerra())
        return cls(collections=col, scale=500)

    @classmethod
    def Todas(cls):
        """ Todas las collections """
        landsat = ColGroup.Landsat().collections
        sen = (Collection.Sentinel2(),)
        mod = ColGroup.Modis().collections

        col = landsat+sen+mod
        return cls(collections=col, scale=10)


if __name__ == "__main__":
    '''
    c = Collection.Landsat1()
    c._ID = "LEDAPS/LE7_L1T_SR"
    # c.ID = None
    print c.ID, c.max, c.NIR, c.scale

    d = Collection.from_id("LANDSAT/LM2_L1T")
    print d.satmask, d.ID, d.scale, d.max, d.process, d.NIR

    h = Collection(scale=30)
    print h.scale, h.ID

    # c.colEE = ee.ImageCollection("Algomas")
    c.custom = ee.ImageCollection("algomas")
    print c.custom

    p = ee.Geometry.Point(-71,-43)

    col = c.colEE.filterBounds(p).map(c.ndvi)

    img = ee.Image(col.first())

    val_ndvi = img.reduceRegion(ee.Reducer.first(), p, 30)

    print val_ndvi.getInfo()
    
    
    for col in Collection.OPCIONES:
        c = Collection.from_id(col)
        print c, c.ID
    
    # Collection.OPC2 = ("aa", "BB")
    # print Collection.OPC()
    Collection.__OPTIONS = ("aa", "BB")
    
    a1 = Collection.from_id("LANDSAT/LT4_L1T_TOA_FMASK")
    a2 = Collection.from_id("LANDSAT/LT5_L1T_TOA_FMASK")

    print a1.kws
    
    # a1.ID = "ALGO"
    # print a1.satmask

    g1 = ColGroup.MSS()
    g1 = ColGroup(collections=(Collection.Landsat5LEDAPS(), Collection.Landsat7LEDAPS(), Collection.ModisTerra()), scale=30)

    print g1.bandsrel(), g1.scale_min(), g1.scale_max(), g1.family()
    

    imagen = ee.Image("LANDSAT/LC8_L1T_TOA_FMASK/LC82310902013344LGN00")
    imagen2 = ee.Image("LEDAPS/LT5_L1T_SR/LT52310901984169XXX03")
    p = ee.Geometry.Point(-71.72029495239258, -42.78997046797438)
    col = Collection.Landsat8TOA()
    col2 = Collection.Landsat5LEDAPS()

    print funciones.get_value(imagen2, p)

    i = col2.do_scale()(imagen2)

    print funciones.get_value(i, p)
    
    col = Collection.Landsat8TOA()
    print col.bandsrel
    print col.bandasrel_original
    print "to_scale", col.to_scale
    print "bandmask", col.bandmask
    print "renombro.."
    col.rename()
    print col.bandsrel
    print col.bandasrel_original
    print "to_scale", col.to_scale
    print "bandmask", col.bandmask
    print "renombro.."
    col.rename()
    print col.bandsrel
    print col.bandasrel_original
    print "to_scale", col.to_scale
    print "bandmask", col.bandmask
    
    g1 = ColGroup.SR()
    print g1.ids
    '''
    ls = ColGroup.Todas()
    print ls.collections
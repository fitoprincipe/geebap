#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Collections module. Add some needed parameters to collections and create
collection groups to generate a Best Available Pixel Composite """
import ee

import ee.data
if not ee.data._initialized: ee.Initialize()

from geetools import indices, tools
from geetools import cloud_mask as cld
from copy import deepcopy
from . import functions
from datetime import date

initialized = True

ACTUAL_YEAR = date.today().year

IDS = {'L1': 'LANDSAT/LM1_L1T',
       'L2': 'LANDSAT/LM2_L1T',
       'L3': 'LANDSAT/LM3_L1T',
       'L4TOA': 'LANDSAT/LT04/C01/T1_TOA',
       'L4USGS': 'LANDSAT/LT04/C01/T1_SR',
       'L5TOA': 'LANDSAT/LT05/C01/T1_TOA',
       'L5USGS': 'LANDSAT/LT05/C01/T1_SR',
       'L5LED': 'LEDAPS/LT5_L1T_SR',
       'L7TOA': 'LANDSAT/LE07/C01/T1_TOA',
       'L7USGS': 'LANDSAT/LE07/C01/T1_SR',
       'L7LED': 'LEDAPS/LE7_L1T_SR',
       'L8TOA': 'LANDSAT/LC08/C01/T1_TOA',
       'L8USGS':'LANDSAT/LC08/C01/T1_SR',
       'S2':'COPERNICUS/S2',
       'MODT':'MODIS/006/MOD09GA',
       'MODAQ': 'MODIS/006/MYD09GA'}

SAT_CODES = {'L1': 1,
             'L2': 2,
             'L3': 3,
             'L4TOA': 4,
             'L4USGS': 5,
             'L5TOA': 6,
             'L5USGS': 7,
             'L5LED': 8,
             'L7TOA': 9,
             'L7USGS': 10,
             'L7LED': 11,
             'L8TOA': 12,
             'L8USGS': 13,
             'S2': 14,
             'MODT': 15,
             'MODAQ': 16}


def info(col):
    """ Pritty prints information about the given collection

    :param col: Collection
    :type col: Collection
    """
    import pprint

    pp = pprint.PrettyPrinter(indent=2)

    print(col.ID)
    pp.pprint(col.kws)


class Collection(object):

    VERROR = ValueError("Collection ID must be one of: {}".format(IDS.values()))

    def __init__(self, **kwargs):

        # All arguments
        self.kws = kwargs

        # Private ID
        self.__ID = None

        # bandid para crear una band que identifique a la col
        # self.col_id = kwargs.get("col_id", None)

        # Name of the process applied to the collection
        self.process = kwargs.setdefault("process", None)

        # Satellite family ('landsat', 'sentinel', 'modis')
        self.family = kwargs.setdefault("family", None)

        # Function to apply the cloud mask
        self.fclouds = kwargs.setdefault("fclouds", {})

        # Name of the metadata that hold the 'CLOUD_COVER' information
        self.clouds_fld = kwargs.setdefault("clouds_fld", None)

        # Band that holds the cloud mask
        self.clouds_band = kwargs.setdefault("clouds_band", None)

        # Short name of the satellite collection
        self.short = kwargs.setdefault("short", None)

        # Collection id
        self.col_id = SAT_CODES[self.short]

        # Common bands
        self.NIR = kwargs.setdefault("NIR", None)
        self.SWIR = kwargs.setdefault("SWIR", None)
        self.RED = kwargs.setdefault("RED", None)
        self.BLUE = kwargs.setdefault("BLUE", None)
        self.SWIR2 = kwargs.setdefault("SWIR2", None)
        self.GREEN = kwargs.setdefault("GREEN", None)
        self.ATM_OP = kwargs.setdefault("ATM_OP", None)  # Atmospheric Opacity

        # Thresholds
        # self.cloud_th = kwargs.get("cloud_th", None)
        # self.shadow_th = kwargs.get("shadow_th", None)

        # Thresholds
        self.threshold = kwargs.setdefault('threshold', None)

        # Bands that should be scaled
        self.to_scale = kwargs.setdefault("to_scale", None)

        # COLECCION TOA EQUIVALENTE
        # self.equiv = kwargs.get("equiv", None)

        # Visualization properties
        self.bandvizNSR = [self.NIR, self.SWIR, self.RED]
        self.min = kwargs.setdefault("min", 0)
        self.max = kwargs.setdefault("max", None)

        # A single scale that represents the collection
        self.scale = kwargs.setdefault("scale", None)

        # Bands scales
        self.bandscale = kwargs.setdefault("bandscale", None)

        # Band that holds the original mask (Some collections come with a
        # masked band
        self.bandmask = kwargs.setdefault("bandmask", None)

        # Are bands renamed?
        self._renamed = False

        # Original band's names relation
        self.bandasrel_original = {"BLUE": self.BLUE,
                                   "GREEN": self.GREEN,
                                   "RED": self.RED,
                                   "NIR": self.NIR,
                                   "SWIR": self.SWIR,
                                   "SWIR2": self.SWIR2,
                                   "ATM_OP": self.ATM_OP}

        self.bandsrel = {v: k for k, v in self.bandasrel_original.items() if v is not None}
        # self._bandasrel = None

        # Launch and end year
        self.ini = kwargs.setdefault("ini", None)
        self.end = kwargs.setdefault("end", None)

        # Create dictionaries
        self.set_dicts()

    def set_dicts(self):
        # Indexes
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
        self.bandsrel = {v: k for k, v in self.bandsrel.items() if v is not None}

    @property
    def bandIDimg(self):
        return ee.Image.constant(self.col_id).select([0], ["col_id"])

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
                "The collection already has ID '{}'".format(self.__ID) + \
                " and cannot be modified")

        elif id in IDS.values():
            self.__ID = id

        else:
            # raise Collection.VERROR
            raise ValueError(
                "ID must be one of: {}".format(
                    list(IDS.values())))

    @property
    def bands(self):
        """
        :return: Band names of images in the collection
        :rtype: list
        """
        if initialized:
            return ee.Image(self.colEE.first()).bandNames().getInfo()
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
            # return Collection._OPTIONS.index(self.ID) + 1
            return SAT_CODES[self.short]
        except:
            raise ValueError(
                "{} is not in {}".format(self.ID, list(IDS.values())))

    @property
    def colEE(self):
        """ Original Earth Engine Collection """
        if initialized:
            ''' TODO
            if not self.renamed:
                self.proxyColEE = ee.ImageCollection(self.ID).map(self.rename())
                return self.proxyColEE
            else:
                return self.proxyColEE
            '''
            try:
                return self.colEE_proxy
            except:
                self.colEE_proxy = ee.ImageCollection(self.ID)
                return self.colEE_proxy
        else:
            return None

    # FUNCIONES PARA MAPEAR EL INDICE DE VEGETACION
    @property
    def ndvi(self):
        """ Funcion para calcular el ndvi usando map() """
        if self.NIR and self.RED and initialized:
            return indices.ndvi(self.NIR, self.RED)
        else:
            return None

    @property
    def nbr(self):
        """ Funcion para calcular el nbr usando map() """
        if self.NIR and self.SWIR2 and initialized:
            return indices.nbr(self.NIR, self.SWIR2)
        else:
            return None

    @property
    def evi(self):
        """ Funcion para calcular el evi usando map() """
        if self.NIR and self.RED and self.BLUE and initialized:
            return indices.evi(self.NIR, self.RED, self.BLUE)
        else:
            return None

    @property
    def indexrel(self):
        rel = {'ndvi': self.ndvi,
               'evi': self.evi,
               'nbr': self.nbr}
        return rel

    # NORMAL METHOD
    def rename(self, drop=False):
        """ Renames the bands for its equivalent names

        :param drop:
        :return:
        :rtype: function
        """
        # drop = drop
        # Redefine self.bandsrel
        # self.bandsrel = {v: k for k, v in self.bandsrel.items() if v is not None}

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

        # print(self.ATM_OP)

        # Redefine to_scale
        self.to_scale = [self.bandsrel[i] for i in self.to_scale]
        self.bandmask = self.bandsrel[self.bandmask]

        # function to rename bands before invert them
        frename = functions.rename_bands(self.bandsrel, drop)
        # frename = tools.Mapping.renameDict(self.bandsrel)

        # Invierte la relation entre las bands
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
                escalables = tools.ee_list.intersection(
                    img.bandNames(), ee.List(self.to_scale))

                return tools.image.parametrize(img,
                    rango_orig, final_range, escalables)
            return wrap
        else:
            return lambda x: x

    @staticmethod
    def from_id(id):
        """ Create a Collection object giving an ID

        :param id: Same as Google Earth Engine. Options in IDS.values()
        :type id: str
        :return: the object
        :rtype: Collection
        """
        rel = {IDS['L1']: Collection.Landsat1,
               IDS['L2']: Collection.Landsat2,
               IDS['L3']: Collection.Landsat3,
               IDS['L4TOA']: Collection.Landsat4TOA,
               IDS['L4USGS']: Collection.Landsat4USGS,
               IDS['L5TOA']: Collection.Landsat5TOA,
               IDS['L5USGS']: Collection.Landsat5USGS,
               # IDS['L5LED']: Collection.Landsat5LEDAPS,
               IDS['L7TOA']: Collection.Landsat7TOA,
               IDS['L7USGS']: Collection.Landsat7USGS,
               # IDS['L7LED']: Collection.Landsat7LEDAPS,
               IDS['L8TOA']: Collection.Landsat8TOA,
               IDS['L8USGS']: Collection.Landsat8USGS,
               IDS['S2']: Collection.Sentinel2,
               IDS['MODT']: Collection.ModisTerra,
               IDS['MODAQ']: Collection.ModisAqua
               }

        try:
            return rel[id]()
        except Exception as e:
            raise e

    @classmethod
    def Landsat1(cls):
        # id = "LANDSAT/LM1_L1T"
        bandscale = dict(B4=80, B5=80, B6=80, B7=80)
        obj = cls(GREEN="B4",
                  RED="B5",
                  NIR="B6",
                  SWIR="B7",
                  process="RAW",
                  to_scale= ["B4", "B5", "B6", "B7"],
                  clouds_fld="CLOUD_COVER",
                  max=255,
                  scale=80,
                  bandscale=bandscale,
                  bandmask="B4",
                  family="Landsat",
                  ini=1972,
                  end=1978,
                  short="L1")

        obj.ID = IDS[obj.short]  # "LANDSAT/LM1_L1T"
        return obj

    @classmethod
    def Landsat2(cls):
        copy = deepcopy(Collection.Landsat1())  # L1
        copy.kws["ini"] = 1975
        copy.kws["end"] = 1983
        copy.kws["short"] = "L2"
        obj = cls(**copy.kws)

        # CAMBIO
        # obj.ID = IDS['L2']  # "LANDSAT/LM2_L1T"
        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat3(cls):
        copy = deepcopy(Collection.Landsat1())  # L1
        copy.kws["bandscale"] = dict(B4=40, B5=40, B6=40, B7=40)
        copy.kws["scale"] = 40
        copy.kws["ini"] = 1978
        copy.kws["end"] = 1983
        copy.kws["short"] = "L3"
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat4TOA(cls):
        bandscale = dict(B1=30, B2=30, B3=30, B4=30, B5=30, B6=120, B7=30)
        obj = cls(BLUE="B1",
                  GREEN="B2",
                  RED="B3",
                  NIR="B4",
                  SWIR="B5",
                  SWIR2="B7",
                  to_scale=["B1", "B2", "B3", "B4", "B5", "B7"],
                  clouds_fld="CLOUD_COVER",
                  fclouds={'computed_ee': cld.landsat457TOA_BQA()},
                  clouds_band='BQA',
                  process="TOA",
                  max=1,
                  scale=30,
                  bandscale=bandscale,
                  bandmask="B1",
                  family="Landsat",
                  ini=1982,
                  end=1993,
                  short="L4TOA",
                  threshold = {'NIR': {'min':0.07, 'max':0.45},
                               'RED':{'min':0.005, 'max':0.2},
                               'SWIR':{'min':0.04, 'max':0.35},
                               'SWIR2':{'min':0.015, 'max':0.28},
                               'BLUE':{'min':0, 'max':0.1},
                               'GREEN':{'min':0.01, 'max':0.15}})

        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat4USGS(cls):
        copy = deepcopy(Collection.Landsat4TOA())
        copy.kws["short"] = "L4USGS"
        copy.kws["max"] = 10000
        copy.kws["fclouds"] = {'computed_ee': cld.landsat457SR_pixelQA()}
        copy.kws["ATM_OP"] = "sr_atmos_opacity"
        copy.kws["equiv"] = IDS['L4TOA']
        copy.kws["clouds_band"] = "pixel_qa"
        copy.kws["threshold"] = {'NIR': {'min':700, 'max':4500},
                                 'RED':{'min':50, 'max':2000},
                                 'SWIR':{'min':400, 'max':3500},
                                 'SWIR2':{'min':150, 'max':2800},
                                 'BLUE':{'min':0, 'max':1000},
                                 'GREEN':{'min':100, 'max':1500}}
        obj = cls(**copy.kws)

        # CAMBIO
        # obj.ID = "LANDSAT/LT04/C01/T1_SR"
        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat5TOA(cls):
        copy = deepcopy(Collection.Landsat4TOA())
        copy.kws["ini"] = 1984
        copy.kws["end"] = 2013
        copy.kws["short"] = "L5TOA"
        # Thresholds remain the same as L4TOA by now (TODO)
        copy.kws["threshold"] = {'NIR': {'min':0.07, 'max':0.45},
                                 'RED':{'min':0.005, 'max':0.2},
                                 'SWIR':{'min':0.04, 'max':0.35},
                                 'SWIR2':{'min':0.015, 'max':0.28},
                                 'BLUE':{'min':0, 'max':0.1},
                                 'GREEN':{'min':0.01, 'max':0.15}}

        obj = cls(**copy.kws)
        # CAMBIO
        # obj.ID = "LANDSAT/LT5_L1T_TOA_FMASK"
        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat5USGS(cls):
        copy = deepcopy(Collection.Landsat5TOA())  # L5 TOA
        copy.kws["process"] = "SR"
        copy.kws["max"] = 10000
        copy.kws["fclouds"] = {'computed_ee': cld.landsat457SR_pixelQA()}
        copy.kws["ATM_OP"] = "sr_atmos_opacity"
        copy.kws["equiv"] = IDS['L5TOA']
        copy.kws["clouds_band"] = "pixel_qa"
        copy.kws["short"] = "L5USGS"
        copy.kws["threshold"] = {'NIR': {'min':700, 'max':4500},
                                 'RED':{'min':50, 'max':2000},
                                 'SWIR':{'min':400, 'max':3500},
                                 'SWIR2':{'min':150, 'max':2800},
                                 'BLUE':{'min':0, 'max':1000},
                                 'GREEN':{'min':100, 'max':1500}}
        obj = cls(**copy.kws)

        # CAMBIO
        # obj.ID = "LANDSAT/LT05/C01/T1_SR"
        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat7TOA(cls):
        copy = deepcopy(Collection.Landsat5TOA()) # copy L5 TOA
        copy.kws["bandscale"] = dict(B1=30, B2=30, B3=30, B4=30, B5=30, B6=60,
                                     B7=30, B8=15)
        copy.kws["ini"] = 1999
        copy.kws["end"] = ACTUAL_YEAR
        copy.kws["short"] = "L7TOA"
        copy.kws["threshold"] = {'NIR': {'min':0.07, 'max':0.45},
                                 'RED':{'min':0.005, 'max':0.2},
                                 'SWIR':{'min':0.04, 'max':0.35},
                                 'SWIR2':{'min':0.015, 'max':0.28},
                                 'BLUE':{'min':0, 'max':0.1},
                                 'GREEN':{'min':0.01, 'max':0.15}}
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def Landsat7USGS(cls):
        copy = deepcopy(Collection.Landsat7TOA())  # L7 TOA
        copy.kws["equiv"] = IDS['L7TOA']
        copy.kws["process"] = "SR"
        copy.kws["max"] = 10000
        copy.kws["fclouds"] = {'computed_ee': cld.landsat457SR_pixelQA()}
        copy.kws["ATM_OP"] = "sr_atmos_opacity"
        copy.kws["clouds_band"] = "pixel_qa"
        copy.kws["short"] = "L7USGS"
        copy.kws["threshold"] = {'NIR': {'min':700, 'max':4500},
                                 'RED':{'min':50, 'max':2000},
                                 'SWIR':{'min':400, 'max':3500},
                                 'SWIR2':{'min':150, 'max':2800},
                                 'BLUE':{'min':0, 'max':1000},
                                 'GREEN':{'min':100, 'max':1500}}
        obj = cls(**copy.kws)

        # CAMBIO
        obj.ID = IDS[obj.short]

        return obj

    @classmethod
    def Landsat8TOA(cls):
        bandscale = dict(B1=30, B2=30, B3=30, B4=30, B5=30, B6=30, B7=30,
                         B8=15, B9=30, B10=100, B11=100)
        obj = cls(BLUE="B2",
                  GREEN="B3",
                  RED="B4",
                  NIR="B5",
                  SWIR="B6",
                  SWIR2="B7",
                  to_scale=["B2", "B3", "B4", "B5", "B6", "B7"],
                  clouds_fld="CLOUD_COVER",
                  fclouds={'computed_ee': cld.landsat8TOA_BQA()},
                  clouds_band='BQA',
                  process="TOA",
                  max=1,
                  scale=30,
                  bandscale=bandscale,
                  bandmask="B2",
                  family="Landsat",
                  ini=2013,
                  end=ACTUAL_YEAR,
                  short="L8TOA",
                  threshold = {'NIR': {'min':0.07, 'max':0.45},
                               'RED':{'min':0.005, 'max':0.2},
                               'SWIR':{'min':0.04, 'max':0.35},
                               'SWIR2':{'min':0.015, 'max':0.28},
                               'BLUE':{'min':0, 'max':0.1},
                               'GREEN':{'min':0.01, 'max':0.15}})

        # CAMBIOS
        obj.ID = IDS[obj.short]

        return obj

    @classmethod
    def Landsat8USGS(cls):
        copy = deepcopy(Collection.Landsat8TOA())  # L8 TOA
        copy_usgs = deepcopy(Collection.Landsat5USGS())  # L5 USGS
        copy.kws["process"] = copy_usgs.process
        copy.kws["max"] = copy_usgs.max
        copy.kws["fclouds"] = {'computed_ee': cld.landsat8SR_pixelQA()}
        copy.kws["equiv"] = IDS['L8TOA']
        copy.kws["bandscale"] = copy.bandscale
        copy.kws["short"] = "L8USGS"
        copy.kws["clouds_band"] = "pixel_qa"
        copy.kws["threshold"] = {'NIR': {'min':700, 'max':4500},
                                 'RED':{'min':50, 'max':2000},
                                 'SWIR':{'min':400, 'max':3500},
                                 'SWIR2':{'min':150, 'max':2800},
                                 'BLUE':{'min':0, 'max':1000},
                                 'GREEN':{'min':100, 'max':1500}}
        obj = cls(**copy.kws)

        # CAMBIOS
        obj.ID = IDS[obj.short]

        return obj

    @classmethod
    def Sentinel2(cls):
        bandscale = dict(B1=60, B2=10, B3=10, B4=10, B5=20, B6=20, B7=20,
                         B8=10, B8a=20, B9=60, B10=60, B11=20, B12=20)

        obj = cls(BLUE="B2",
                  GREEN="B3",
                  RED="B4",
                  NIR="B8",
                  SWIR="B11",
                  SWIR2="B12",
                  to_scale=["B2", "B3", "B4", "B8", "B11", "B12"],
                  process="TOA",
                  clouds_fld="CLOUD_COVERAGE_ASSESSMENT",
                  max=10000,
                  fclouds= {'computed_ee':cld.sentinel2(),
                            'hollstein':cld.hollstein_S2()},
                  scale=10,
                  bandscale=bandscale,
                  bandmask="B2",
                  family="Sentinel",
                  ini=2015,
                  end=ACTUAL_YEAR,
                  short="S2",
                  threshold = {'NIR': {'min':700, 'max':4500},
                               'RED':{'min':50, 'max':2000},
                               'SWIR':{'min':400, 'max':3500},
                               'SWIR2':{'min':150, 'max':2800},
                               'BLUE':{'min':0, 'max':1000},
                               'GREEN':{'min':100, 'max':1500}},
                  )

        obj.ID = IDS[obj.short]

        return obj

    @classmethod
    def ModisTerra(cls):
        bandscale = dict(sur_refl_b03=500, sur_refl_b04=500, sur_refl_b01=500,
                         sur_refl_b02=500, sur_refl_b06=500, sur_refl_b07=500)

        obj = cls(BLUE="sur_refl_b03",
                  GREEN="sur_refl_b04",
                  RED="sur_refl_b01",
                  NIR="sur_refl_b02",
                  SWIR="sur_refl_b06",
                  SWIR2="sur_refl_b07",
                  process="SR",
                  scale=500,
                  max=5000,
                  bandscale=bandscale,
                  bandmask="sur_refl_b06",
                  family="Modis",
                  ini=1999,
                  short="MODT",
                  to_scale=["sur_refl_b01", "sur_refl_b02", "sur_refl_b03",
                            "sur_refl_b04", "sur_refl_b06", "sur_refl_b07"],
                  fclouds={'computed_ee':cld.modis09ga()},
                  threshold = {'NIR': {'min':700, 'max':4500},
                               'RED':{'min':50, 'max':2000},
                               'SWIR':{'min':400, 'max':3500},
                               'SWIR2':{'min':150, 'max':2800},
                               'BLUE':{'min':0, 'max':1000},
                               'GREEN':{'min':100, 'max':1500}},)

        obj.ID = IDS[obj.short]
        return obj

    @classmethod
    def ModisAqua(cls):
        copy = deepcopy(Collection.ModisTerra())
        copy.kws["ini"] = 2002
        copy.kws["short"] = "MODAQ"
        # copy.kws["col_id"] = 15
        obj = cls(**copy.kws)

        # CAMBIO
        # obj.ID = "MODIS/006/MYD09GA"
        obj.ID = IDS[obj.short]

        return obj


class ColGroup(object):
    """ Grouped collections

    :param scale: Scale to use for all collections inside the group
    :type scale: int

    :param collections: grouped collections
    :type collections: tuple

    :param IDS: list of IDs
    :type IDS: list
    """

    def __init__(self, collections=None, scale=None, **kwargs):
        """ Grouped collections """
        self.scale = scale
        self.collections = collections

    @staticmethod
    def options():
        import pprint
        pp = pprint.PrettyPrinter()
        pp.pprint(GROUPS)

    @property
    def ids(self):
        if self.collections:
            return [c.ID for c in self.collections]
        else:
            return None

    def bandsrel(self):
        """ Matching bands throghout the collections

        Example
        -------

        - collections:
            - Landsat 1 (GREEN, RED, NIR, SWIR)
            - Landsat 4 (BLUE, GREEN, RED, NIR, SWIR, SWIR2)
            - Landsat 8 (BLUE, GREEN, RED, NIR, SWIR, SWIR2)
        - bandasrel: [GREEN, RED, NIR, SWIR]

        :return: names of the matching bands
        :rtype: list
        """
        # diccionario de relaciones de la primer coleccion
        rel = self.collections[0].bandasrel_original

        # Bandas
        bandas = [k for k, v in rel.items() if v is not None]
        s = set(bandas)

        for i, c in enumerate(self.collections):
            if i == 0: continue
            rel = c.bandasrel_original
            bandas = [k for k, v in rel.items() if v is not None]
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
        """ All Landsat Collection """
        col = (Collection.Landsat1(),
               Collection.Landsat2(),
               Collection.Landsat3(),
               Collection.Landsat4TOA(),
               Collection.Landsat4USGS(),
               Collection.Landsat5TOA(),
               Collection.Landsat5USGS(),
               # Collection.Landsat5LEDAPS(),
               Collection.Landsat7TOA(),
               Collection.Landsat7USGS(),
               # Collection.Landsat7LEDAPS(),
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
        """ All collections except Modis (Landsat + Sentinel) """
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
        col = (Collection.Landsat4USGS(),
               Collection.Landsat5USGS(),
               # Collection.Landsat5LEDAPS(),
               Collection.Landsat7USGS(),
               # Collection.Landsat7LEDAPS(),
               Collection.Landsat8USGS())
        return cls(collections=col, scale=30)

    @classmethod
    def Sentinel2(cls):
        """ Only Sentinel 2 inside a Collection Group """
        col = (Collection.Sentinel2(),)
        return cls(collections=col, scale=10)

    @classmethod
    def Modis(cls):
        """ All Modis collections """
        col = (Collection.ModisAqua(),
               Collection.ModisTerra())
        return cls(collections=col, scale=500)

    @classmethod
    def All(cls):
        """ All collections """
        landsat = ColGroup.Landsat().collections
        sen = (Collection.Sentinel2(),)
        mod = ColGroup.Modis().collections

        col = landsat+sen+mod
        return cls(collections=col, scale=10)


GROUPS = {'Landsat': [col.ID for col in ColGroup.Landsat().collections],
          'MSS': [col.ID for col in ColGroup.MSS().collections],
          'Landsat_Sentinel': [col.ID for col in ColGroup.Landsat_Sentinel().collections],
          'TOA': [col.ID for col in ColGroup.TOA().collections],
          'SR': [col.ID for col in ColGroup.SR().collections],
          'Sentinel2': [col.ID for col in ColGroup.Sentinel2().collections],
          'Modis': [col.ID for col in ColGroup.Modis().collections],
          'All': [col.ID for col in ColGroup.All().collections]}
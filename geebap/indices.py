#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Module containing vegetation indixes calculations """
import ee

import ee.data
if not ee.data._initialized: ee.Initialize()

NDVI_EXP = "(NIR-RED)/(NIR+RED)"
EVI_EXP = "G*((NIR-RED)/(NIR+(C1*RED)-(C2*BLUE)+L))"
NBR_EXP = "(NIR-SWIR)/(NIR+SWIR)"


def ndvi(nir, red, addBand=True):
    """ Calculates NDVI index

    :USE:

    .. code:: python

        # use in a collection
        col = ee.ImageCollection(ID)
        ndvi = col.map(indices.ndvi("B4", "B3"))

        # use in a single image
        img = ee.Image(ID)
        ndvi = Indices.ndvi("NIR", "RED")(img)

    :param nir: name of the Near Infrared () band
    :type nir: str
    :param red: name of the red () band
    :type red: str
    :param addBand: if True adds the index band to the others, otherwise
        returns just the index band
    :type addBand: bool
    :return: The function to apply a map() over a collection
    :rtype: function
    """
    addBandEE = ee.Number(1) if addBand else ee.Number(0)

    def calc(img):
        nd = img.expression(NDVI_EXP, {
            "NIR": img.select(nir),
            "RED": img.select(red)
        }).select([0], ["ndvi"])
        result = ee.Algorithms.If(addBandEE, img.addBands(nd), nd)
        return ee.Image(result)

    return calc


def evi(nir, red, blue, G=2.5, C1=6, C2=7.5, L=1, addBand=True):
    """ Calculates EVI index

    :param nir: name of the Near Infrared () band
    :type nir: str
    :param red: name of the red () band
    :type red: str
    :param blue: name of the blue () band
    :type blue: str
    :param G: G coefficient for the EVI index
    :type G: float
    :param C1: C1 coefficient for the EVI index
    :type C1: float
    :param C2: C2 coefficient for the EVI index
    :type C2: float
    :param L: L coefficient for the EVI index
    :type L: float
    :param addBand: if True adds the index band to the others, otherwise
        returns just the index band
    :return: The function to apply a map() over a collection
    :rtype: function
    """
    G = float(G)
    C1 = float(C1)
    C2 = float(C2)
    L = float(L)

    addBandEE = ee.Number(1) if addBand else ee.Number(0)

    def calc(img):
        nd = img.expression(EVI_EXP, {
            "NIR": img.select(nir),
            "RED": img.select(red),
            "BLUE": img.select(blue),
            "G": ee.Number(G),
            "C1": ee.Number(C1),
            "C2": ee.Number(C2),
            "L": ee.Number(L)
        }).select([0], ["evi"])
        result = ee.Algorithms.If(addBandEE, img.addBands(nd), nd)
        return ee.Image(result)

    return calc


def nbr(nir, swir, addBand=True):
    """ Calculates NBR index

    :USE:

    .. code:: python

        # use in a collection
        col = ee.ImageCollection(ID)
        ndvi = col.map(indices.ndvi("B4", "B3"))

        # use in a single image
        img = ee.Image(ID)
        ndvi = Indices.ndvi("NIR", "RED")(img)

    :param nir: name of the Near Infrared () band
    :type nir: str
    :param red: name of the red () band
    :type red: str
    :param addBand: if True adds the index band to the others, otherwise
        returns just the index band
    :type addBand: bool
    :return: The function to apply a map() over a collection
    :rtype: function
    """
    addBandEE = ee.Number(1) if addBand else ee.Number(0)

    def calc(img):
        nd = img.expression(NBR_EXP, {
            "NIR": img.select(nir),
            "SWIR": img.select(swir),
        }).select([0], ["nbr"])
        result = ee.Algorithms.If(addBandEE, img.addBands(nd), nd)
        return ee.Image(result)

    return calc


REL = {"ndvi": ndvi,
       "evi": evi,
       "nbr": nbr
      }

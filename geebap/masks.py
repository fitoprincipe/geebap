#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Module containing the classes
Modulo que contiene las clases para las mascaras a aplicar en la generacion
del compuesto BAP """
import ee

import ee.data
if not ee.data._initialized: ee.Initialize()

import satcol
from abc import ABCMeta, abstractmethod

class Mask(object):
    __metaclass__ = ABCMeta
    """ Clase base para las mascaras """
    def __init__(self, nombre="masks", **kwargs):
        self.nombre = nombre

    @abstractmethod
    def map(self, **kwargs):
        pass

class Manual(object):
    pass

class Clouds(Mask):
    """ Mascara de nubes propia de la coleccion """
    def __init__(self, **kwargs):
        super(Clouds, self).__init__(**kwargs)
        self.nombre = "clouds"

    def map(self, col, **kwargs):
        """
        :param col: Coleccion
        :type col: satcol.Collection
        :param kwargs:
        :return: la funcion para enmascarar la/s imagen/es con la mascara de
            nubes que indica el objeto Coleccion
        :rtype: function
        """
        if col.fclouds:
            return col.fclouds
        else:
            return lambda x: x


class Equivalent(Mask):
    """ Use fmask mask from TOA collections in images of LEDAPS collection
    It does not use Joins, but it should -> TODO

    DEPRECATED: New SR collections have fmask information
    """

    def __init__(self, **kwargs):
        super(Equivalent, self).__init__(**kwargs)
        self.nombre = "equivalent"

    def map(self, col, **kwargs):
        """
        :param col: Collection
        :type col: satcol.Collection
        """
        fam = col.family
        tipo = col.process
        equivID = col.equiv

        # if fam == "Landsat" and tipo == "SR" and (colequiv is not None):
        if equivID:
            colequiv = satcol.Collection.from_id(equivID)
            mask = colequiv.clouds_band
            def wrap(img):
                path = img.get("WRS_PATH")
                row = img.get("WRS_ROW")
                # TODO: usar un filtro de EE (ee.Filter)
                dateadq = ee.Date(img.date())
                nextday = dateadq.advance(1, "day")

                filtered = (colequiv.colEE
                .filterMetadata("WRS_PATH", "equals", path)
                .filterMetadata("WRS_ROW", "equals", row)
                .filterDate(dateadq, nextday))

                # TOA = ee.Image(filtered.first())
                newimg = ee.Algorithms.If(
                    filtered.size(),
                    img.updateMask(ee.Image(filtered.first()).select(mask).neq(2)),
                    img)

                # fmask = TOA.select(mask)
                # mascara = fmask.eq(2)
                #return img.updateMask(mascara.Not())
                return ee.Image(newimg)
                ## return img
        else:
            def wrap(img): return img

        return wrap

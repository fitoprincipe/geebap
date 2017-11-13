#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" El funcionamiento de los filters puede ser distinto..
se filtran colecciones, asi que no hay funciones map()
la funcion en comun va a ser apply()
"""

import satcol
import ee


class Filter(object):
    def __init__(self, **kwargs):
        """ Clase base para los filters """
        pass

    def apply(self, colEE, **kwargs):
        pass


class CloudsPercent(Filter):
    def __init__(self, percent=70, **kwargs):
        """ Filtro por porcentaje de cobertura de nubes de la escena

        :param percent: porcentaje
        :param kwargs:
        """
        super(CloudsPercent, self).__init__(**kwargs)
        self.percent = percent

    def apply(self, colEE, **kwargs):
        """

        :param colEE:
        :type colEE: ee.ImageCollection
        :param col:
        :type col: satcol.Collection
        :param kwargs:
        :return:
        """
        col = kwargs.get("col")
        if col.clouds_fld:
            return colEE.filterMetadata(col.clouds_fld, "less_than", self.percent)
        else:
            return colEE


class MaskPercent(Filter):
    def __init__(self, percent=0.7, prop="pmascpor", **kwargs):
        """

        :param percent:
        :param kwargs:
        """
        super(MaskPercent, self).__init__(**kwargs)
        self.percent = percent
        self.prop = prop

    def apply(self, colEE, **kwargs):
        """

        :param colEE:
        :type colEE: ee.ImageCollection
        :param col:
        :type col: satcol.Collection
        :param kwargs:
        :return:
        """
        return colEE.filterMetadata(self.prop, "less_than", self.percent)

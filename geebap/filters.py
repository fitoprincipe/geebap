# -*- coding: utf-8 -*-

""" El funcionamiento de los filtros puede ser distinto..
se filtran colecciones, asi que no hay funciones map()
la funcion en comun va a ser apply()
"""

import satcol
import ee


class Filtro(object):
    def __init__(self, **kwargs):
        """ Clase base para los filtros """
        pass

    def apply(self, colEE, **kwargs):
        pass


class NubesPor(Filtro):
    def __init__(self, percent=70, **kwargs):
        """ Filtro por porcentaje de cobertura de nubes de la escena

        :param percent: porcentaje
        :param kwargs:
        """
        super(NubesPor, self).__init__(**kwargs)
        self.percent = percent

    def apply(self, colEE, **kwargs):
        """

        :param colEE:
        :type colEE: ee.ImageCollection
        :param col:
        :type col: satcol.Coleccion
        :param kwargs:
        :return:
        """
        col = kwargs.get("col")
        if col.nubesFld:
            return colEE.filterMetadata(col.nubesFld, "less_than", self.percent)
        else:
            return colEE


class MascPor(Filtro):
    def __init__(self, percent=0.7, prop="pmascpor", **kwargs):
        """

        :param percent:
        :param kwargs:
        """
        super(MascPor, self).__init__(**kwargs)
        self.percent = percent
        self.prop = prop

    def apply(self, colEE, **kwargs):
        """

        :param colEE:
        :type colEE: ee.ImageCollection
        :param col:
        :type col: satcol.Coleccion
        :param kwargs:
        :return:
        """
        return colEE.filterMetadata(self.prop, "less_than", self.percent)

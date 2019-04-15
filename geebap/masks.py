# -*- coding: utf-8 -*-
""" Module containing the classes
Modulo que contiene las clases para las mascaras a aplicar en la generacion
del compuesto BAP """
from abc import ABCMeta, abstractmethod


class Mask(object):
    """ Base Class for masks """
    __metaclass__ = ABCMeta

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
        :param col: Collection
        :type col: satcol.Collection
        :param algorithm: algorithm to use. Default: all. See
            satcol.Collection.NNN.fclouds
        :param kwargs:
        :return: the function to apply the mask
        :rtype: function
        """
        algorithm = kwargs.get('algorithm', 'computed_ee')
        if col.fclouds:
            return col.fclouds[algorithm]
        else:
            return lambda x: x

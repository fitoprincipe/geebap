# -*- coding: utf-8 -*-

import expgen
from functions import drange, replace
import math
import simpleeval as sval
import numpy as np
import copy
import ee

# FUNCIONES PARA simpleeval
CUSTOM_FUNCTIONS = {"sqrt": math.sqrt,
                    "exp": math.exp,
                    "max": max,
                    "min": min}

CUSTOM_NAMES = {"pi": math.pi}

sval.DEFAULT_FUNCTIONS.update(CUSTOM_FUNCTIONS)
sval.DEFAULT_NAMES.update(CUSTOM_NAMES)


class Expresion(object):
    # TODO: Limitante: si hay mas de una variable
    """ El método principal de Expresiones() es map(**kwargs), el cual define
    la funcion que se usará en ImageCollection.map()

    :param expresion: Expresion en formato texto. Se pueden usar algunas
        variables calculadas de la siguiente forma:

        - {max}: maximo valor del range
        - {min}: minimo valor del range
        - {media}: media del range
        - {std}: desvío estandar del range
        - {maximo}: maximo valor de los resultados

        La variable puede ser solo una, que al momento de aplicar el método
        map() se definirá de donde proviene, y debe incluirse en la expresión
        de la siguiente forma: {var}. Ejemplo:

        |
        `expr = "{var}*{media}/{std}+40"`

        `e = Expresion(expresion=expr, range=(0, 100))`

        `print e.format_local()`

        >> {var}*50.0/28.8963665536+40

    :type expresion: str
    :param rango: Rango de valores entre los que varía la variable
    :type rango: tuple
    :param normalizar: Hacer que los valores (resultado) oscilen entre
        0 y 1 dividiendo los valores por el maximo. Si se quiere
        normalizar se debe proveer un range.
    :type normalizar: bool
    :param kargs: argumentos 'keywords', ej: a=1, b=2

    :Propiedades fijas:
    :param media: Si se provee un range, es la media aritmetica, sino None
    :type media: float
    :param std: Si se provee un range es el desvío estandar, sino None
    :type std: float
    :param maximo: Determinar el maximo resultado posible. Aplicando la
        expresion localmente con la funcion eval()
    :type maximo: float

    :Uso:

    .. code:: python

        # Defino las expresiones con sus rangos
        exp = Expresion.Exponencial(range=(0, 100))
        exp2 = Expresion.Exponencial(range=(0, 5000), normalizar=True)

        # Defino las funciones, indicando el nombre de la banda resultante
        # y la variable que se usará para el cálculo
        fmap = exp.map("otronombre", prop="CLOUD_COVER")
        fmap2 = exp2.map("nombre", banda="NIR")

        # Mapeo los resultados
        newcol = imgcol.map(fmap)
        newcol2 = imgcol.map(fmap2)

    :Operadores:
    :\+ \- * / % **:    Add, Subtract, Multiply, Divide, Modulus, Exponent
    :== != < > <= >=:   Equal, Not Equal, Less Than, Greater than, etc.

    :Constantes:
    :pi: pi (3.1415)
    :e: euler (2.71)

    :Funciones admitidas:
    :max: maximo valor entre dos argumentos
    :min: minimo valor entre dos argumentos
    :exp: exponencial de e: e^argumento
    :sqrt: raiz cuadrada del argumento
    """
    def __init__(self, expresion="{var}", normalizar=False, rango=None,
                 nombre=None, **kwargs):
        self.expresion = expresion
        self.rango = rango
        self._normalizar = normalizar
        self.parametros = kwargs
        self._max = kwargs.get("max")
        self._min = kwargs.get("min")
        self._std = kwargs.get("std")
        self._media = kwargs.get("media")
        self.nombre = nombre

    def format_local(self):
        """ Reemplaza las variables de la expresion por los valores asignados
        al objeto, excepto la variable 'var' que la deja como está porque es
        la que variará en la expresion de EE"""
        # print self.expresion
        # reemplaza las variables estadisticas
        params = copy.deepcopy(self.parametros)
        params["max"] = self.max
        params["min"] = self.min
        params["media"] = self.media
        params["std"] = self.std

        return self.expresion.format(var="{var}", **params)

    def format_ee(self):
        """ Reemplaza las variables de la expresion por los valores asignados
        al objeto y genera la expresion lista para usar en Earth Engine """
        # reemplaza las variables estadisticas
        params = copy.deepcopy(self.parametros)
        params["max"] = self.max
        params["min"] = self.min
        params["media"] = self.media
        params["std"] = self.std

        expr = self.expresion.format(var="'var'", **params)

        return expgen.ExpGen.parse(expr)

        # return sval.simple_eval("")

    @staticmethod
    def ajustar(nombre, valor):
        """ Ajusta el valor de la banda resultante multipliandolo por 'valor'

        :param valor: Valor de ajuste
        :type valor: float
        :param nombre: nombre de la banda que contiene el valor a ajustar
        :type nombre: str
        :return: La funcion para map()
        :rtype: function
        """
        def wrap(img):
            band = img.select(nombre).multiply(valor)
            return replace(nombre, band)(img)

        return wrap

    @property
    def normalizar(self):
        """
        :rtype: bool
        """
        return self._normalizar

    @normalizar.setter
    def normalizar(self, value):
        """ Metodo para setear el valor de la propiedad 'normalizar' """
        if type(value) is bool and type(self.rango) is tuple:
            self._normalizar = value
        else:
            self._normalizar = False
            print "Si se desea normalizar la funcion, el range debe ser una " \
                  "tupla"

    # ESTADISTICAS DEL RANGO
    @property
    def media(self):
        if type(self.rango) is tuple:
            r = drange(self.rango[0], self.rango[1]+1, places=1)
            return np.mean(r)
        elif self._media:
            return self._media
        else:
            raise ValueError("Para determinar la media el parametro 'range'"
                             " debe ser del tipo tuple")

    @property
    def std(self):
        if type(self.rango) is tuple:
            r = drange(self.rango[0], self.rango[1]+1, places=1)
            return np.std(r)
        elif self._std:
            return self._std
        else:
            raise ValueError("Para determinar el desvio el parametro 'range'"
                             " debe ser del tipo tuple")

    @property
    def maximo(self):
        """ Determinar el maximo resultado posible. Aplicando la expresion
        localmente con la funcion eval()

        :return:
        """
        if type(self.rango) is tuple:
            rango = self.rango
        elif self._max and self._min:
            rango = (self._min, self._max)
        else:
            raise ValueError("Para determinar el maximo el parametro 'range'"
                             " debe ser del tipo tuple")

        r = drange(rango[0], rango[1]+1, places=1)
        lista_result = [self.eval(var) for var in r]
        maximo = max(lista_result)
        return maximo

    @property
    def max(self):
        """ Maximo valor del range """
        val = self.rango[1] if self.rango else self.parametros.get("max", None)
        return val

    @property
    def min(self):
        """ Minimo valor del range """
        val = self.rango[0] if self.rango else self.parametros.get("min", None)
        return val

    def eval(self, var):
        """ Metodo para aplicar la funcion localmente con un valor dado

        :param var: Valor que se usara como variable
        :return: el resultado de evaluar la expresion con un valor dado
        :rtype: float
        """
        expr = self.format_local()
        expr = expr.format(var=var)
        result = sval.simple_eval(expr)
        return result

    def eval_normalizado(self, var):
        """ Metodo para aplicar la funcion normalizada (resultado entre 0 y 1)
        localmente con un valor dado. No influye el parametro 'normalizar'

        :param var: Valor que se usara como variable
        :return: el resultado de evaluar la expresion con un valor dado
        :rtype: float
        """
        e = self.format_local()
        expr = "({e})/{maximo}".format(e=e, maximo=self.maximo)
        expr = expr.format(var=var)
        result = sval.simple_eval(expr)
        return result

    def map(self, nombre="expresion", banda=None, prop=None, eval=None,
            map=None, **kwargs):
        """ Funcion para mapear el resultado de la expresion

        :param nombre: nombre que se le dara a la banda de la imagen una vez
            calculada la expresion
        :type nombre: str
        :param banda: nombre de la banda que se usara como valor variable
        :type banda: str
        :param prop: nombre de la propiedad que se usara como valor variable
        :type prop: str
        :param eval: funcion para aplicar a la variable. Si la variable es el
            valor de una banda, entonces el argumento de la funcion será
            esa banda, y si es una propiedad, el argumento será la propiedad.
        :type eval: function
        :param map: funcion para aplicarle al valor final. Puede usarse para
            hacer un ajuste o ponderacion. El argumento de la funcion debe ser
            la imagen con la banda agregada
        :type map: function
        :return: la funcion para map()
        :rtype: function
        """
        # Define la funcion para aplicarle a la variable
        if eval is None:
            func = lambda x: x
        elif callable(eval):
            func = eval
        else:
            raise ValueError("el parametro 'eval' debe ser una funcion")

        # Define la funcion para aplicar
        # print "map:", map

        if map is None:
            finalf = lambda x: x
        elif callable(map):
            finalf = map
        else:
            raise ValueError("el parametro 'map' debe ser una funcion")

        # reemplazo las variables de la expresion
        expr = self.format_ee()

        # Normalizar
        if self.normalizar:
            expr = "({e})/{maximo}".format(e=expr, maximo=self.maximo)
        else:
            expr = expr

        # print "nombre", nombre
        # print "propiedad", prop
        # print "expresion", expr
        # Define la funcion de retorno según si se eligio una propiedad o una banda
        if prop is None and banda is not None:  # BANDA
            def wrap(img):
                # Selecciono los pixeles con valor distinto de cero
                ceros = img.select([0]).eq(0).Not()

                # aplico la funcion 'eval' a la banda
                variable = func(img.select(banda))
                # aplico la expresion
                '''
                calculo = img.expression(expr,
                                         dict(var=variable, **self.parametros))
                '''

                calculo = img.expression(expr, dict(var=variable))

                # renombro
                calculo = calculo.select([0], [nombre])
                # aplico la funcion final sobre la imagen completa
                imgfinal = finalf(img.addBands(calculo))
                # retorno la imagen con la banda agregada
                return imgfinal.updateMask(ceros)
        elif banda is None and prop is not None:  # PROPIEDAD
            def wrap(img):
                # Selecciono los pixeles con valor distinto de cero
                ceros = img.select([0]).eq(0).Not()
                # aplico la funcion 'eval' a la propiedad
                propval = func(ee.Number(img.get(prop)))
                # aplico la expresion
                '''
                calculo = img.expression(expr,
                                         dict(var=propval, **self.parametros))
                '''
                calculo = img.expression(expr, dict(var=propval))

                # renombro
                calculo = calculo.select([0], [nombre])
                # aplico la funcion final sobre la imagen completa
                imgfinal = finalf(img.addBands(calculo))
                # imgfinal = img.addBands(calculo)
                # retorno la imagen con la banda agregada
                return imgfinal.updateMask(ceros)
        else:
            raise ValueError("la funcion map debe ser llamada con \
                             'banda' o 'prop'")

        return wrap

    @classmethod
    def Exponencial(cls, a=-10, rango=(0, 100), **kwargs):
        """ Funcion Exponencial

        :USO:

        :param var: valor variable
        :param media: valor de la media aritmetica de la variable
        :param a: constante a. El signo determina si el maximo está al final
            de la serie (positivo) o al principio (negativo)
        :param b: constante b. Determina el punto de quiebre de de la curva.
            Cuando es cero, el punto esta en la media de la serie. Cuando es
            positivo se acerca al principio de la serie, y cuando es negativo
            al final de la serie.
        """
        # DETERMINO LOS PARAMETROS SEGUN EL RANGO DADO SI EXISTIERA
        exp = "1.0-(1.0/(exp(((min({var}, {max})-{media})*(1/{max}*{a})))+1.0))"
        return cls(expresion=exp, a=a, rango=rango, nombre="Exponencial",
                   **kwargs)

    @classmethod
    def Gauss(cls, rango=(0, 100), factor=-0.5, **kwargs):
        """ Campana de Gauss

        :param rango: Rango entre los que oscilan los valores de entrada
        :type rango: tuple
        :param factor: factor de 'agusamiento' de la curva. Debe ser menor a
            cero. Cuanto menor sea, mas 'fina' será la curva
        :type factor: float
        :param kwargs:
        :return:
        """
        if factor > 0:
            print "el factor de la curva gaussiana debe ser menor a cero, convirtiendo.."
            factor *= -1
        if not isinstance(rango, tuple):
            raise ValueError("el range debe ser una tupla")

        exp = "exp(((({var}-{media})/{std})**2)*{factor})/(sqrt(2*pi)*{std})"
        return cls(expresion=exp, rango=rango, factor=factor,
                   nombre="Gauss", **kwargs)
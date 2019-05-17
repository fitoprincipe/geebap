# -*- coding: utf-8 -*-
import ee

from . import expgen
from .functions import drange
from geetools import tools
import math
import simpleeval as sval
import numpy as np
import copy

# FUNCIONES PARA simpleeval
CUSTOM_FUNCTIONS = {"sqrt": math.sqrt,
                    "exp": math.exp,
                    "max": max,
                    "min": min}

CUSTOM_NAMES = {"pi": math.pi}

sval.DEFAULT_FUNCTIONS.update(CUSTOM_FUNCTIONS)
sval.DEFAULT_NAMES.update(CUSTOM_NAMES)


class Expression(object):
    # TODO: Limitante: si hay mas de una variable
    """ El método principal de Expresiones() es map(**kwargs), el cual define
    la funcion que se usará en ImageCollection.map()

    :param expresion: Expression en formato texto. Se pueden usar algunas
        variables calculadas de la siguiente forma:

        - {max}: max_result valor del range
        - {min}: minimo valor del range
        - {mean}: mean del range
        - {std}: desvío estandar del range
        - {max_result}: max_result valor de los resultados

        La variable puede ser solo una, que al momento de aplicar el método
        map() se definirá de donde proviene, y debe incluirse en la expresión
        de la siguiente forma: {var}. Ejemplo:

        |
        `expr = "{var}*{mean}/{std}+40"`

        `e = Expression(expression=expr, range=(0, 100))`

        `print e.format_local()`

        >> {var}*50.0/28.8963665536+40

    :type expresion: str
    :param rango: Rango de valores entre los que varía la variable
    :type rango: tuple
    :param normalizar: Hacer que los valores (resultado) oscilen entre
        0 y 1 dividiendo los valores por el max_result. Si se quiere
        normalize se debe proveer un range.
    :type normalizar: bool
    :param kargs: argumentos 'keywords', ej: a=1, b=2

    :Propiedades fijas:
    :param media: Si se provee un range, es la mean aritmetica, sino None
    :type media: float
    :param std: Si se provee un range es el desvío estandar, sino None
    :type std: float
    :param maximo: Determinar el max_result resultado posible. Aplicando la
        expression localmente con la funcion eval()
    :type maximo: float

    :Uso:

    .. code:: python

        # Defino las expresiones con sus rangos
        exp = Expression.Exponential(range=(0, 100))
        exp2 = Expression.Exponential(range=(0, 5000), normalize=True)

        # Defino las funciones, indicando el name de la band resultante
        # y la variable que se usará para el cálculo
        fmap = exp.map("otronombre", prop="CLOUD_COVER")
        fmap2 = exp2.map("name", band="NIR")

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
    :max: max_result valor entre dos argumentos
    :min: minimo valor entre dos argumentos
    :exp: exponencial de e: e^argumento
    :sqrt: raiz cuadrada del argumento
    """
    def __init__(self, expression="{var}", normalize=False, range=None,
                 name=None, **kwargs):
        self.expression = expression
        self.range = range
        self._normalize = normalize
        self.params = kwargs
        self._max = kwargs.get("max")
        self._min = kwargs.get("min")
        self._std = kwargs.get("std")
        self._mean = kwargs.get("mean")
        self.name = name

    def format_local(self):
        """ Reemplaza las variables de la expression por los valores asignados
        al objeto, excepto la variable 'var' que la deja como está porque es
        la que variará en la expression de EE"""
        # print self.expression
        # reemplaza las variables estadisticas
        params = copy.deepcopy(self.params)
        params["max"] = self.max
        params["min"] = self.min
        params["mean"] = self.mean
        params["std"] = self.std

        return self.expression.format(var="{var}", **params)

    def format_ee(self):
        """ Reemplaza las variables de la expression por los valores asignados
        al objeto y genera la expression lista para usar en Earth Engine """
        # reemplaza las variables estadisticas
        params = copy.deepcopy(self.params)
        params["max"] = self.max
        params["min"] = self.min
        params["mean"] = self.mean
        params["std"] = self.std

        expr = self.expression.format(var="'var'", **params)

        return expgen.ExpGen.parse(expr)


    @staticmethod
    def adjust(name, valor):
        """ Ajusta el valor de la band resultante multipliandolo por 'valor'

        :param valor: Valor de adjust
        :type valor: float
        :param name: name de la band que contiene el valor a ajustar
        :type name: str
        :return: La funcion para map()
        :rtype: function
        """
        def wrap(img):
            band = img.select(name).multiply(valor)
            return tools.image.replace(img, name, band)

        return wrap

    @property
    def normalize(self):
        """
        :rtype: bool
        """
        return self._normalize

    @normalize.setter
    def normalize(self, value):
        """ Metodo para setear el valor de la propiedad 'normalize' """
        if type(value) is bool and type(self.range) is tuple:
            self._normalize = value
        else:
            self._normalize = False
            print("If you want to normalize the function, the range must be "
                  " a tuple")

    # ESTADISTICAS DEL RANGO
    @property
    def mean(self):
        if type(self.range) is tuple:
            r = drange(self.range[0], self.range[1] + 1, places=1)
            return np.mean(r)
        elif self._mean:
            return self._mean
        else:
            raise ValueError("To determine the mean the 'range' param must be "
                             "a tuple")

    @property
    def std(self):
        if type(self.range) is tuple:
            r = drange(self.range[0], self.range[1] + 1, places=1)
            return np.std(r)
        elif self._std:
            return self._std
        else:
            raise ValueError("To determine the std the 'range' param must be "
                             "a tuple")

    @property
    def max_result(self):
        """ Determinar el max_result resultado posible. Aplicando la expression
        localmente con la funcion eval()

        :return:
        """
        if type(self.range) is tuple:
            rango = self.range
        elif self._max and self._min:
            rango = (self._min, self._max)
        else:
            raise ValueError("To determine the max result the 'range' param "
                             "must be a tuple")

        r = drange(rango[0], rango[1]+1, places=1)
        lista_result = [self.eval(var) for var in r]
        maximo = max(lista_result)
        return maximo

    @property
    def max(self):
        """ Maximo valor del range """
        val = self.range[1] if self.range else self.params.get("max", None)
        return val

    @property
    def min(self):
        """ Minimo valor del range """
        val = self.range[0] if self.range else self.params.get("min", None)
        return val

    def eval(self, var):
        """ Metodo para aplicar la funcion localmente con un valor dado

        :param var: Valor que se usara como variable
        :return: el resultado de evaluar la expression con un valor dado
        :rtype: float
        """
        expr = self.format_local()
        expr = expr.format(var=var)
        result = sval.simple_eval(expr)
        return result

    def eval_normalized(self, var):
        """ Metodo para aplicar la funcion normalizada (resultado entre 0 y 1)
        localmente con un valor dado. No influye el parametro 'normalize'

        :param var: Valor que se usara como variable
        :return: el resultado de evaluar la expression con un valor dado
        :rtype: float
        """
        e = self.format_local()
        expr = "({e})/{maximo}".format(e=e, maximo=self.max_result)
        expr = expr.format(var=var)
        result = sval.simple_eval(expr)
        return result

    def map(self, name="expression", band=None, prop=None, eval=None,
            map=None, **kwargs):
        """ Funcion para mapear el resultado de la expression

        :param name: name que se le dara a la band de la imagen una vez
            calculada la expression
        :type name: str
        :param band: name de la band que se usara como valor variable
        :type band: str
        :param prop: name de la propiedad que se usara como valor variable
        :type prop: str
        :param eval: funcion para aplicar a la variable. Si la variable es el
            valor de una band, entonces el argumento de la funcion será
            esa band, y si es una propiedad, el argumento será la propiedad.
        :type eval: function
        :param map: funcion para aplicarle al valor final. Puede usarse para
            hacer un adjust o ponderacion. El argumento de la funcion debe ser
            la imagen con la band agregada
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

        # reemplazo las variables de la expression
        expr = self.format_ee()

        # Normalizar
        if self.normalize:
            expr = "({e})/{maximo}".format(e=expr, maximo=self.max_result)
        else:
            expr = expr

        # print "name", name
        # print "propiedad", prop
        # print "expression", expr
        # Define la funcion de retorno según si se eligio una propiedad o una band
        if prop is None and band is not None:  # BANDA
            def wrap(img):
                # Selecciono los pixeles con valor distinto de cero
                ceros = img.select([0]).eq(0).Not()

                # aplico la funcion 'eval' a la band
                variable = func(img.select(band))
                # aplico la expression
                '''
                calculo = img.expression(expr,
                                         dict(var=variable, **self.params))
                '''

                calculo = img.expression(expr, dict(var=variable))

                # renombro
                calculo = calculo.select([0], [name])
                # aplico la funcion final sobre la imagen completa
                imgfinal = finalf(img.addBands(calculo))
                # retorno la imagen con la band agregada
                return imgfinal.updateMask(ceros)
        elif band is None and prop is not None:  # PROPIEDAD
            def wrap(img):
                # Selecciono los pixeles con valor distinto de cero
                ceros = img.select([0]).eq(0).Not()
                # aplico la funcion 'eval' a la propiedad
                propval = func(ee.Number(img.get(prop)))
                # aplico la expression
                '''
                calculo = img.expression(expr,
                                         dict(var=propval, **self.params))
                '''
                calculo = img.expression(expr, dict(var=propval))

                # renombro
                calculo = calculo.select([0], [name])
                # aplico la funcion final sobre la imagen completa
                imgfinal = finalf(img.addBands(calculo))
                # imgfinal = img.addBands(calculo)
                # retorno la imagen con la band agregada
                return imgfinal.updateMask(ceros)
        else:
            raise ValueError("la funcion map debe ser llamada con \
                             'band' o 'prop'")

        return wrap

    @classmethod
    def Exponential(cls, a=-10, range=(0, 100), **kwargs):
        """ Funcion Exponential

        :USO:

        :param var: valor variable
        :param media: valor de la mean aritmetica de la variable
        :param a: constante a. El signo determina si el max_result está al final
            de la serie (positivo) o al principio (negativo)
        :param b: constante b. Determina el punto de quiebre de de la curva.
            Cuando es cero, el punto esta en la mean de la serie. Cuando es
            positivo se acerca al principio de la serie, y cuando es negativo
            al final de la serie.
        """
        # DETERMINO LOS PARAMETROS SEGUN EL RANGO DADO SI EXISTIERA
        exp = "1.0-(1.0/(exp(((min({var}, {max})-{mean})*(1/{max}*{a})))+1.0))"
        return cls(expression=exp, a=a, range=range, name="Exponential",
                   **kwargs)

    @classmethod
    def Normal(cls, range=(0, 100), ratio=-0.5, **kwargs):
        """ Campana de Normal

        :param rango: Rango entre los que oscilan los valores de entrada
        :type rango: tuple
        :param ratio: factor de 'agusamiento' de la curva. Debe ser menor a
            cero. Cuanto menor sea, mas 'fina' será la curva
        :type ratio: float
        :param kwargs:
        :return:
        """
        if ratio > 0:
            print("el ratio de la curva gaussiana debe ser menor a cero, "
                  "convirtiendo..")
            ratio *= -1
        if not isinstance(range, tuple):
            raise ValueError("el range debe ser una tupla")

        exp = "exp(((({var}-{mean})/{std})**2)*{ratio})/(sqrt(2*pi)*{std})"
        return cls(expression=exp, range=range, ratio=ratio,
                   name="Normal", **kwargs)
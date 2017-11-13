#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Date module for Gee Bap """

import functions
import ee


class Date(object):
    """ Agrega una band de name *fecha* de tipo *Uint16* que toma de la
    propiedad *system:time_start* y computa la cantidad de dias que
    transcurrieron a partir del 1970-01-01.
    Agrega a la imagen una propiedad con el id de la imagen llamada 'id_img'

    :metodos:
    :mapfecha: estatico para utilizar con ee.ImageCollection.map()
    """
    oneday_local = 86400000  # milisegundos
    oneday = ee.Number(oneday_local)

    def __init__(self):
        pass

    @staticmethod
    def map(name="date"):
        """
        :PARAMETROS:
        :param name: name que se le dara a la band
        :type name: str
        """
        def wrap(img):
            # BANDA DE LA FECHA
            dateadq = img.date()
            fechadq = ee.Date(dateadq).millis().divide(Date.oneday)
            imgfecha = ee.Image(fechadq).select([0], [name]).toUint16()
            final = img.addBands(imgfecha).set(name, fechadq.toInt())
            return functions.pass_date(img, final)
        return wrap

    @staticmethod
    def local(date):
        """ Dada una fecha obtiene la cantidad de dias desde el comienzo
        de las fechas (01-01-1970)

        :param date: fecha en formato (AAAA-MM-DD)
        :type date: str
        :param unit: unidades en las que se quiere expresar
        :return: dias desde el comienzo de las fechas
        :rtype: int
        """
        d = ee.Date(date)
        mili = d.millis().getInfo()
        return float(mili / Date.oneday_local)


    @staticmethod
    def get(date, unit="days"):
        """ Obtiene la fecha EE de la cantidad de unidades pasadas como
        argumento

        :param date:
        :type date: int
        :param unit:
        :return:
        :rtype: ee.Date
        """
        if unit == "days":
            mili = ee.Number(date).multiply(Date.oneday)
            d = ee.Date(mili)
            dstr = d.format()

            print "{0} days corresponds to the date {1}".format(
                date, dstr.getInfo())
        return d

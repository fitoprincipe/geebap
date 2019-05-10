# -*- coding: utf-8 -*-
""" Date module for Gee Bap """
import ee


class Date(object):
    """ Class holding some custom methods too add a 'date' band in the 'Best
    Available Pixel' compostite.

    Agrega una band de name *fecha* de tipo *Uint16* que toma de la
    propiedad *system:time_start* y computa la cantidad de dias que
    transcurrieron a partir del 1970-01-01.
    Agrega a la imagen una propiedad con el id de la imagen llamada 'id_img'

    :metodos:
    :mapfecha: estatico para utilizar con ee.ImageCollection.map()
    """
    oneday_local = 86400000  # milisegundos
    oneday = ee.Number(oneday_local)

    def __init__(self):
        ''' This Class doesn't initialize '''
        pass

    @staticmethod
    def map(name="date"):
        """
        :param name: name for the new band
        :type name: str
        """
        def wrap(img):
            dateadq = img.date()  # ee.Date
            days_since_70 = ee.Date(dateadq).millis().divide(Date.oneday)  # days since 1970
            dateimg = ee.Image(days_since_70).select([0], [name]).toUint16()
            final = img.addBands(dateimg).set(name, days_since_70.toInt())
            # return functions.pass_date(img, final)
            # return tools.passProperty(img, final, 'system:time_start')
            return final.copyProperties(img, ['system:time_start'])
        return wrap

    @staticmethod
    def local(date):
        """ Number of days since the beggining (1970-01-01)
        Dada una fecha obtiene la cantidad de dias desde el comienzo
        de las fechas (01-01-1970)

        :param date: date (yyyy-MM-dd)
        :type date: str
        :return: days since the beggining
        :rtype: float
        """
        d = ee.Date(date)
        mili = d.millis().getInfo()
        return float(mili / Date.oneday_local)

    @staticmethod
    def get(date, unit="days"):
        """ get the date (ee.Date) of the given value in 'unit'.
        Currentrly ONLY process 'days', so:

        `date.Date.get(365) = '1971-01-01T00:00:00`

        :param date: the value to transform
        :type date: int
        :param unit: date's unit (currently ONLY 'days')
        :return: date corresponding to the given value
        :rtype: ee.Date
        """
        if unit == "days":
            mili = ee.Number(date).multiply(Date.oneday)
            d = ee.Date(mili)
            # dstr = d.format()
        return d

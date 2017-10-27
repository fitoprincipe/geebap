""" Agrega a la imagen una banda con la fecha en un formato propio
La fecha esta expresada en la cantidad de dias que hay a partir de 1970-01-01
Ademas agrega a la imagen una propiedad con el id de la imagen llamada 'id_img'
"""

import funciones
import ee


class FechaEE(object):
    """ Agrega una banda de nombre *fecha* de tipo *Uint16* que toma de la
    propiedad *system:time_start* y computa la cantidad de dias que
    transcurrieron a partir del 1970-01-01.
    Agrega a la imagen una propiedad con el id de la imagen llamada 'id_img'

    :metodos:
    :mapfecha: estatico para utilizar con ee.ImageCollection.map()
    """
    undia_local = 86400000  # milisegundos
    undia = ee.Number(undia_local)

    def __init__(self):
        pass

    @staticmethod
    def map(nombre="fecha"):
        """
        :PARAMETROS:
        :param nombre: nombre que se le dara a la banda
        :type nombre: str
        """
        def wrap(img):
            # BANDA DE LA FECHA
            dateadq = img.date()
            fechadq = ee.Date(dateadq).millis().divide(FechaEE.undia)
            imgfecha = ee.Image(fechadq).select([0], [nombre]).toUint16()
            final = img.addBands(imgfecha).set(nombre, fechadq.toInt())
            return funciones.pass_date(img, final)
        return wrap

    @staticmethod
    def local(fecha):
        """ Dada una fecha obtiene la cantidad de dias desde el comienzo
        de las fechas (01-01-1970)

        :param fecha: fecha en formato (AAAA-MM-DD)
        :type fecha: str
        :param unit: unidades en las que se quiere expresar
        :return: dias desde el comienzo de las fechas
        :rtype: int
        """
        d = ee.Date(fecha)
        mili = d.millis().getInfo()
        return float(mili/FechaEE.undia_local)


    @staticmethod
    def get(fecha, unit="dias"):
        """ Obtiene la fecha EE de la cantidad de unidades pasadas como
        argumento

        :param fecha:
        :type fecha: int
        :param unit:
        :return:
        :rtype: ee.Date
        """
        if unit == "dias":
            mili = ee.Number(fecha).multiply(FechaEE.undia)
            d = ee.Date(mili)
            dstr = d.format()

            print "{0} dias es la fecha {1}".format(fecha, dstr.getInfo())
        return d

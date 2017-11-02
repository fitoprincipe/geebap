#!/usr/bin/env python
# -*- coding: utf-8 -*-
import satcol
import ee
from datetime import date

# IDS
ID1 = "LANDSAT/LM1_L1T"
ID2 = "LANDSAT/LM2_L1T"
ID3 = "LANDSAT/LM3_L1T"
ID4TOA = "LANDSAT/LT4_L1T_TOA_FMASK"
ID5SR = "LANDSAT/LT5_SR"
ID5LED = "LEDAPS/LT5_L1T_SR"
ID5TOA = "LANDSAT/LT5_L1T_TOA_FMASK"
ID7SR = "LANDSAT/LE7_SR"
ID7TOA = "LANDSAT/LE7_L1T_TOA_FMASK"
ID7LED = "LEDAPS/LE7_L1T_SR"
ID8SR = "LANDSAT/LC8_SR"
ID8TOA = "LANDSAT/LC8_L1T_TOA_FMASK"
S2 = "COPERNICUS/S2"


class Temporada(object):
    """ PROTOTIPO """
    #
    dias_mes = {1:31, 2:29, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30,
                10:31, 11:30, 12:31}

    @staticmethod
    def check_valid_date(fecha):
        """ Verifica que la fecha tenga el formato correcto

        :param fecha:
        :return: año, mes, dia
        :rtype: tuple
        """
        if not isinstance(fecha, str):
            # raise ValueError("La fecha no es del tipo string")
            return False

        split = fecha.split("-")
        m = int(split[0])
        d = int(split[1])

        if m < 1 or m > 12:
            raise ValueError(
                "Error en {}: El mes debe ser mayor a 1 y menor a 12".format(fecha))
            # return False
        maxday = Temporada.dias_mes[m]
        if d < 1 or d > maxday:
            raise ValueError(
                "Error en {}: En el mes {} el dia debe ser menor a {}".format(fecha, m, maxday))
            # return False

        return m , d

    @staticmethod
    def check_between(fecha, ini, fin, raiseE=True):
        """ Verifica que la fecha dada este entre la inicial y la final

        :param fecha:
        :param ini:
        :param fin:
        :param raiseE:
        :return:
        """
        retorno = False
        def rerror():
            if raiseE:
                raise ValueError("La fecha {} debe estar entre {} y {}".format(fecha, ini, fin))
            else:
                return

        m, d = Temporada.check_valid_date(fecha)
        mi, di = Temporada.check_valid_date(ini)
        mf, df = Temporada.check_valid_date(fin)
        # valores relativos de mes
        # varia entre 0 y 12
        if mi > mf:
            over = True
        elif mi == mf and di > df:
            over = True
        else:
            over = False

        if not over:
            if (mf > m > mi):
                retorno = True
            elif mf == m and df >= d:
                retorno = True
            elif mi == m and di <= d:
                retorno = True
            else:
                rerror()
        else:
            if m < mf:
                retorno = True
            elif m == mf and d <= df:
                retorno = True
            elif m > mi:
                retorno = True
            elif m == mi and d >= di:
                retorno = True
            else:
                rerror()

        return retorno

    def __init__(self, ini=None, fin=None, doy=None, **kwargs):
        """ Temporada de crecimiento

        :param ini: mes y dia de inicio de la season
        :param fin: mes y dia de fin de la season
        :param doy: mes y dia del dia mas representativo del año
        :param kwargs:
        """

        self.ini = ini
        self.fin = fin

        self.doy = doy

        if ini is not None and fin is not None:
            # Temporada.check_dif_date(ini, fin)
            self._mes_ini = int(self.ini.split("-")[0])
            self._mes_fin = int(self.fin.split("-")[0])
            self._dia_ini = int(self.ini.split("-")[1])
            self._dia_fin = int(self.fin.split("-")[1])
        elif (ini and not fin) or (fin and not ini):
            raise ValueError("si se especifica una fecha de inicio "
                             "debe especificarse la fecha de fin, y viceversa")
        else:
            self._mes_ini = None
            self._mes_fin = None
            self._dia_ini = None
            self._dia_fin = None

    @property
    def factor_anio(self):
        rel_mi = 12 - self.mes_ini
        rel_mf = 12 - self.mes_fin
        if rel_mi < rel_mf:
            return 1
        else:
            return 0

    def dif_anios(self, fecha, anio, raiseE=True):
        """ Metodo para calcular la diferencia de 'anios' o mas bien
        numero de temporadas, desde la fecha dada, hasta la season que
        tiene como año el de la fecha final.

        :param fecha: fecha de la cual se quiere saber la diferencia, tiene
            que incluir el año. Ej: "1999-01-05"
        :type fecha: str
        :param anio: año del final de la season
        :type anio: int
        """
        try:
            s = fecha.split("-")
        except:
            fecha = fecha.format("yyyy-MM-dd").getInfo()
            s = fecha.split("-")

        a = int(s[0])  # a es el año de la fecha dada
        desc = "{}-{}".format(s[1], s[2])
        m, d = Temporada.check_valid_date(desc)

        if self.factor_anio == 0:
            return abs(anio-a)
        else:
            dentro = Temporada.check_between(desc, self.ini, self.fin, raiseE=False)
            if not dentro:
                if raiseE:
                    raise ValueError("La fecha {} no esta dentro de la season".format(fecha))
                else:
                    return abs(anio-a)
            else:
                if m > self.mes_ini:
                    return abs(anio - (a+1))
                elif m == self.mes_ini and d >= self.dia_ini:
                    return abs(anio - (a+1))
                else:
                    return abs(anio - a)

    def dif_anios_ee(self, fechaEE, anio):
        a = fechaEE.get("year")
        m = fechaEE.get("month")
        d = fechaEE.get("day")
        anio = ee.Number(anio)
        # factor = ee.Number(self.factor_anio)
        mes_ini = ee.Number(self.mes_ini)
        dia_ini = ee.Number(self.dia_ini)

        cond = m.gt(mes_ini).Or(m.eq(mes_ini).And(d.gte(dia_ini)))

        diff = ee.Algorithms.If(cond, anio.subtract(a).add(1), anio.subtract(a))

        return ee.Number(diff).abs()


    def add_anio(self, anio):
        """ Crea el inicio y fin de la season con el año dado

        :param anio: año de la season
        :return: inicio y fin de la season
        :rtype: tuple
        """
        a = int(anio)
        ini = str(a-self.factor_anio)+"-"+self.ini
        fin = str(a)+"-"+self.fin
        # print "add_anio", ini, fin
        return ini, fin

    # INICIO
    @property
    def ini(self):
        return self._ini

    @ini.setter
    def ini(self, value):
        if value is not None:
            m, d = Temporada.check_valid_date(value)
            self._ini = value
            self._ini_mes = m
            self._ini_dia = d
        else:
            self._ini = None
            self._ini_mes = None
            self._ini_dia = None

    # FIN
    @property
    def fin(self):
        return self._fin

    @fin.setter
    def fin(self, value):
        if value is not None:
            m, d = Temporada.check_valid_date(value)
            self._fin = value
            self._fin_mes = m
            self._fin_dia = d
        else:
            self._fin = None
            self._fin_mes = None
            self._fin_dia = None

    # DOY
    @property
    def doy(self):
        # Temporada.check_between(self.doy, self.ini, self.fin)
        return self._doy

    @doy.setter
    def doy(self, value):
        if value is None:
            self._doy = None
        else:
            m, d = Temporada.check_valid_date(value)
            Temporada.check_between(value, self.ini, self.fin)
            self._doy = value
            self._doy_mes = m
            self._doy_dia = d

    @property
    def doy_dia(self):
        return self._doy_dia

    @property
    def doy_mes(self):
        return self._doy_mes

    @doy_dia.setter
    def doy_dia(self, dia):
        newdoy = "{}-{}".format(self._doy_mes, dia)
        Temporada.check_valid_date(newdoy)
        Temporada.check_between(newdoy, self.ini, self.fin)
        self._doy = newdoy
        self._doy_dia = dia

    @doy_mes.setter
    def doy_mes(self, mes):
        newdoy = "{}-{}".format(mes, self._doy_dia)
        Temporada.check_between(newdoy, self.ini, self.fin)
        self._doy = newdoy
        self._doy_mes = mes

    @property
    def mes_ini(self):
        return self._mes_ini

    @mes_ini.setter
    def mes_ini(self, mes):
        newini = "{}-{}".format(mes, self.dia_ini)
        # Temporada.check_dif_date(newini, self.fin)
        self._mes_ini = mes
        self.ini = newini

    @property
    def mes_fin(self):
        return self._mes_fin

    @mes_fin.setter
    def mes_fin(self, mes):
        newfin = "{}-{}".format(mes, self.dia_fin)
        # Temporada.check_dif_date(self.ini, newfin)
        self._mes_fin = mes
        self.fin = newfin

    @property
    def dia_ini(self):
        return self._dia_ini

    @dia_ini.setter
    def dia_ini(self, dia):
        newini = "{}-{}".format(self.mes_ini, dia)
        # Temporada.check_dif_date(newini, self.fin)
        self._dia_ini = dia
        self.ini = newini

    @property
    def dia_fin(self):
        return self._dia_fin

    @dia_fin.setter
    def dia_fin(self, dia):
        newfin = "{}-{}".format(self.mes_fin, dia)
        # Temporada.check_dif_date(self.ini, newfin)
        self._dia_fin = dia
        self.fin = newfin

    @classmethod
    def Crecimiento_patagonia(cls):
        return cls(ini="11-15", fin="03-15", doy="01-15")


class PrioridadTemporada(object):
    """ Determina las prioridades de los satelites segun la season dada
    El año de inicio es el dado, y el año final es el siguiente

    :param breaks: años donde hay un cambio en la lista de satelites
    :param periodos: lista de lista de periodos
    :param satlist: lista de satlites segun cada periodo
    :param relacion: diccionario de relacion
    """
    breaks = [1972, 1974, 1976, 1978, 1982, 1983, 1994, 1999, 2012, 2013, date.today().year+1]
    periodos = [range(b, breaks[i+1]) for i, b in enumerate(breaks) if i < len(breaks)-1]

    satlist = [[ID1],
               [ID2, ID1],
               [ID3, ID2, ID1],
               [ID3, ID2],
               [ID4TOA, ID3, ID2],
               [ID5LED, ID5SR, ID4TOA],
               [ID5LED, ID5SR],
               [ID7LED, ID7SR, ID5LED, ID5SR],
               [ID8SR, ID8TOA, ID7LED, ID7SR, ID5LED, ID5SR],
               [ID8SR, ID8TOA, ID7LED, ID7SR]]

    relacion = dict([(p, sat) for per, sat in zip(periodos, satlist) for p in per])

    relacionEE = ee.Dictionary(relacion)

if __name__ == "__main__":
    # print ee.List(PrioridadTemporada.relacionEE.get(ee.String(2014))).getInfo()

    t = Temporada.Crecimiento_patagonia()
    f = ee.Date("2013-03-12")

    for a in range(2014, 2015):
        d = t.dif_anios_ee(f, a)
        # print d.getInfo()

    print ee.Date("2014-"+t.doy).millis().getInfo()
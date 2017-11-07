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


class Season(object):
    """ PROTOTIPO """
    #
    month_day = {1:31, 2:29, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30,
                 10:31, 11:30, 12:31}

    @staticmethod
    def check_valid_date(date):
        """ Verifica que la fecha tenga el formato correcto

        :param date:
        :return: año, mes, dia
        :rtype: tuple
        """
        if not isinstance(date, str):
            # raise ValueError("La date no es del tipo string")
            return False

        split = date.split("-")
        m = int(split[0])
        d = int(split[1])

        if m < 1 or m > 12:
            raise ValueError(
                "Error en {}: El mes debe ser mayor a 1 y menor a 12".format(date))
            # return False
        maxday = Season.month_day[m]
        if d < 1 or d > maxday:
            raise ValueError(
                "Error en {}: En el mes {} el dia debe ser menor a {}".format(date, m, maxday))
            # return False

        return m , d

    @staticmethod
    def check_between(date, ini, end, raiseE=True):
        """ Verifica que la fecha dada este entre la inicial y la final

        :param date:
        :param ini:
        :param end:
        :param raiseE:
        :return:
        """
        retorno = False
        def rerror():
            if raiseE:
                raise ValueError("La date {} debe estar entre {} y {}".format(date, ini, end))
            else:
                return

        m, d = Season.check_valid_date(date)
        mi, di = Season.check_valid_date(ini)
        mf, df = Season.check_valid_date(end)
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

    def __init__(self, ini=None, end=None, doy=None, **kwargs):
        """ Season de crecimiento

        :param ini: mes y dia de inicio de la season
        :param end: mes y dia de end de la season
        :param doy: mes y dia del dia mas representativo del año
        :param kwargs:
        """

        self.ini = ini
        self.end = end

        self.doy = doy

        if ini is not None and end is not None:
            # Season.check_dif_date(ini, end)
            self._ini_month = int(self.ini.split("-")[0])
            self._end_month = int(self.end.split("-")[0])
            self._ini_day = int(self.ini.split("-")[1])
            self._end_day = int(self.end.split("-")[1])
        elif (ini and not end) or (end and not ini):
            raise ValueError("si se especifica una fecha de inicio "
                             "debe especificarse la fecha de end, y viceversa")
        else:
            self._ini_month = None
            self._end_month = None
            self._ini_day = None
            self._end_day = None

    @property
    def year_factor(self):
        rel_mi = 12 - self.ini_month
        rel_mf = 12 - self.end_month
        if rel_mi < rel_mf:
            return 1
        else:
            return 0

    def year_diff(self, date, year, raiseE=True):
        """ Metodo para calcular la diferencia de 'anios' o mas bien
        numero de temporadas, desde la fecha dada, hasta la season que
        tiene como año el de la fecha final.

        :param date: fecha de la cual se quiere saber la diferencia, tiene
            que incluir el año. Ej: "1999-01-05"
        :type date: str
        :param year: año del final de la season
        :type year: int
        """
        try:
            s = date.split("-")
        except:
            date = date.format("yyyy-MM-dd").getInfo()
            s = date.split("-")

        a = int(s[0])  # a es el año de la date dada
        desc = "{}-{}".format(s[1], s[2])
        m, d = Season.check_valid_date(desc)

        if self.year_factor == 0:
            return abs(year - a)
        else:
            dentro = Season.check_between(desc, self.ini, self.end, raiseE=False)
            if not dentro:
                if raiseE:
                    raise ValueError("La date {} no esta dentro de la season".format(date))
                else:
                    return abs(year - a)
            else:
                if m > self.ini_month:
                    return abs(year - (a + 1))
                elif m == self.ini_month and d >= self.ini_day:
                    return abs(year - (a + 1))
                else:
                    return abs(year - a)

    def year_diff_ee(self, eedate, year):
        a = eedate.get("year")
        m = eedate.get("month")
        d = eedate.get("day")
        year = ee.Number(year)
        # factor = ee.Number(self.year_factor)
        mes_ini = ee.Number(self.ini_month)
        dia_ini = ee.Number(self.ini_day)

        cond = m.gt(mes_ini).Or(m.eq(mes_ini).And(d.gte(dia_ini)))

        diff = ee.Algorithms.If(cond, year.subtract(a).add(1), year.subtract(a))

        return ee.Number(diff).abs()


    def add_year(self, year):
        """ Crea el inicio y end de la season con el año dado

        :param year: año de la season
        :return: inicio y end de la season
        :rtype: tuple
        """
        a = int(year)
        ini = str(a - self.year_factor) + "-" + self.ini
        end = str(a)+"-"+self.end
        # print "add_year", ini, end
        return ini, end

    # INICIO
    @property
    def ini(self):
        return self._ini

    @ini.setter
    def ini(self, value):
        if value is not None:
            m, d = Season.check_valid_date(value)
            self._ini = value
            self._ini_month = m
            self._ini_day = d
        else:
            self._ini = None
            self._ini_month = None
            self._ini_day = None

    # FIN
    @property
    def end(self):
        return self._fin

    @end.setter
    def end(self, value):
        if value is not None:
            m, d = Season.check_valid_date(value)
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
        # Season.check_between(self.doy, self.ini, self.end)
        return self._doy

    @doy.setter
    def doy(self, value):
        if value is None:
            self._doy = None
        else:
            m, d = Season.check_valid_date(value)
            Season.check_between(value, self.ini, self.end)
            self._doy = value
            self._doy_month = m
            self._doy_day = d

    @property
    def doy_day(self):
        return self._doy_day

    @property
    def doy_month(self):
        return self._doy_month

    @doy_day.setter
    def doy_day(self, day):
        newdoy = "{}-{}".format(self._doy_month, day)
        Season.check_valid_date(newdoy)
        Season.check_between(newdoy, self.ini, self.end)
        self._doy = newdoy
        self._doy_day = day

    @doy_month.setter
    def doy_month(self, month):
        newdoy = "{}-{}".format(month, self._doy_day)
        Season.check_between(newdoy, self.ini, self.end)
        self._doy = newdoy
        self._doy_month = month

    @property
    def ini_month(self):
        return self._ini_month

    @ini_month.setter
    def ini_month(self, month):
        newini = "{}-{}".format(month, self.ini_day)
        # Season.check_dif_date(newini, self.end)
        self._ini_month = month
        self.ini = newini

    @property
    def end_month(self):
        return self._end_month

    @end_month.setter
    def end_month(self, month):
        newfin = "{}-{}".format(month, self.end_day)
        # Season.check_dif_date(self.ini, newfin)
        self._end_month = month
        self.end = newfin

    @property
    def ini_day(self):
        return self._ini_day

    @ini_day.setter
    def ini_day(self, day):
        newini = "{}-{}".format(self.ini_month, day)
        # Season.check_dif_date(newini, self.end)
        self._ini_day = day
        self.ini = newini

    @property
    def end_day(self):
        return self._end_day

    @end_day.setter
    def end_day(self, day):
        newfin = "{}-{}".format(self.end_month, day)
        # Season.check_dif_date(self.ini, newfin)
        self._end_day = day
        self.end = newfin

    @classmethod
    def Growing_South(cls):
        """ Growing season for Southern latitudes. Begins on November 15th
        and ends on March 15th """
        return cls(ini="11-15", end="03-15", doy="01-15")

    @classmethod
    def Growing_North(cls):
        """ Growing season for Northern latitudes. Begins on May 15th
        and ends on September 15th """
        return cls(ini="05-15", end="09-15", doy="07-15")


class SeasonPriority(object):
    """ Determina las prioridades de los satelites segun la season dada
    El año de inicio es el dado, y el año final es el siguiente

    :param breaks: años donde hay un cambio en la lista de satelites
    :param periods: lista de lista de periods
    :param satlist: lista de satlites segun cada periodo
    :param relacion: diccionario de relacion
    """
    breaks = [1972, 1974, 1976, 1978, 1982, 1983,
              1994, 1999, 2003, 2012, 2013, date.today().year+1]
    periods = [range(b, breaks[i + 1]) for i, b in enumerate(breaks) if i < len(breaks) - 1]

    satlist = [[ID1],
               [ID2, ID1],
               [ID3, ID2, ID1],
               [ID3, ID2],
               [ID4TOA, ID3, ID2],
               [ID5SR, ID5LED, ID4TOA],
               [ID5SR, ID5LED],
               [ID7SR, ID7LED, ID5SR, ID5LED],
               [ID5SR, ID5LED, ID7SR, ID7LED],
               [ID8SR, ID8TOA, ID7SR, ID7LED, ID5SR, ID5LED],
               [ID8SR, ID8TOA, ID7SR, ID7LED]]

    relation = dict(
        [(p, sat) for per, sat in zip(periods, satlist) for p in per])

    ee_relation = ee.Dictionary(relation)

if __name__ == "__main__":
    # print ee.List(SeasonPriority.ee_relation.get(ee.String(2014))).getInfo()

    t = Season.Growing_South()
    f = ee.Date("2007-03-05")
    year = f.get("year")
    '''
    for a in range(2014, 2015):
        d = t.year_diff_ee(f, a)
        # print d.getInfo()

    print ee.Date("2014-"+t.doy).millis().getInfo()
    '''
    print SeasonPriority.ee_relation.get(year.format()).getInfo()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import satcol
import ee
from datetime import date

col_opt = satcol.Collection._OPTIONS

# IDS
ID1 = col_opt[0]
ID2 = col_opt[1]
ID3 = col_opt[2]
ID4TOA = col_opt[3]
ID4SR = col_opt[4]
ID5TOA = col_opt[5]
ID5SR = col_opt[6]
ID5LED = col_opt[7]
ID7TOA = col_opt[8]
ID7SR = col_opt[9]
ID7LED = col_opt[10]
ID8TOA = col_opt[11]
ID8SR = col_opt[12]
S2 = col_opt[13]


class Season(object):
    """ Growing season

    :param ini: initial month and day of the season
    :param end: final month and day of the season
    :param doy: month and day of the 'day of year'
    """
    month_day = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30,
                 10:31, 11:30, 12:31}

    @staticmethod
    def check_valid_date(date):
        """ Verify if date has right format

        :param date: date to verify
        :type date: str
        :return: month, day
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
                "Error in {}: Month must be greate than 1 and less than 12".format(date))
            # return False
        maxday = Season.month_day[m]
        if d < 1 or d > maxday:
            raise ValueError(
                "Error in {}: In month {} the day must be less than {}".format(date, m, maxday))
            # return False

        return m, d

    @staticmethod
    def check_between(date, ini, end, raiseE=True):
        """ Verify that the given date is between `ini_date` and `end_date`

        :param date:
        :param ini:
        :param end:
        :param raiseE:
        :return:
        """
        retorno = False
        def rerror():
            if raiseE:
                raise ValueError("Date {} must be between {} and {}".format(date, ini, end))
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

    def __init__(self, ini=None, end=None, doy=None):

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
        ''' season is in different years?

        :return: 1 if True, 0 if False
        :rtype: int
        '''
        rel_mi = 12 - self.ini_month
        rel_mf = 12 - self.end_month
        if rel_mi < rel_mf:
            return 1
        else:
            return 0

    def year_diff(self, date, year, raiseE=True):
        """ Compute difference between number of seasons, since the given date,
        until the last season

        :param date: date to which want to know the difference, must include
            the year. Example: '1999-01-05'
        :type date: str
        :param year: final season's year
        :type year: int
        :return: number of seasons
        :rtype: int
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
                    raise ValueError("Date {} is not inside the season".format(date))
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
        ''' Same as `year_diff` but all code is in Earth Engine format

        :param eedate: date to which want to know the difference, must include
            the year. Example: ee.Date('1999-01-05')
        :type eedate: ee.Date
        :param year: final season's year
        :type year: int
        :return: number of seasons
        :rtype: ee.Number
        '''
        # TODO: check if given date is inside the season, now assumes it is
        a = ee.Number(eedate.get("year"))
        m = ee.Number(eedate.get("month"))
        d = ee.Number(eedate.get("day"))
        year = ee.Number(year)
        # factor = ee.Number(self.year_factor)
        mes_ini = ee.Number(self.ini_month)
        dia_ini = ee.Number(self.ini_day)

        # year factor
        rel_mi = ee.Number(12).subtract(mes_ini)
        rel_mf = ee.Number(12).subtract(ee.Number(self.end_month))
        year_factor = ee.Algorithms.If(rel_mi.lt(rel_mf), ee.Number(1), ee.Number(0))
        year_factor = ee.Number(year_factor)

        # cond = m.gt(mes_ini).Or(m.eq(mes_ini).And(d.gte(dia_ini)))

        cond1 = ee.Algorithms.If(m.gt(mes_ini).Or(m.eq(mes_ini).And(d.gte(dia_ini))),
                                 year.subtract(a).add(1).abs(),
                                 year.subtract(a).abs())

        # diff = ee.Algorithms.If(cond, year.subtract(a).add(1), year.subtract(a))
        diff = ee.Algorithms.If(year_factor.eq(0), year.subtract(a).abs(), ee.Number(cond1))

        return ee.Number(diff).abs()


    def add_year(self, year):
        """ Create the beginning and end of a season with the given year

        :param year: season's year
        :type year: int
        :return: season's beginning and end
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
    """ Satellite priorities for seasons. It could NOT be a class, but for
    organization purposes it is. It has only class params. No methods
    and initialization.

    :param breaks: list of years when there is a break
    :param periods: nested list of periods
    :param satlist: nested list of satellites in each period
    :param relation: dict of relations
    :param ee_relation: EE dict of relations
    """
    breaks = [1972, 1974, 1976, 1978, 1982, 1983,
              1994, 1999, 2003, 2012, 2013, date.today().year+1]
    periods = [range(b, breaks[i + 1]) for i, b in enumerate(breaks) if i < len(breaks) - 1]

    satlist = [[ID1],
               [ID2, ID1],
               [ID3, ID2, ID1],
               [ID3, ID2],
               [ID4SR, ID4TOA, ID3, ID2],
               [ID5SR, ID5TOA, ID4SR, ID4TOA],
               [ID5SR, ID5TOA],
               [ID7SR, ID7TOA, ID5SR, ID5TOA],
               [ID5SR, ID5TOA, ID7SR, ID7TOA],
               [ID8SR, ID8TOA, ID7SR, ID7TOA, ID5SR, ID5TOA],
               [ID8SR, ID8TOA, ID7SR, ID7TOA]]

    relation = dict(
        [(p, sat) for per, sat in zip(periods, satlist) for p in per])

    ee_relation = ee.Dictionary(relation)

    relation_colgroup = []
    for year, satlist in relation.iteritems():
        col_satlist = [satcol.Collection.from_id(id) for id in satlist]
        colgroup = satcol.ColGroup(col_satlist)
        relation_colgroup.append((year, colgroup))

    relation_colgroup = dict(relation_colgroup)

if __name__ == "__main__":
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    prior = SeasonPriority.relation
    colgroup = SeasonPriority.relation_colgroup
    # pp.pprint(prior)
    # pp.pprint(colgroup)

    print(colgroup[2010].bandsrel())
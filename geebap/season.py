#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ee

import ee.data
if not ee.data._initialized: ee.Initialize()

import satcol
from datetime import date
from collections import OrderedDict
from geetools import filters

col_opt = satcol.IDS

# IDS
ID1 = col_opt['L1']
ID2 = col_opt['L2']
ID3 = col_opt['L3']
ID4TOA = col_opt['L4TOA']
ID4SR = col_opt['L4USGS']
ID5TOA = col_opt['L5TOA']
ID5SR = col_opt['L5USGS']
ID5LED = col_opt['L5LED']
ID7TOA = col_opt['L7TOA']
ID7SR = col_opt['L7USGS']
ID7LED = col_opt['L7LED']
ID8TOA = col_opt['L8TOA']
ID8SR = col_opt['L8USGS']
S2 = col_opt['S2']


class Season(object):
    """ Growing season

    format for `ini`, `end` and `doy` parameters must be: MM-dd, but `doy` can
    be also `None` or n days since the initial date for the season

    Example: '06-02' will be the 2nd of June

    :param ini: initial month and day of the season
    :type ini: str
    :param end: final month and day of the season
    :type end: str
    :param doy: month and day of the 'day of year' or n days since the initial
        date for the season. If None, it will be computed automatically to be
        the half of the range.
    :type doy: str, int
    """

    @staticmethod
    def rel_month_day(leap=False):
        months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        pairs = zip(months, days)

        month_day = OrderedDict()
        for pair in pairs:
            m = pair[0]
            if leap and m == 2:
                d = 29
            else:
                d = pair[1]

            month_day[m] = d
        return month_day

    @staticmethod
    def check_valid_date(date, leap=False):
        """ Verify if date has right format

        :param date: date to verify
        :type date: str
        :return: month, day
        :rtype: tuple
        """
        if not isinstance(date, str):
            raise ValueError("Dates in Season must be strings with format: "
                             "MM-dd")
            # return False

        split = date.split("-")
        assert len(split) == 2, \
            "Error in Season {}: month and day must be divided by '-' " \
            "and with the following format --> MM-dd".format(date)
        m = int(split[0])
        d = int(split[1])

        if m < 1 or m > 12:
            raise ValueError(
                "Error in Season {}: Month must be greater than 1 and less "
                "than 12".format(date))
        maxday = Season.rel_month_day(leap)[m]
        if d < 1 or d > maxday:
            raise ValueError(
                "Error in Season {}: In month {} the day must be less or "
                "equal than {}".format(date, m, maxday))

        return m, d

    @staticmethod
    def check_between(date, ini, end, raiseE=True, leap=False):
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

        m, d = Season.check_valid_date(date, leap)
        mi, di = Season.check_valid_date(ini, leap)
        mf, df = Season.check_valid_date(end, leap)
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

    @staticmethod
    def day_of_year(date, leap=False):
        ''' Day of the year for the given date '''
        m, d = Season.check_valid_date(date, leap)
        if m == 1:
            return d
        else:
            ini = 31

        for month, days in Season.rel_month_day(leap).iteritems():
            if month == 1: continue

            if month != m:
                ini += days
            else:
                break

        return ini + d

    @staticmethod
    def date_for_day(day, leap=False):
        """ Date corresponding to the given 'day of the year' """
        for m in range(1, 13):
            for d in range(1, 32):
                days = Season.rel_month_day(leap)[m]
                if d > days: continue
                date = '{}-{}'.format(m, d)
                nday = Season.day_of_year(date, leap)
                if day == nday: return date

    def __init__(self, ini, end, doy=None, leap=False):
        self.leap = leap
        self.ini = ini
        self.end = end

        self.doy = doy

    @property
    def year_days(self):
        '''
        :return: number of days in one year
        :rtype: int
        '''
        return 366 if self.leap else 365

    @property
    def year_factor(self):
        ''' season covers different years? Like 11-01 to 02-01?

        :return: 1 if True, 0 if False
        :rtype: int
        '''
        dini = Season.day_of_year(self.ini, self.leap)
        dend = Season.day_of_year(self.end, self.leap)
        if dini >= dend:
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
        m, d = Season.check_valid_date(desc, self.leap)

        if self.year_factor == 0:
            return abs(year - a)
        else:
            dentro = Season.check_between(desc, self.ini, self.end, raiseE=False, leap=self.leap)
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
        """ Create the beginning and end of a season with the given year.
        If param year is a ee.Number, it returns a ee.DateRange

        :param year: season's year
        :type year: int or ee.Number
        :return: season's beginning and end
        :rtype: tuple
        """
        if isinstance(year, int) or isinstance(year, float):
            a = int(year)
            ini = str(a - self.year_factor) + "-" + self.ini
            end = str(a)+"-"+self.end
            # print "add_year", ini, end
            return ini, end
        elif isinstance(year, ee.Number):
            factor = ee.Number(self.year_factor)
            y = year.subtract(factor).format()
            temp_ini = ee.String(self.ini)
            ini = y.cat('-').cat(temp_ini)
            temp_end = ee.String(self.end)
            end = year.format().cat('-').cat(temp_end)
            r = ee.DateRange(ee.Date(ini), ee.Date(end))
            return r

    def year_filter(self, year):
        '''
        :param year: season's year
        :type year: int or ee.Number
        :return: a date filter for the given year
        :rtype: ee.Filter
        '''
        if isinstance(year, int) or isinstance(year, float):
            year = int(year)
            date = self.add_year(year)
            return ee.Filter.date(*date)
        elif isinstance(year, ee.Number):
            daterange = self.add_year(year)
            filter = filters.date_range(daterange)
            return filter

    def filter(self):
        '''
        :return: a filter for the season (as it can be applied througout the
            years, leap years won't be considered
        :rtype: ee.Filter
        '''
        ini = Season.day_of_year(self.ini)
        end = Season.day_of_year(self.end)
        return ee.Filter.dayOfYear(ini, end)

    # INICIO
    @property
    def ini(self):
        return self._ini

    @ini.setter
    def ini(self, value):
        if value is not None:
            m, d = Season.check_valid_date(value, self.leap)
            self._ini = value
        else:
            raise ValueError('initial date is required')

    # FIN
    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        if value is not None:
            m, d = Season.check_valid_date(value, self.leap)
            self._end = value
        else:
            raise ValueError('end date is required')

    @property
    def range_in_days(self):
        rini = Season.day_of_year(self.ini, self.leap)
        rend = Season.day_of_year(self.end, self.leap)
        r = rend-rini+1
        return r if self.year_factor == 0 else self.year_days+r

    # DOY
    @property
    def doy(self):
        return self._doy

    @doy.setter
    def doy(self, value):
        drange = self.range_in_days
        if value is None or (isinstance(value, int) and value > drange):
            doy = drange/2  # doy will be half of range by now

            dini = Season.day_of_year(self.ini, self.leap)
            new_doy = dini+doy if dini+doy <= self.year_days \
                               else dini+doy-self.year_days

            self._doy = Season.date_for_day(new_doy-1, self.leap)
        elif isinstance(value, int):
            dini = Season.day_of_year(self.ini, self.leap)
            ini_plus_doy = dini+value
            # print ini_plus_doy
            new_doy = ini_plus_doy if ini_plus_doy <= self.year_days \
                                   else ini_plus_doy-self.year_days
            print 'newdoy', new_doy
            self._doy = Season.date_for_day(new_doy+1, self.leap)
            print self._doy
        else:
            Season.check_valid_date(value, self.leap)
            self._doy = value

    @property
    def ini_month(self):
        return int(self.ini.split('-')[0])

    @ini_month.setter
    def ini_month(self, month):
        newini = "{}-{}".format(month, self.ini_day)
        Season.check_valid_date(newini, self.leap)
        self.ini = newini

    @property
    def end_month(self):
        return int(self.end.split('-')[0])

    @end_month.setter
    def end_month(self, month):
        newfin = "{}-{}".format(month, self.end_day)
        Season.check_valid_date(newfin, self.leap)
        self.end = newfin

    @property
    def ini_day(self):
        return int(self.ini.split('-')[1])

    @ini_day.setter
    def ini_day(self, day):
        newini = "{}-{}".format(self.ini_month, day)
        Season.check_valid_date(newini, self.leap)
        self.ini = newini

    @property
    def end_day(self):
        return int(self.end.split('-')[1])

    @end_day.setter
    def end_day(self, day):
        newfin = "{}-{}".format(self.end_month, day)
        Season.check_valid_date(newfin, self.leap)
        self.end = newfin

    @property
    def doy_month(self):
        return int(self.doy.split('-')[0])

    @property
    def doy_day(self):
        return int(self.end.split('-')[1])

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
    """ Satellite priorities for seasons.

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

    def __init__(self, year):
        self.year = year

    @property
    def satellites(self):
        '''
        :return: list of satellite's ids
        :rtype: list
        '''
        return self.relation[self.year]

    @property
    def collections(self):
        '''
        :return: list of satcol.Collection
        :rtype: list
        '''
        sat = self.satellites
        return [satcol.Collection.from_id(id) for id in sat]

    @property
    def colgroup(self):
        '''
        :rtype: satcol.ColGroup
        '''
        return satcol.ColGroup(self.collections)

    @property
    def ee_collection(self):
        '''
        :return: merged image collection without filters
        :rtype: ee.ImageCollection
        '''
        collection = ee.ImageCollection(ee.List([]))
        for col in self.collections:
            rename_f = col.rename(True)
            cee = col.colEE.map(rename_f)
            collection = ee.ImageCollection(collection.merge(cee))

        # date = '{year}-01-01, {year}-12-31'.format(year=self.year).split(',')
        return collection

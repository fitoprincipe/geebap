#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ee

import ee.data
if not ee.data._initialized: ee.Initialize()

from collections import OrderedDict
from geetools import filters
from datetime import date

LEAP_YEARS = list(range(1968, date.today().year, 4))


class SeasonDate(object):
    """ A simple class to hold dates as MM-DD """
    def __init__(self, date, leap_year):
        self.date = date
        self.leap_year = leap_year

        # Check if format is valid
        self.check_valid()

    @property
    def month(self):
        return int(self.date.split('-')[0])

    @property
    def day(self):
        return int(self.date.split('-')[1])

    @property
    def day_of_year(self):
        """ Day of the year """
        month = self.month
        day = self.day

        if month == 1:
            return day
        else:
            ini = 31

        for month, days in rel_month_day(self.leap_year).items():
            if month == 1: continue

            if month != month:
                ini += days
            else:
                break

        return ini + day

    def add_year(self, year):
        """ Add a year to the season date """
        return '{}-'.format(year, self.date)

    def check_valid(self):
        """ Verify if the season date has right format """
        if not isinstance(self.date, str):
            mje = "Dates in Season must be strings with format: MM-dd, found "\
                  "{}"
            raise ValueError(mje.format(self.date))

        split = self.date.split("-")
        assert len(split) == 2, \
            "Error in Season {}: month and day must be divided by '-' " \
            "and with the following format --> MM-dd".format(self.date)
        m = int(split[0])
        d = int(split[1])

        if m < 1 or m > 12:
            raise ValueError(
                "Error in Season {}: Month must be greater than 1 and less "
                "than 12".format(self.date))

        maxday = rel_month_day(self.leap_year)[m]
        if d < 1 or d > maxday:
            raise ValueError(
                "Error in Season {}: In month {} the day must be less or "
                "equal than {}".format(self.date, m, maxday))

        return True


class Season(object):
    """ Growing season

    format for `ini`, `end` and `best_doy` parameters must be: MM-dd, but `best_doy` can
    be also `None` or n days since the initial date for the season

    Example: '06-02' will be the 2nd of June

    :param ini: initial month and day of the season
    :type ini: str
    :param end: final month and day of the season
    :type end: str
    :param best_doy: month and day of the 'day of year' or n days since the initial
        date for the season. If None, it will be computed automatically to be
        the half of the range.
    :type doy: str, int
    """
    def __init__(self, start, end, best_doy=None, leap_year=False):
        self.leap_year = leap_year
        self.start = start
        self.end = end
        self.best_doy = best_doy

    # START
    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        if value is not None:
            if not isinstance(value, SeasonDate):
                value = SeasonDate(value, self.leap_year)
            self._start = value
        else:
            raise ValueError('initial date is required')

    # END
    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        if value is not None:
            if not isinstance(value, SeasonDate):
                value = SeasonDate(value, self.leap_year)
            self._end = value
        else:
            raise ValueError('end date is required')

    @property
    def range_in_days(self):
        start_doy = self.start.day_of_year
        end_doy = self.end.day_of_year
        r = end_doy-start_doy+1
        return r if self.year_factor == 0 else self.year_days+r

    # DOY
    @property
    def best_doy(self):
        return self._best_doy

    @best_doy.setter
    def best_doy(self, value):
        # Get days between start and end of season
        drange = self.range_in_days

        # Check valid date
        if not isinstance(value, SeasonDate):
            value = SeasonDate(value, self.leap_year)

        value_doy = value.day_of_year

        out_of_range1 = isinstance(value_doy, int) and (value_doy > drange)

        if value is None or out_of_range1:
            doy = int(drange/2)  # best_doy will be half of range by now

            dini = self.day_of_year(self.start, self.leap_year)
            new_doy = dini+doy if dini+doy <= self.year_days \
                else dini+doy-self.year_days

            self._best_doy = date_for_day(new_doy - 1, self.leap_year)
        elif isinstance(value, int):
            dini = self.day_of_year(self.start, self.leap_year)
            ini_plus_doy = dini+value
            new_doy = ini_plus_doy if ini_plus_doy <= self.year_days \
                else ini_plus_doy-self.year_days
            self._best_doy = date_for_day(new_doy + 1, self.leap_year)
        else:
            self.check_valid_date(value, self.leap_year)
            self._best_doy = value

    @property
    def year_days(self):
        '''
        :return: number of days in one year
        :rtype: int
        '''
        return 366 if self.leap_year else 365

    @property
    def year_factor(self):
        ''' season covers different years? Like 11-01 to 02-01?

        :return: 1 if True, 0 if False
        :rtype: int
        '''
        dini = Season.day_of_year(self.start, self.leap_year)
        dend = Season.day_of_year(self.end, self.leap_year)
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
        s = date.split("-")
        year = int(s[0])
        desc = "{}-{}".format(s[1], s[2])
        month, day = Season.check_valid_date(desc, self.leap_year)

        if self.year_factor == 0:
            return abs(year - year)
        else:
            dentro = Season.check_between(desc, self.start, self.end,
                                          raiseE=False, leap=self.leap_year)
            if not dentro:
                if raiseE:
                    msg = "Date {} is not inside the season"
                    raise ValueError(msg.format(date))
                else:
                    return abs(year - year)
            else:
                if month > self.ini_month:
                    return abs(year - (year + 1))
                elif month == self.ini_month and day >= self.ini_day:
                    return abs(year - (year + 1))
                else:
                    return abs(year - year)

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
            ini = str(a - self.year_factor) + "-" + self.start
            end = str(a)+"-"+self.end
            # print "add_year", ini, end
            return ini, end
        elif isinstance(year, ee.Number):
            factor = ee.Number(self.year_factor)
            y = year.subtract(factor).format()
            temp_ini = ee.String(self.start)
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
            years, leap_year years won't be considered
        :rtype: ee.Filter
        '''
        ini = Season.day_of_year(self.start)
        end = Season.day_of_year(self.end)
        return ee.Filter.dayOfYear(ini, end)



    @property
    def ini_month(self):
        return int(self.start.split('-')[0])

    @ini_month.setter
    def ini_month(self, month):
        newini = "{}-{}".format(month, self.ini_day)
        Season.check_valid_date(newini, self.leap_year)
        self.start = newini

    @property
    def end_month(self):
        return int(self.end.split('-')[0])

    @end_month.setter
    def end_month(self, month):
        newfin = "{}-{}".format(month, self.end_day)
        Season.check_valid_date(newfin, self.leap_year)
        self.end = newfin

    @property
    def ini_day(self):
        return int(self.start.split('-')[1])

    @ini_day.setter
    def ini_day(self, day):
        newini = "{}-{}".format(self.ini_month, day)
        Season.check_valid_date(newini, self.leap_year)
        self.start = newini

    @property
    def end_day(self):
        return int(self.end.split('-')[1])

    @end_day.setter
    def end_day(self, day):
        newfin = "{}-{}".format(self.end_month, day)
        Season.check_valid_date(newfin, self.leap_year)
        self.end = newfin

    @property
    def doy_month(self):
        return int(self.best_doy.split('-')[0])

    @property
    def doy_day(self):
        return int(self.end.split('-')[1])

    def doy_date(self, year):
        """ Add a year to DOY """
        if self.year_factor == 1 and self.doy_month > self.ini_month:
            year = year-1

        return '{}-{}-{}'.format(year, self.doy_month, self.doy_day)

    def contains(self, date):
        """ Check if a SeasonDate is contained in the Season """
        if not isinstance(date, SeasonDate):
            raise ValueError('date must be a SeasonDate')






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


def check_between(date, start, end, raiseE=True, leap=False):
    """ Verify that the given date is between `start` and `end` dates

    :param date: the date to verify
    :type date: SeasonDate or str
    :param start:
    :param end:
    :param raiseE:
    :return:
    """
    is_between = False
    def rerror():
        if raiseE:
            msg = "Date {} must be between {} and {}"
            raise ValueError(msg.format(date, start, end))
        else:
            return

    m, d = check_valid_season(date, leap)
    mi, di = check_valid_season(start, leap)
    mf, df = check_valid_season(end, leap)
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
            is_between = True
        elif mf == m and df >= d:
            is_between = True
        elif mi == m and di <= d:
            is_between = True
        else:
            rerror()
    else:
        if m < mf:
            is_between = True
        elif m == mf and d <= df:
            is_between = True
        elif m > mi:
            is_between = True
        elif m == mi and d >= di:
            is_between = True
        else:
            rerror()

    return is_between


def day_of_year(season, leap=False):
    ''' Day of the year for the given season '''
    m, d = check_valid_season(season, leap)
    if m == 1:
        return d
    else:
        ini = 31

    for month, days in rel_month_day(leap).items():
        if month == 1: continue

        if month != m:
            ini += days
        else:
            break

    return ini + d


def date_for_day(day, leap=False):
    """ Date corresponding to the given 'day of the year' """
    for m in range(1, 13):
        for d in range(1, 32):
            days = rel_month_day(leap)[m]
            if d > days: continue
            date = '{}-{}'.format(m, d)
            nday = day_of_year(date, leap)
            if day == nday: return date
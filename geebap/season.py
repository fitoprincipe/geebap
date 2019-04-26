# -*- coding: utf-8 -*-
import ee
from collections import OrderedDict


def is_leap(year):
    if isinstance(year, (int, float)):
        mod = year%4
        return True if mod == 0 else False
    elif isinstance(year, (ee.Number,)):
        mod = year.mod(4)
        return mod.Not()


def _rel_month_day(leap_year):
    months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    pairs = zip(months, days)

    month_day = OrderedDict()
    for m, d in pairs:
        if leap_year and m == 2:
            d = 29
        month_day[m] = d
    return month_day


class SeasonDate(object):
    """ A simple class to hold dates as MM-DD """
    def __init__(self, date):
        self.date = date

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

        for rel_month, days in _rel_month_day(True).items():
            if rel_month == 1: continue

            if rel_month != month:
                ini += days
            else:
                break

        return ini + day

    def add_year(self, year):
        """ Just add the year """
        if not is_leap(year) and self.date == '02-29':
            msg = "Year {} is leap, hence it does't contain day 29 in february"
            raise ValueError(msg.format(year))
        return '{}-{}'.format(year, self.date)

    def check_valid(self):
        """ Verify if the season date has right format """
        if not isinstance(self.date, str):
            mje = "Dates in Season must be strings with format: MM-dd, found " \
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

        maxday = _rel_month_day(True)[m]
        if d < 1 or d > maxday:
            raise ValueError(
                "Error in Season {}: In month {} the day must be less or "
                "equal than {}".format(self.date, m, maxday))

        return True


class Season(object):
    """ Growing season """
    def __init__(self, start, end):
        self.start = start
        self.end = end

    # START
    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        if value is not None:
            if not isinstance(value, SeasonDate):
                try:
                    value = SeasonDate(value)
                except:
                    raise ValueError('start date must be an instance of SeasonDate')
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
                try:
                    value = SeasonDate(value)
                except:
                    raise ValueError('end date must be an instance of SeasonDate')

            self._end = value
        else:
            raise ValueError('end date is required')

    @property
    def over_end(self):
        """ True if the season goes over the end of the year """
        if self.start.day_of_year >= self.end.day_of_year:
            return True
        else:
            return False

    @property
    def range_in_days(self):
        return abs(self.start.difference(self.end, self.over_end))

    def add_year(self, year):
        year = ee.Number(year)
        if self.over_end:
            start_year = year.subtract(1)
        else:
            start_year = ee.Number(year)
        end_year = ee.Number(year)

        sday = self.start.day
        eday = self.end.day

        # look for feb 29h in non leap
        if not is_leap(year):
            if self.start.month == 2 and sday == 29:
                sday = 28
            if self.end.month == 2 and eday == 29:
                eday = 28

        start = ee.Date.fromYMD(start_year, self.start.month, sday)
        end = ee.Date.fromYMD(end_year, self.end.month, eday)
        daterange = ee.DateRange(ee.Date(start), ee.Date(end))
        return daterange
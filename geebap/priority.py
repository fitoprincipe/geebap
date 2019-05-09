# -*- coding: utf-8 -*-
import ee
from datetime import date
from geetools import collection
from geetools.collection.group import CollectionGroup

# IDS
ID1 = 'LANDSAT/LM01/C01/T1'
ID2 = 'LANDSAT/LM02/C01/T1'
ID3 = 'LANDSAT/LM03/C01/T1'
ID4TOA = 'LANDSAT/LT04/C01/T1_TOA'
ID4SR = 'LANDSAT/LT04/C01/T1_SR'
ID5TOA = 'LANDSAT/LT05/C01/T1_TOA'
ID5SR = 'LANDSAT/LT05/C01/T1_SR'
ID7TOA = 'LANDSAT/LE07/C01/T1_TOA'
ID7SR = 'LANDSAT/LE07/C01/T1_SR'
ID8TOA = 'LANDSAT/LC08/C01/T1_TOA'
ID8SR = 'LANDSAT/LC08/C01/T1_SR'
S2 = 'COPERNICUS/S2'
S2SR = 'COPERNICUS/S2_SR'


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

    periods = []
    for i, b in enumerate(breaks):
        if i < len(breaks) - 1:
            periods.append(range(b, breaks[i + 1]))

    satlist = [[ID1], # 72 74
               [ID2, ID1], # 74 76
               [ID3, ID2, ID1], # 76 78
               [ID3, ID2], # 78 82
               [ID4SR, ID4TOA, ID3, ID2], # 82 83
               [ID5SR, ID5TOA, ID4SR, ID4TOA], # 83 94
               [ID5SR, ID5TOA], # 94 99
               [ID7SR, ID7TOA, ID5SR, ID5TOA], # 99 03
               [ID5SR, ID5TOA, ID7SR, ID7TOA], # 03 12
               [ID8SR, ID8TOA, ID7SR, ID7TOA, ID5SR, ID5TOA], # 12 13
               [ID8SR, ID8TOA, ID7SR, ID7TOA]] # 13 -

    relation = dict(
        [(p, sat) for per, sat in zip(periods, satlist) for p in per])

    ee_relation = ee.Dictionary(relation)

    l7_slc_off = range(2003, date.today().year+1)

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
        return [collection.fromId(id) for id in sat]

    @property
    def colgroup(self):
        '''
        :rtype: CollectionGroup
        '''
        return CollectionGroup(*self.collections)

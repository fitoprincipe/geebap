#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import ee
ee.Initialize()

from .. import season
import json
import math
from geetools import tools

class TestSeason(unittest.TestCase):

    def test_month(self):
        ini = '01-01'
        end = '01-30'

        seas = season.Season(ini, end)

        factor = 0
        factor_compute = seas.year_factor
        self.assertEqual(factor_compute, factor)

        year_diff = 2
        year_diff_compute = seas.year_diff('1999-01-15', 2001)
        # season: 2001-01-01 to 2001-01-30
        self.assertEqual(year_diff, year_diff_compute)

        year_diff_ee = 2
        year_diff_ee_compute = seas.year_diff_ee(ee.Date('1999-01-15'), 2001)
        self.assertEqual(year_diff_ee, year_diff_ee_compute.getInfo())

        add_year = ('1999-01-01', '1999-01-30')
        add_year_compute = seas.add_year(1999)
        self.assertEqual(add_year, add_year_compute)

    def test_diff_year(self):
        ini = '12-01'
        end = '01-30'

        seas = season.Season(ini, end)

        factor = 1
        factor_compute = seas.year_factor
        self.assertEqual(factor_compute, factor)

        year_diff = 3
        year_diff_compute = seas.year_diff('1999-01-15', 2002)
        # season: 2001-12-01 to 2002-01-30
        # -> 1999 to 2000, 2000 to 2001, 2001 to 2002 -> 3 sesons
        self.assertEqual(year_diff, year_diff_compute)

        year_diff_ee = 3
        year_diff_ee_compute = seas.year_diff_ee(ee.Date('1999-01-15'), 2002)
        self.assertEqual(year_diff_ee, year_diff_ee_compute.getInfo())

        add_year = ('1999-12-01', '2000-01-30')
        add_year_compute = seas.add_year(2000)
        self.assertEqual(add_year, add_year_compute)

    def test_same_year(self):
        ini = '10-01'
        end = '12-30'

        seas = season.Season(ini, end)

        factor = 0
        factor_compute = seas.year_factor
        self.assertEqual(factor_compute, factor)

        year_diff = 2
        year_diff_compute = seas.year_diff('1999-11-15', 2001)
        # season: 2001-10-01 to 2001-12-30
        self.assertEqual(year_diff, year_diff_compute)

        year_diff_ee = 2
        year_diff_ee_compute = seas.year_diff_ee(ee.Date('1999-11-15'), 2001)
        self.assertEqual(year_diff_ee, year_diff_ee_compute.getInfo())

        add_year = ('1999-10-01', '1999-12-30')
        add_year_compute = seas.add_year(1999)
        self.assertEqual(add_year, add_year_compute)

    def test_add_year_ee(self):
        year = 2000
        seas = season.Season.Growing_South()
        ini, end = seas.add_year(year)

        year = ee.Number(year)
        daterange = seas.add_year(year)

        newini = ee.Date(daterange.start()).format('yyyy-MM-dd').getInfo()
        newend = ee.Date(daterange.end()).format('yyyy-MM-dd').getInfo()

        self.assertEqual(ini, '1999-11-15')
        self.assertEqual(end, '2000-03-15')
        self.assertEqual(newini, '1999-11-15')
        self.assertEqual(newend, '2000-03-15')





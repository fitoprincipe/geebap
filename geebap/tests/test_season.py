#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import ee
from .. import season
from geetools import tools
import json
import math

ee.Initialize()

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

    def test_season_priority(self):
        relations = season.SeasonPriority.relation

        expected = {1972: ['LANDSAT/LM1_L1T'],
                    1973: ['LANDSAT/LM1_L1T'],
                    1974: ['LANDSAT/LM2_L1T', 'LANDSAT/LM1_L1T'],
                    1975: ['LANDSAT/LM2_L1T', 'LANDSAT/LM1_L1T'],
                    1976: ['LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T', 'LANDSAT/LM1_L1T'],
                    1977: ['LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T', 'LANDSAT/LM1_L1T'],
                    1978: ['LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T'],
                    1979: ['LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T'],
                    1980: ['LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T'],
                    1981: ['LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T'],
                    1982: ['LANDSAT/LT04/C01/T1_SR','LANDSAT/LT4_L1T_TOA_FMASK', 'LANDSAT/LM3_L1T', 'LANDSAT/LM2_L1T'],
                    1983: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1984: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1985: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1986: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1987: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1988: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1989: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1990: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1991: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1992: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1993: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LT04/C01/T1_SR', 'LANDSAT/LT4_L1T_TOA_FMASK'],
                    1994: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    1995: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    1996: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    1997: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    1998: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    1999: ['LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR', 'LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    2000: ['LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR', 'LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    2001: ['LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR', 'LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    2002: ['LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR', 'LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    2003: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2004: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2005: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2006: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2007: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2008: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2009: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2010: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2011: ['LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2012: ['LANDSAT/LC08/C01/T1_SR', 'LANDSAT/LC8_L1T_TOA_FMASK', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR', 'LANDSAT/LT05/C01/T1_SR', 'LEDAPS/LT5_L1T_SR'],
                    2013: ['LANDSAT/LC08/C01/T1_SR', 'LANDSAT/LC8_L1T_TOA_FMASK', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2014: ['LANDSAT/LC08/C01/T1_SR', 'LANDSAT/LC8_L1T_TOA_FMASK', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2015: ['LANDSAT/LC08/C01/T1_SR', 'LANDSAT/LC8_L1T_TOA_FMASK', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2016: ['LANDSAT/LC08/C01/T1_SR', 'LANDSAT/LC8_L1T_TOA_FMASK', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR'],
                    2017: ['LANDSAT/LC08/C01/T1_SR', 'LANDSAT/LC8_L1T_TOA_FMASK', 'LANDSAT/LE07/C01/T1_SR', 'LEDAPS/LE7_L1T_SR']}

        self.assertDictEqual(relations, expected)



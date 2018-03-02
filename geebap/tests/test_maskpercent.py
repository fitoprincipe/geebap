#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import ee
from .. import satcol, scores
from geetools import tools

ee.Initialize()

class TestMaskPercent(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.band = "B1"

        self.pol = ee.Geometry.Polygon(
            [[[-71.56928658485413, -43.356795174869426],
              [-71.56932950019836, -43.357879484308015],
              [-71.56781673431396, -43.35791848788363],
              [-71.56779527664185, -43.35682637828949]]])

        self.p = ee.Geometry.Point([-71.56871795654297,
                                    -43.35720861888331])

        self.col = satcol.Collection.Landsat8TOA()
        self.colEE = self.col.colEE
        self.colEE = self.colEE.filterBounds(self.p)

        self.image = ee.Image(self.colEE.first()).clip(self.pol).select([self.band])

        # MASK OUT SOME PIXELS
        condition = self.image.gte(0.13)
        self.image = self.image.updateMask(condition)

    def test_default(self):
        # SCORE
        score = scores.MaskPercent(self.band)
        newimg = score.map(self.col, self.pol)(self.image)

        maskpercent_prop = newimg.get(score.name).getInfo()
        maskpercent_pix = tools.get_value(newimg, self.p, side='client')[score.name]

        self.assertEqual(maskpercent_prop, 0,5625)
        self.assertEqual(maskpercent_pix, 0,5625)





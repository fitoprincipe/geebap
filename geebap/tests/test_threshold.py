#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import ee
from .. import scores
from geetools import tools

ee.Initialize()

class TestThreshold(unittest.TestCase):
    def setUp(self):
        self.img = ee.Image('LANDSAT/LC08/C01/T1_SR/LC08_231090_20130414')
        self.band = "B4"
        self.p1 = ee.Geometry.Point([-71.51, -43.27])
        self.p2 = ee.Geometry.Point([-71.53, -43.271])
        self.p3 = ee.Geometry.Point([-71.547, -43.274])

        self.region = ee.Geometry.Polygon(
            [[[-71.57, -43.25],
              [-71.57, -43.29],
              [-71.49, -43.29],
              [-71.49, -43.25]]])

        self.original_value1 = 308
        self.original_value2 = 101
        self.original_value3 = 5701

    def test_minmax(self):
        min = 150
        max = 2000

        thres = scores.Threshold(self.band, (min, max))
        newimg = thres.map()(self.img)

        val1 = tools.get_value(img=newimg, point=self.p1, scale=30, side='client')['score-thres']
        val2 = tools.get_value(img=newimg, point=self.p2, scale=30, side='client')['score-thres']
        val3 = tools.get_value(img=newimg, point=self.p3, scale=30, side='client')['score-thres']

        self.assertEqual(val1, 1)
        self.assertEqual(val2, 0)
        self.assertEqual(val3, 0)

        masked = newimg.select(['B5', 'B7', 'B4']).updateMask(newimg.select('score-thres'))
        thumb = masked.getThumbUrl({'min':0, 'max':5000, 'region':self.region.getInfo()['coordinates']})
        original = newimg.select(['B5', 'B7', 'B4']).getThumbUrl({'min':0, 'max':5000, 'region':self.region.getInfo()['coordinates']})
        print('Original: {}'.format(original))
        print('See image at: {}'.format(thumb))
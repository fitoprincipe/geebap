#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import ee
ee.Initialize()

from ..scores import CloudDist, MaskPercent
from geetools import tests, tools, cloud_mask

cloud_S2 = ee.Image(tests.TEST_CLOUD_IMAGES['S2'])

class TestCloudDist(unittest.TestCase):
    def setUp(self):
        self.score = CloudDist()

    def test_generate_mask(self):
        band = 'B1'
        mask = cloud_mask.sentinel2(cloud_S2)
        cld_score = self.score.generate_score(mask, band)
        vis = cld_score.visualize(min=0, max=1, palette=['b9936c', 'dac292',
                                                         'e6e2d3', 'c4b7a6'])

        region = cloud_S2.geometry().centroid().buffer(5000)
        url = vis.getThumbUrl({'region':tools.getRegion(region)})

        print('\nCloud Distance Score: {}\n'.format(url))
        self.assertEqual(cld_score.getInfo()['type'], 'Image')


class TestMaskPercent(unittest.TestCase):
    def setUp(self):
        pass
    def test_with_zeros(self):
        score = MaskPercent()

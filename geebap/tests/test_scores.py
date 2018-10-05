#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import ee
ee.Initialize()

from ..satcol import Collection
from ..scores import CloudDist, MaskPercent, Threshold
from geetools import tests, tools, cloud_mask

cloud_S2 = ee.Image(tests.TEST_CLOUD_IMAGES['S2'])

def output(image, name, vis_params):

    visimage = image.visualize(**vis_params)
    url = visimage.getThumbUrl({'region':tools.geometry.getRegion(cloud_S2)})

    print(name, url)

def export(image, folder, score, scale=30):
    user = ee.data.getAssetRoots()[0]['id']
    task = ee.batch.Export.image.toAsset(image,
           assetId='{}/{}/{}'.format(user, folder, score),
           scale=30,
           region=tools.geometry.getRegion(image))
    task.start()

class TestCloudDist(unittest.TestCase):
    def setUp(self):
        self.score = CloudDist()

    def test_generate_mask(self):
        band = 'B1'
        mask = cloud_mask.sentinel2()(cloud_S2)
        cld_score = self.score.generate_score(mask, band)
        vis = cld_score.visualize(min=0, max=1, palette=['b9936c', 'dac292',
                                                         'e6e2d3', 'c4b7a6'])

        region = cloud_S2.geometry().centroid().buffer(5000)
        url = vis.getThumbUrl({'region':tools.geometry.getRegion(region)})

        print('\nCloud Distance Score: {}\n'.format(url))
        self.assertEqual(cld_score.getInfo()['type'], 'Image')


class TestMaskPercent(unittest.TestCase):
    def test_with_zeros(self):

        col = Collection.Sentinel2()
        score = MaskPercent()
        image = cloud_mask.sentinel2()(cloud_S2)
        bounds = image.geometry().buffer(-50000)
        computed = score.map(col, bounds)(image)

        maskprop = computed.get(score.name).getInfo()
        maskband = tools.image.get_value(
            computed, image.geometry().centroid(), 10, 'client')[score.name]

        self.assertEqual(maskband, maskprop)


class TestThreshold(unittest.TestCase):
    def test_threshold(self):
        # test_image = ee.Image(LANDSAT/LC08/C01/T1_SR/LC08_231090_20170103)
        score = Threshold({'B8':{'min': 100,'max':2000},
                           'B11':{'min':100, 'max':2000}})
        col = Collection.Sentinel2()
        result = score.map(col)(cloud_S2)
        self.assertEqual(result.getInfo()['type'], 'Image')
        output(result, 'test threshold', {'bands':['score-thres'],
                                          'min':0, 'max':1})
        output(cloud_S2, 'original', {'bands':['B8','B11','B4'],
                                      'min':0, 'max':5000})

        export(result.select([score.name]), 'test_scores', 'threshold', 10)

    def test_threshold_satcol(self):
        col = Collection.Landsat8USGS()
        p = ee.Geometry.Point([-70.16521453857422,-43.02372558882024])
        colEE = col.colEE.filterBounds(p).map(col.rename())
        score = Threshold()
        colEE_score = colEE.map(score.map(col))

        p1 = ee.Geometry.Point([-69.38690186070744,-43.06088427532436])
        p0 = ee.Geometry.Point([-69.21112061070744, -43.41704165930161])

        image = ee.Image(colEE_score.first())

        p1_val = tools.image.get_value(image, p1, 30,'client')['score-thres']
        p0_val = tools.image.get_value(image, p0, 30,'client')['score-thres']

        self.assertEqual(float(p1_val), 1)
        self.assertEqual(float(p0_val), 0)

        # output(image, 'from_satcol', {'bands':['score-thres'], 'min':0, 'max':1})
        export(image.select([score.name]), 'test_scores', 'threshold_satcol', 30)
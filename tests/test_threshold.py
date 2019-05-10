# -*- coding: utf-8 -*-

import ee
ee.Initialize()
from geebap import scores
from geetools import tools

img = ee.Image('LANDSAT/LC08/C01/T1_SR/LC08_231090_20130414')

p1 = ee.Geometry.Point([-71.51, -43.27])
p2 = ee.Geometry.Point([-71.53, -43.271])
p3 = ee.Geometry.Point([-71.547, -43.274])

region = ee.Geometry.Polygon(
    [[[-71.57, -43.25],
      [-71.57, -43.29],
      [-71.49, -43.29],
      [-71.49, -43.25]]])

original_value1 = 308
original_value2 = 101
original_value3 = 5701


def test_minmax():

    thres = scores.Threshold()
    newimg = thres.compute(img, thresholds={
        'B4': {'min':150, 'max':2000}
    }, name=thres.name)

    val1 = tools.image.getValue(newimg, point=p1, scale=30, side='client')[thres.name]
    val2 = tools.image.getValue(newimg, point=p2, scale=30, side='client')[thres.name]
    val3 = tools.image.getValue(newimg, point=p3, scale=30, side='client')[thres.name]

    assert val1 == 1
    assert val2 == 0
    assert val3 == 0

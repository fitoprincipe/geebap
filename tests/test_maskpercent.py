# -*- coding: utf-8 -*-

import ee
ee.Initialize()

from geebap import scores
from geetools import tools, collection

maxDiff = None
band = "B1"

pol = ee.Geometry.Polygon(
    [[[-71.56928658485413, -43.356795174869426],
      [-71.56932950019836, -43.357879484308015],
      [-71.56781673431396, -43.35791848788363],
      [-71.56779527664185, -43.35682637828949]]])

p = ee.Geometry.Point([-71.56871795654297,
                       -43.35720861888331])

col = collection.Landsat8TOA()
colEE = col.collection
colEE = colEE.filterBounds(p)

image = ee.Image(colEE.first()).clip(pol).select([band])

# MASK OUT SOME PIXELS
condition = image.gte(0.13)
image = image.updateMask(condition)

def test_default():
    # SCORE
    score = scores.MaskPercent(band)
    newimg = score.compute(image, geometry=pol, scale=30)

    maskpercent_prop = newimg.get(score.name).getInfo()
    maskpercent_pix = tools.image.getValue(newimg, p, side='client')[score.name]

    assert maskpercent_prop == 0,5625
    assert maskpercent_pix == 0,5625





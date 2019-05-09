# -*- coding: utf-8 -*-

import ee
ee.Initialize()
from geebap import scores, bap, season, masks, filters


# FILTERS
filter = filters.CloudCover()

# MASKS
clouds = masks.Mask()

# SEASON
seas = season.Season('11-15', '02-15')

# SCORES
psat = scores.Satellite()
pop = scores.AtmosOpacity()
pmascpor = scores.MaskPercent()
pindice = scores.Index()
pout = scores.Outliers(("ndvi",))
pdoy = scores.Doy('01-15', seas)
thres = scores.Threshold()

# SITES
site = ee.Geometry.Polygon(
    [[[-71.78, -42.79],
      [-71.78, -42.89],
      [-71.57, -42.89],
      [-71.57, -42.79]]])
centroid = site.centroid()

def test_bap2016_0():
    pmulti = scores.MultiYear(2016, seas)
    objbap = bap.Bap(season=seas,
                     scores=(pindice, pmascpor, psat,
                             pout, pop, pdoy, thres,
                             pmulti),
                     masks=(clouds,),
                     filters=(filter,),
                     )

    composite = objbap.build_composite_best(2016, site, indices=("ndvi",))

    assert isinstance(composite, ee.Image) == True

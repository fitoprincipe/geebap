Gee Bap
=
Best Available Pixel (Bap) Composite using the Python API of Google Earth Engine (Gee)
-

This code is based on *Pixel-Based Image Compositing for Large-Area Dense Time Series Applications and Science. (White et al., 2014)* 
http://www.tandfonline.com/doi/full/10.1080/07038992.2014.945827

It uses a series of pixel based scores to generate a composite with the *Best Available Pixel*, assuming it is the one that has better score.

Instalation
-

To use this package you must have installed and running Google Earth Engine Python API: https://developers.google.com/earth-engine/python_install

Once you have that, proceed 

> pip install geebap


Available Collections
-

- Serie Landsat
    
    - Landsat 1,2 and 3: Raw collections
    - Landsat 4: TOA collection
    - Landsat 5: TOA, SR (Ledaps and USGS) collections
    - Landsat 7: TOA, SR (Ledaps and USGS) collections
    - Landsat 8: TOA, SR (USGS) collections

- Sentinel 2

- Modis Series (experimental)

    - Modis Aqua
    - Modis Terra

Available Scores
-

- Satellite
- Distance to clouds and shadows masks
- Atmospheric Opacity
- Day of the year (doy)
- Masked pixels percentage
- Outliers
- Absolute value of a vegetation index

Available Indices
-

- NDVI
- EVI
- NBR

Basic Usage
-

.. code:: python

    from geebap import bap, season, filters, masks, \
                       scores, satcol, functions
    
    # COLLECTION
    col_group = satcol.ColGroup.Landsat()
    
    # SEASON
    a_season = season.Season.Growing_North()
    
    # MASKS
    cld_mask = masks.Clouds()
    equiv_mask = masks.Equivalent()
    
    # Combine masks in a tuple
    masks = (cld_mask, equiv_mask)
     
    # FILTERS
    filt_cld = filters.CloudsPercent()
    filt_mask = filters.MaskPercent()
    
    # Combine filters in a tuple
    filters = (filt_cld, filt_mask)
    
    # SCORES
    doy = scores.Pdoy()
    sat = scores.Psat()
    op = scores.Pop()
    out = scores.Poutlier(("ndvi",))
    ind = scores.Pindice("ndvi")
    mascpor = scores.Pmascpor()
    dist = scores.Pdist()
    
    # Combine scores in a tuple    
    scores = (doy, sat, op, out, ind, mascpor, dist)
    
    # BAP OBJECT
    bap = bap.Bap(year=2010, range=(0, 0),
                  season=a_season,
                  colgroup=col_group,
                  masks=masks,
                  scores=scores,
                  filters=filters)
    
    # SITE
    site = ee.Geometry.Polygon([[-71,-42],
                                [-71,-43],
                                [-72,-43],
                                [-72,-42]])
    
    # COMPOSITE
    composite = bap.bestpixel(site=site,
                              indices=("ndvi",))
    
    # The result (composite) is a namedtuple, so
    image = composite.image
    
    # image is a ee.Image object, so you can do anything
    # from here..
    
    one_value = functions.get_value(
                            image,
                            ee.Geometry.Point([-71.9, -38.9]),
                            30)
    
    print(one_value)

*Prints:*

> {u'BLUE': 0.018400000408291817, 
   u'bandID': 10.0, 
   u'date': 14592.0, 
   u'score': 0.4800287335965901, 
   u'psat': 0.8500000238418579, 
   u'poutlier': 1.0, 
   u'pdoy': 0.010760011453995735, 
   u'pop': 0.01338691782766488, 
   u'NIR': 0.365200012922287, 
   u'pindice': 0.934493362903595, 
   u'GREEN': 0.041200000792741776, 
   u'pdist': 5.749522023787777e-19, 
   u'pmascpor': 0.5515608191490173, 
   u'ATM_OP': 93.0, 
   u'ndvi': 0.8689867258071899, 
   u'RED': 0.025599999353289604, 
   u'SWIR': 0.13779999315738678}
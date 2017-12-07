Best Available Pixel (Bap) Composite using the Python API of Google Earth Engine (Gee)
--------------------------------------------------------------------------------------

This code is based on *Pixel-Based Image Compositing for Large-Area Dense Time
Series Applications and Science. (White et al., 2014)*
http://www.tandfonline.com/doi/full/10.1080/07038992.2014.945827

It uses a series of pixel based scores to generate a composite with the
*Best Available Pixel*, assuming it is the one that has better score.

License and Copyright
---------------------

2017 Rodrigo E. Principe - geebap - https://github.com/fitoprincipe/geebap

This work was financed by 'Ministerio de Ambiente y Desarrollo Sustentable"
(Argentine Nation) and CIEFAP (Centro de Investigación y Extensión Forestal
Andino Patagónico)

Contact
-------

Rodrigo E. Principe: rprincipe@ciefap.org.ar

Installation
------------

To use this package you must have installed and running Google Earth Engine
Python API: https://developers.google.com/earth-engine/python_install

Once you have that, proceed 

download the latest release from https://github.com/fitoprincipe/geebap/releases

::

  pip install geebap-(ver)-py2-none-any.whl

replace (ver) for the version you have downloaded. Example:

::

  pip install geebap-0.0.2-py2-none-any.whl


Available Collections
---------------------

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
----------------

- Satellite
- Distance to clouds and shadows masks
- Atmospheric Opacity
- Day of the year (doy)
- Masked pixels percentage
- Outliers
- Absolute value of a vegetation index

Available Indices
-----------------

- ndvi
- evi
- nbr

Some considerations
-------------------

- Sites size must not be too big. Works with 300 km2 tiles
- There is a module (sites.py) that has the avility to read a list of fusion table sites from a csv file

Basic Usage
-----------

.. code:: python

    from geebap import bap, season, filters, masks, \
                       scores, satcol, functions
    from geetools import tools
    
    import ee
    ee.Initialize()
    
    # COLLECTION
    col_group = satcol.ColGroup.Landsat()
    
    # SEASON
    a_season = season.Season.Growing_South()
    
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
    doy = scores.Doy()
    sat = scores.Satellite()
    op = scores.AtmosOpacity()
    out = scores.Outliers(("ndvi",))
    ind = scores.Index("ndvi")
    mascpor = scores.MaskPercent()
    dist = scores.CloudDist()
    
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
    
    one_value = tools.get_value(image,
                                site.centroid(),
                                30, 'client')
    
    print(one_value)

*Prints:*

::

   {u'ATM_OP': 9.0,
    u'BLUE': 0.03440000116825104,
    u'GREEN': 0.06920000165700912,
    u'NIR': 0.2443999946117401,
    u'RED': 0.06809999793767929,
    u'SWIR': 0.1915999948978424,
    u'SWIR2': 0.12039999663829803,
    u'col_id': 7.0,
    u'date': 14632.0,
    u'ndvi': 0.5641599893569946,
    u'score': 0.7584124471824276,
    u'score-atm-op': 0.983697501608319,
    u'score-cld-dist': 1.0,
    u'score-doy': 0.010969498225101475,
    u'score-index': 0.7820799946784973,
    u'score-maskper': 0.5821401476860046,
    u'score-outlier': 1.0,
    u'score-sat': 0.949999988079071}
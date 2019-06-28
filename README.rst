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

This work thanks to: "Dirección de Bosques - SAyDS" (Argentine Nation) and CIEFAP (Centro
de Investigación y Extensión Forestal Andino Patagónico)

Contact
-------

Rodrigo E. Principe: rprincipe@ciefap.org.ar

Installation
------------

To use this package you must have installed and running Google Earth Engine
Python API: https://developers.google.com/earth-engine/python_install

Once you have that, proceed 

::

  pip install geebap

this will install also `geetools` that you could use besides `geebap`

Installation in DataLab
-----------------------

After following Option 1 or 2 in https://developers.google.com/earth-engine/python_install,
open a new notebook and write:

.. code:: python

    import sys
    !{sys.executable} -m pip install geebap

Available Collections
---------------------

Collections come from `geetools.collection`. For examples see:
https://github.com/gee-community/gee_tools/tree/master/notebooks/collection

Available Scores
----------------

- Satellite
- Distance to clouds and shadows masks
- Atmospheric Opacity
- Day of the year (best_doy)
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

- Sites size should not be too big. Works with 300 km2 tiles

Basic Usage
-----------

If you are using Jupyter, you can download a notebook from
https://github.com/fitoprincipe/geebap/blob/master/Best_Available_Pixel_Composite.ipynb

else, if you are using another approach, like Spyder, create an empty script and
paste the following code:

.. code:: python

    import ee
    ee.Initialize()

    import geebap
    from geetools import tools

    import pprint
    pp = pprint.PrettyPrinter(indent=2)

    # SEASON
    a_season = geebap.Season('11-15', '03-15')

    # MASKS
    cld_mask = geebap.masks.Mask()

    # Combine masks in a tuple
    masks = (cld_mask,)

    # FILTERS
    filt_cld = geebap.filters.CloudCover()
    # filt_mask = geebap.filters.MaskCover() # Doesn't work

    # Combine filters in a tuple
    filters = (filt_cld,)#, filt_mask)

    # SCORES
    best_doy = geebap.scores.Doy('01-15', a_season)
    sat = geebap.scores.Satellite()
    out = geebap.scores.Outliers(("ndvi",))
    ind = geebap.scores.Index("ndvi")
    maskpercent = geebap.scores.MaskPercentKernel()
    dist = geebap.scores.CloudDist()

    # Combine scores in a tuple
    scores = (
        best_doy,
        sat,
        out,
        ind,
        maskpercent,
        dist
    )

    # BAP OBJECT
    BAP = geebap.Bap(range=(0, 0),
                     season=a_season,
                     masks=masks,
                     scores=scores,
                     filters=filters)

    # SITE
    site = ee.Geometry.Polygon([[-71.5,-42.5],
                                [-71.5,-43],
                                [-72,-43],
                                [-72,-42.5]])

    # COMPOSITE
    composite = BAP.build_composite_best(2019, site=site, indices=("ndvi",))

    # `composite` is a ee.Image object, so you can do anything
    # from here..
    one_value = tools.image.getValue(composite,
                                     site.centroid(),
                                     30, 'client')
    pp.pprint(one_value)

*Prints:*

::

    { 'blue': 733,
      'col_id': 29,
      'date': 20190201,
      'green': 552,
      'ndvi': 0.7752976417541504,
      'nir': 2524,
      'red': 313,
      'score': 5.351020336151123,
      'swir': 661,
      'swir2': 244,
      'thermal': 2883}
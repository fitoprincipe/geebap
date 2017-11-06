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
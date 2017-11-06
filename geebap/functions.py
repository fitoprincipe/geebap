#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ee
import time
import sys
import traceback

_execli_trace = False
_execli_times = 10
_execli_wait = 0


def execli(function, times=None, wait=None, trace=None):
    """ This function tries to excecute a client side Earth Engine function
    and retry as many times as needed

    :Example:
    .. code:: python

        from geetools import execli
        import ee
        ee.Initialize()

        # THIS IMAGE DOESN'E EXISTE SO IT WILL THROW AN ERROR
        img = ee.Image("wrongparam")

        # try to get the info with default parameters (10 times, wait 0 sec)
        info = execli(img.getInfo)()
        print info

        # try with custom param (2 times 5 seconds with traceback)
        info2 = execli(img.getInfo, 2, 5)
        print info2


    :param times: number of times it will try to excecute the function
    :type times: int
    :param wait: waiting time to excetue the function again
    :type wait: int
    :param trace: print the traceback
    :type trace: bool
    """
    if trace is None:
        trace = _execli_trace
    if times is None:
        times = _execli_times
    if wait is None:
        wait = _execli_wait

    try:
        times = int(times)
        wait = int(wait)
    except:
        print type(times)
        print type(wait)
        raise ValueError("los parametros 'times' y 'wait' deben ser numericos")

    def wrap(f):
        def wrapper(*args, **kwargs):
            r = range(times)
            for i in r:
                try:
                    # print "ejecutando {0} {1} veces, {2} seg cada vez".format(f.__name__, times, wait)
                    result = f(*args, **kwargs)
                except Exception as e:
                    print "intento n°", i+1, "en la funcion", f.__name__, "ERROR:", e
                    if trace:
                        traceback.print_exc()
                    if i < r[-1] and wait > 0:
                        print "esperando {} segundos...".format(str(wait))
                        time.sleep(wait)
                    elif i == r[-1]:
                        raise RuntimeError("Hubo un error al ejecutar la " \
                                           "funcion '{0}'".format(f.__name__))
                else:
                    return result

        return wrapper
    return wrap(function)


def pass_prop(imgcon, imgsin, prop):
    p = imgcon.get(prop)
    return imgsin.set(prop, p)


def pass_date(imgcon, imgsin):
    return pass_prop(imgcon, imgsin, "system:time_start")


def drange(ini, end, step=1, places=0):
    """ Create a range of floats

    :param ini: initial value (as in range)
    :param end: final value (as in range)
    :param step: Similar to range, except that if decimal places are specified
        the step is done between decimal places.
    :param places: decimal places
    :return: range
    :rtype: list
    """
    factor = 10**places if places>0 else 1
    ini *= factor
    end = end * factor - factor + 1
    result = [float(val) / factor for val in range(int(ini), int(end), step)]
    return result


def antiMask(img):
    """ Converts masked pixels into zeros

    :param img: Image contained in the Collection
    :type img: ee.Image
    """
    theMask = img.mask()
    return pass_date(img, theMask.where(1, img))


def simple_rename(img, suffix="", prefix="", separator="_"):
    """ Rename an image band using a given prefix and/or suffix

    :param suffix: after the name
    :type suffix: str
    :param prefix: before the name
    :type prefix: str
    :param separator: separator character. Defults to '_'
    :type separator: str

    :return: Image with bands renamed
    :rtype: ee.Image
    """
    bandas = img.bandNames()
    suf = ee.String(suffix)
    pref = ee.String(prefix)
    sep = ee.String(separator)

    def ren(banda):
        p = ee.Algorithms.If(pref, pref.cat(sep), "")
        s = ee.Algorithms.If(suf, sep.cat(suf), "")
        return ee.String(p).cat(ee.String(banda)).cat(ee.String(s))

    newbandas = bandas.map(ren)
    newimg = img.select(bandas, newbandas)
    return newimg


def sumBands(name="sum", bands=None):
    """ Add all bands values together and put the result in a new band

    :param name: name of the new band holding the added value
    :type name: str
    :return: a function to use in a mapping or iteration
    :rtype: function
    """
    def wrap(image):
        if bands is None:
            bn = image.bandNames()
        else:
            bn = ee.List(list(bands))

        nim = ee.Image(0).select([0], [name])

        # TODO: check if passed band names are in band names
        def sumBandas(n, ini):
            return ee.Image(ini).add(image.select([n]))

        newimg = ee.Image(bn.iterate(sumBandas, nim))

        return image.addBands(newimg)
    return wrap


def replace(to_replace, to_add):
    """ Replace one band of the image with a provided band

    :param img: Image containing the band to replace
    :type img: ee.Image
    :param to_replace: name of the band to replace. If the image hasn't got
        that band, it will be added to the image.
    :type to_replace: str
    :param to_add: Image (one band) containing the band to add. If an Image
        with more than one band is provided, it uses the first band.
    :type to_add: ee.Image
    :return: Same Image provided with the band replaced
    :rtype: ee.Image
    """
    def wrap(img):
        band = to_add.select([0])
        bands = img.bandNames()
        band = band.select([0], [to_replace])
        resto = bands.remove(to_replace)
        img_resto = img.select(resto)
        img_final = img_resto.addBands(band)
        return img_final
    return wrap

# FUNCIONES PARA ee.List
def listSubtract(list1, list2):
    """ Subtract two Earth Engine List Objects """

    def dif(ele, prim):
        prim = ee.List(prim)
        cond = list2.contains(ele)
        return ee.Algorithms.If(cond, prim, prim.add(ele))

    nl = ee.List(list1.iterate(dif, ee.List([])))
    return nl


def list_intersection(listEE1, listEE2):
    """ Find matching values. If listEE1 has duplicated values that are present
    on listEE2, all values from listEE1 will apear in the result

    :param listEE1: one Earth Engine List
    :param listEE2: the other Earth Engine List
    :return: list with the intersection (matching values)
    :rtype: ee.List
    """
    newlist = ee.List([])
    def wrap(element, first):
        first = ee.List(first)

        return ee.Algorithms.If(listEE2.contains(element), first.add(element), first)

    return ee.List(listEE1.iterate(wrap, newlist))


def list_diff(listEE1, listEE2):
    """ Difference between two earth engine lists

    :param listEE1: one list
    :param listEE2: the other list
    :return: list with the values of the difference
    :rtype: ee.List
    """
    return listEE1.removeAll(listEE2).add(listEE2.removeAll(listEE1)).flatten()


def replace_dict(toreplace):
    """ Replace many bands

    :param values: a dict containing the name of the bands as keys, and images
        containing only one bands as values
    :type values: dict
    :return:
    """
    valEE = ee.Dictionary(toreplace)
    bands = valEE.keys()  # bands to replace
    def wrap(img):
        todas = img.bandNames()  # all img bands
        inter = list_intersection(todas, bands)  # matching bands
        def f(el, first):
            i = ee.Image(first)
            return replace(el, ee.Image(valEE.get(el)))(i)

        return ee.Image(inter.iterate(f, img))
    return wrap


def get_value(img, point, scale=10):
    """ Return the value of all bands of the image in the specified point

    :param img: Image to get the info from
    :type img: ee.Image
    :param point: Point from where to get the info
    :type point: ee.Geometry.Point
    :param scale: The scale to use in the reducer. It defaults to 10 due to the
        minimum scale available in EE (Sentinel 10m)
    :type scale: int
    :return: Values of all bands in the ponit
    :rtype: dict
    """
    scale = int(scale)
    type = point.getInfo()["type"]
    if type != "Point":
        raise ValueError("Point must be ee.Geometry.Point")

    return img.reduceRegion(ee.Reducer.first(), point, scale).getInfo()


def replace_many(listEE, toreplace):
    """ Replace many elements of a Earth Engine List object

    :param listEE: list
    :type listEE: ee.List
    :param toreplace: values to replace
    :type toreplace: dict
    :return: list with replaced values
    :rtype: ee.List
    """
    for key, val in toreplace.iteritems():
        if val:
            listEE = listEE.replace(key, val)
    return listEE


def rename_bands(names, drop=False):
    """ Renames bands of images

    :param names: matching names where key is original name and values the
        new name
    :type names: dict
    :param drop: drop the non matching bands
    :type drop: bool
    :return: a function to rename images
    :rtype: function
    """
    def wrap(img):
        bandnames = img.bandNames()
        newnames = replace_many(bandnames, names)
        newimg = img.select(bandnames, newnames)
        if drop:
            return newimg.select(names.values())
        else:
            return newimg
    return wrap


def parameterize(original_range, final_range, bands=None):
    """ Parameterize from an original range (has to be a known range) to a
    final range in the elected bands.

    :param original_range: min and max range of the original image. Ej: (0, 1)
    :type original_range: tuple
    :param final_range: min and max range of the final image. Ej: (0.5, 2)
    :type final_range: tuple
    :param bands: bands to parameterize. If None, all bands will be
        parameterized.
    :type bands: list
    :return: function to use in a mapping or iteration
    :rtype: function
    """

    original_range = original_range if isinstance(original_range, ee.List) else ee.List(original_range)
    final_range = final_range if isinstance(final_range, ee.List) else ee.List(final_range)

    # Imagenes del min y max originales
    min0 = ee.Image.constant(original_range.get(0))
    max0 = ee.Image.constant(original_range.get(1))

    # Rango de min a max
    rango0 = max0.subtract(min0)

    # Imagenes del min y max final
    min1 = ee.Image.constant(final_range.get(0))
    max1 = ee.Image.constant(final_range.get(1))

    # Rango final
    rango1 = max1.subtract(min1)

    def wrap(img):
        # todas las bands
        todas = img.bandNames()

        # bands a parameterize. Si no se especifica se usan todas
        if bands:
            bandasEE = ee.List(bands)
        else:
            bandasEE = img.bandNames()

        inter = list_intersection(todas, bandasEE)
        diff = list_diff(todas, inter)
        imagen = img.select(inter)

        # Porcentaje del valor actual de la banda en el rango de valores
        porcent = imagen.subtract(min0).divide(rango0)

        # Teniendo en cuenta el porcentaje en el que se encuentra el valor
        # real en el rango real, calculo el valor en el que se encuentra segun
        # el rango final. Porcentaje*rango_final + min_final

        final = porcent.multiply(rango1).add(min1)

        # Agrego el resto de las bands que no se parametrizaron
        # final = final.addBands(img.select(diff))

        # VALE LA PENA ACLARAR QUE: siempre se le deben agregar las bands a la
        # imagen original y no al reves, para que mantenga las propiedades
        final = img.select(diff).addBands(final)

        return pass_date(img, final)
    return wrap


def replace_duplicate(list):
    """ replace duplicated values from a list adding a suffix with a number

    :param list: list to be processed
    :type list: ee.List
    :return: new list with renamed values
    :rtype: ee.List
    """
    def wrap(a):
        newlist = [a[0]]
        for i, v in enumerate(a):
            if i == 0: continue
            # t = a[i+1:]
            if v in newlist:
                if "_" in v:
                    two = v.split("_")
                    orig = two[0]
                    n = int(two[1])
                    newval = "{}_{}".format(orig, n+1)
                else:
                    newval = v+"_1"
                newlist.append(newval)
            else:
                newlist.append(v)
        return newlist

    new = wrap(list)
    while(new != list):
        list = new[:]
        new = wrap(new)
    return(new)


def get_size(col, sleep=0, step=5, limit=100):
    """ Obtain locally the size of a collection. If an error of 'too many
    concurrent aggregations' occurs, it will retry adding a step of time each
    time

    :param col: collection to get the size of
    :type col: ee.ImageCollection
    :param sleep: time to sleep each time (seconds)
    :type sleep: int
    :param step: time to add each new iteration (seconds)
    :type step: int
    :param limit: limit of time in wich it will raise the error
    :type limit: int
    :return: size of the collection
    :rtype: int
    """
    try:
        s = col.size().getInfo()
        return s
    except Exception as e:
        print str(e)
        cond = str(e) in "Too many concurrent aggregations."
        if cond and sleep<limit:
            print "esperando {} segundos".format(sleep)
            for r in range(sleep+1):
                sys.stdout.write(str(r+1)+".")
                time.sleep(1)
            return get_size(col, sleep+step)
        else:
            raise e


def select_match(col):
    """ Check the bands of all images and leave only the ones that are in all
    images of the collection.

    :param col: collection holding all images
    :type col: ee.ImageCollection
    :return: new collection
    :rtype: ee.ImageCollection
    """
    imglist = col.toList(100)

    # list de bandas de la primer imagen
    prim_bands = ee.List(ee.Image(imglist.get(0)).bandNames())
    rest = ee.List(imglist.slice(1))

    ini_rest = ee.List([])
    def frest(i, ini):
        bn = ee.Image(i).bandNames()
        return ee.List(ini).add(bn)

    # lista de listas de bandas del resto de las imagenes
    rest_bands = ee.List(rest.iterate(frest, ini_rest))

    init = ee.List([])

    def f(elem, ini):
        e = ee.String(elem)
        init2 = ee.Number(1)

        def ff(elem2, ini2):
            el = ee.List(elem2)
            i2 = ee.List(ini2)
            contain = el.contains(e)
            result = ee.Algorithms.If(contain, i2, ee.Number(0))
            return ee.Number(result)

        contain = ee.Number(rest_bands.iterate(ff, init2))
        inicast = ee.List(ini)

        result = ee.Algorithms.If(contain, inicast.add(e), inicast)
        return ee.List(result)

    sl = ee.List(prim_bands.iterate(f, init))

    def select(img):
        return img.select(sl)

    return col.map(select)


def nirXred(nir="NIR", red="RED", output="nirXred"):
    """ Creates a NIR times RED band

    :param nir: name of the NIR band
    :type nir: str
    :param red: name of the RED band
    :type red: str
    :param output: name of the output band
    :type output: str
    :return:
    :rtype: function
    """
    def wrap(img):
        n = img.select([nir])
        r = img.select([red])
        nirXred = n.multiply(r).select([0], [output])
        return img.addBands(nirXred)
    return wrap


if __name__ == "__main__":

    ee.Initialize()
    '''
    imagen = ee.Image("LANDSAT/LC8_L1T_TOA_FMASK/LC82310902013344LGN00").select(["B1","B2","B3"])
    m = imagen.select(["B1"]).lt(0.1).addBands(ee.Image(1)).addBands(ee.Image(1))
    i = imagen.updateMask(m)

    p = ee.Geometry.Point(-71.72029495239258, -42.78997046797438)

    print get_value(antiMask(i), p)

    
    todas = imagen.bandNames()
    otras = ee.List(["B1"])

    inter = list_intersection(todas, otras)
    print inter.getInfo()
    print list_diff(todas, inter).getInfo()

    
    i = ee.Image().select("hola")
    tarea = ee.batch.Export.image.toDrive(i, folder="P", fileNamePrefix="P")
    runonserver(tarea)
    # tarea.runonserver()
    
    l1 = ee.List([1,"dos","tres"])
    print l1.getInfo()

    l2 = replace_many(l1, {1:"NIR", "dos":"RED"})

    print l2.getInfo()
    
    i = rename_bands({"B1":"BLUE", "B2":"GREEN"}, True)(imagen)

    print get_value(imagen, p)
    print get_value(i, p)
    
    list = ee.List(["one", "two", "three", 4])
    newlist = replace_many(list, {"one": 1, 4:"four"})

    print newlist.getInfo()
    
    i = replace_dict({"B1":ee.Image(0), "B2":ee.Image(1)})(imagen)
    print get_value(imagen, p)
    print get_value(i, p)
    

    a = ee.List(["a", "a", "b"])
    b = ee.List(["a", "c"])

    i = list_intersection(a, b)

    print i.getInfo()
    
    a = ["cc", "trs", "uno", "dos", "uno", "uno", "dos", "uno"]

    print replace_duplicate(a)
    print a
    '''

    i1 = ee.Image(0).select([0], ["uno"])
    i2 = ee.Image(0).select([0], ["dos"])
    i3 = ee.Image(0).select([0], ["tres"])
    i4 = ee.Image(0).select([0], ["cuatro"])

    i12 = i1.addBands(i2).addBands(i4)
    i134 = i1.addBands(i3).addBands(i4)
    i14 = i1.addBands(i4)

    col = ee.ImageCollection([i12, i134, i14])

    col = select_match(col)

    for f in col.getInfo()["features"]:
        print f["bands"]
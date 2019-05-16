# -*- coding: utf-8 -*-
import ee
from geetools import collection


def get_id_col(id):
    """ get the corresponding collection of the given id """
    try:
        col = collection.IDS[id]
    except IndexError:
        raise IndexError
    else:
        return col


def get_col_id(col):
    return collection.IDS.index(col.id)


def get_col_id_image(col, name='col_id'):
    return ee.Image.constant(get_col_id(col)).rename(name).toUint8()


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
    bands = list(valEE.keys())  # bands to replace
    def wrap(img):
        todas = img.bandNames()  # all img bands
        inter = list_intersection(todas, bands)  # matching bands
        def f(el, first):
            i = ee.Image(first)
            return replace(el, ee.Image(valEE.get(el)))(i)

        return ee.Image(inter.iterate(f, img))
    return wrap


def replace_many(listEE, toreplace):
    """ Replace many elements of a Earth Engine List object

    :param listEE: list
    :type listEE: ee.List
    :param toreplace: values to replace
    :type toreplace: dict
    :return: list with replaced values
    :rtype: ee.List
    """
    for key, val in toreplace.items():
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
            return newimg.select(list(names.values()))
        else:
            return newimg
    return wrap


def replace_duplicate(list, separator="_"):
    """ replace duplicated values from a list adding a suffix with a number

    :param list: list to be processed
    :type list: list
    :param separator: string to separate the name and the suffix
    :type separator: str
    :return: new list with renamed values
    :rtype: list
    """
    def wrap(a):
        newlist = [a[0]]  # list with first element
        for i, v in enumerate(a):
            if i == 0: continue  # skip first element
            # t = a[i+1:]
            if v in newlist:
                if separator in v:
                    two = v.split(separator)
                    orig = two[0]
                    n = int(two[1])
                    newval = "{}{}{}".format(orig, separator, n+1)
                else:
                    newval = v+separator+"1"
                newlist.append(newval)
            else:
                newlist.append(v)
        return newlist

    new = wrap(list)
    while(new != list):
        list = new[:]
        new = wrap(new)
    return(new)


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


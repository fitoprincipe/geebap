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


def unmask_slc_off(image):
    """ Unmask pixels that are masked in ALL bands """
    mask = image.mask()
    reduced = mask.reduce('sum')
    slc_off = reduced.eq(0)
    unmasked = image.unmask()
    newmask = mask.where(slc_off, 1)
    return unmasked.updateMask(newmask)
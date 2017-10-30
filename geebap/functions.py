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


def drange(ini, fin, step=1, places=0):
    """ Funcion para crear un rango con numeros decimales

    :param ini: valor inicial (igual que range)
    :param fin: valor final (igual que range)
    :param step: paso. Similar a range, excepto que si se especifican los
        lugares decimales, el paso lo hace entre decimales.
    :param places: lugares decimales
    :return: rango con numeros decimales
    :rtype: list
    """
    factor = 10**places if places>0 else 1
    ini *= factor
    fin = fin*factor-factor+1
    result = [float(val)/factor for val in range(int(ini), int(fin), step)]
    return result


def antiMask(imagen):
    """ TRANSFORMA LOS PIXELES ENMASCARADOS EN 0

    ARGUMENTO: UNA IMAGEN

    SE USA PARA REALIZAR ARITMETICA ENTRE IMAGENES
    EJ: SI QUIERO SUMAR LOS VALORES DE LOS PIXELES
    DE DOS IMAGENES USANDO img1.add(img2) CUANDO EL
    PIXEL ESTA ENMASCARADO, EL RESULTADO ES mask Y
    NO LA SUMA ( 1,234 + mask = mask ) """
    theMask = imagen.mask()
    return pass_date(imagen, theMask.where(1, imagen))


def renombrar(img, sufijo="", prefijo="", separador="_"):
    """ Renombra las bandas de una imagen con un prefijo, un sufijo y/o
    un separador dado.

    :param sufijo: despues del nombre
    :type sufijo: str

    :param prefijo: antes del nombre
    :type prefijo: str

    :param separador: caracter que se usará como separador. Defult: '_'
    :type separador: str

    :return: La imagen con las bandas renombradas
    :rtype: ee.Image
    """
    bandas = img.bandNames()
    suf = ee.String(sufijo)
    pref = ee.String(prefijo)
    sep = ee.String(separador)

    def ren(banda):
        return suf.cat(sep).cat(ee.String(banda)).cat(sep).cat(suf)

    newbandas = bandas.map(ren)
    newimg = img.select(bandas, newbandas)
    return newimg


def sumBands(name="sum", bands=None):
    """ funcion para sumar los valores de todas las bandas
    Argumetos

    :param imagen: la imagen sobre la cual se quieren sumar las bandas
    :type imagen: ee.Image
    :param nombre: nombre para la nueva banda que contiene los valores
        sumados
    :type nombre: str
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
def listSubtract(lista1, lista2):
    """
    Funcion que resta dos listas de GEE. lista1 - lista2
    """

    def dif(ele, prim):
        prim = ee.List(prim)
        cond = lista2.contains(ele)
        return ee.Algorithms.If(cond, prim, prim.add(ele))

    nl = ee.List(lista1.iterate(dif, ee.List([])))
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


def parametrizar(rango_orig, rango_final, bandas=None):
    """ Funcion para parametrizar una imagen según los rangos dados

    :Argumentos:
    :param rango_orig: min y max rango de la imagen original. ejemplo: (0,1)
    :type rango_orig: tuple
    :param rango_final: min y max rango de la imagen resultante. ej: (0.5,2)
    :type rango_final: tuple
    :param bandas: bandas a parametrizar. Si es None se parametrizan todas.
    :type bandas: list

    :return: funcion para mapear una coleccion
    :rtype: function
    """

    rango_orig = rango_orig if isinstance(rango_orig, ee.List) else ee.List(rango_orig)
    rango_final = rango_final if isinstance(rango_final, ee.List) else ee.List(rango_final)

    # Imagenes del min y max originales
    min0 = ee.Image.constant(rango_orig.get(0))
    max0 = ee.Image.constant(rango_orig.get(1))

    # Rango de min a max
    rango0 = max0.subtract(min0)

    # Imagenes del min y max final
    min1 = ee.Image.constant(rango_final.get(0))
    max1 = ee.Image.constant(rango_final.get(1))

    # Rango final
    rango1 = max1.subtract(min1)

    def wrap(img):
        # todas las bandas
        todas = img.bandNames()

        # bandas a parametrizar. Si no se especifica se usan todas
        if bandas:
            bandasEE = ee.List(bandas)
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

        # Agrego el resto de las bandas que no se parametrizaron
        # final = final.addBands(img.select(diff))

        # VALE LA PENA ACLARAR QUE: siempre se le deben agregar las bandas a la
        # imagen original y no al reves, para que mantenga las propiedades
        final = img.select(diff).addBands(final)

        return pass_date(img, final)
    return wrap


def replace_duplicate(lista):
    """ reemplaza los valores duplicados de una lista agregandole el sufijo
    _n, siendo n la cantidad de veces que se repite

    :param lista:
    :return:
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

    new = wrap(lista)
    while(new != lista):
        lista = new[:]
        new = wrap(new)
    return(new)


def get_size(col, sleep=0, step=5, limit=100):
    """ Funcion para obtener localmente el tamaño de una coleccion, de tal
    forma que si lanza un error de 'too many concurrent aggregations'
    incremente el tiempo de espera gradualmente

    :param col: coleccion de la cual se quiere calcular el tamaño
    :return: tamaño de la coleccion
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
    """ Dejar las imagenes de una coleccion solo con las bandas que coincidan
    en todas las imagenes

    :param col:
    :return: la coleccion con las imagenes 'filtradas'
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
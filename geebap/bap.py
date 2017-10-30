#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Modulo principal para la creacion de un compuesto Best Available Pixel

Premisas:

El objeto BAP debería ser independiente del sitio (o area) y ¿el año?, estos se
definirian en los metodos del objeto..

objetoBAP = Bap(año_central, rango_años, colecciones, puntajes, mascaras,
                filtros, indices?)

los argumentos serían tuples de objetos.
Si las colecciones son None, entonces usa el año para determinar qué satelites
habia en esa temporada

metodo coleccion(sitio)

    toma las colecciones del objetoBAP, las filtra, enmascara y calcula puntaje
    en el sitio dado. Cada objeto de puntajes, mascaras y filtros debe tener
    un metodo map(**kwargs)
    Devuelve una coleccion

metodos de generacion de 1 compuesto:

    reduccion
    Aplica el metodo coleccion() y sobre la coleccion resultante aplica un
    metodo de reduccion

    unpix
    Aplica el metodo coleccion() y de la coleccion resultante elige el pixel
    con mejor puntaje total
"""

import ee
import satcol
import season as temp
import functions
import datetime
import date
import scores
import masks
import filters
import time
import sys
from collections import namedtuple

MIN_ANIO = 1970
MAX_ANIO = datetime.date.today().year

def check_type(name, param, type):
    if param and not isinstance(param, type):
        raise ValueError(
            "el param '{}' debe ser una {}".format(name, type.__name__))
    else:
        return


class Bap(object):
    debug = False
    verbose = True
    def __init__(self, anio=None, rango=(0, 0), colgroup=None, puntajes=None,
                 mascaras=None, filtros=None, bbox=0, temporada=None,
                 fmap=None):
        """

        :param anio:
        :type anio: int
        :param rango:
        :type rango: tuple
        :param colgroup:
        :type colgroup: satcol.ColGroup
        :param puntajes:
        :type puntajes: tuple
        :param mascaras:
        :type mascaras: tuple
        :param filtros:
        :type filtros: tuple
        :param bbox:
        :param temporada:
        :type temporada: temporada.Temporada
        """
        check_type("colecciones", colgroup, satcol.ColGroup)
        # check_type("puntajes", puntajes, tuple)
        # check_type("mascaras", mascaras, tuple)
        # check_type("filtros", filtros, tuple)
        check_type("anio", anio, int)
        # check_type("rango", rango, tuple)
        check_type("bbox", bbox, int)
        check_type("temporada", temporada, temp.Temporada)

        if anio < MIN_ANIO or anio > MAX_ANIO:
            raise ValueError(
        "El año debe ser mayor a {} y menor a {}".format(MIN_ANIO, MAX_ANIO))

        self.anio = anio
        self.rango = rango
        self.col = colgroup
        self.punt = puntajes
        self.masc = mascaras
        self.filtros = filtros
        self.bbox = bbox
        self.temporada = temporada
        self.fmap = fmap

    @property
    def date_to_set(self):
        return ee.Date(
            str(self.anio)+"-"+self.temporada.doy).millis().getInfo()

    @property
    def fecha_ini(self):
        return self.temporada.add_anio(self.anio-self.rango[0])[0]

    @property
    def fecha_fin(self):
        return self.temporada.add_anio(self.anio+self.rango[1])[1]

    @property
    def ini_temporada(self):
        return self.temporada.add_anio(self.anio)[0]

    @property
    def fin_temporada(self):
        return self.temporada.add_anio(self.anio)[1]

    @property
    def anios_range(self):
        try:
            i = self.anio - abs(self.rango[0])
            f = self.anio + abs(self.rango[1]) + 1

            return range(i, f)
        except:
            return None

    @property
    def nombre_puntajes(self):
        if self.punt:
            punt = [p.nombre for p in self.punt]
            return functions.replace_duplicate(punt)
        else:
            return []


    def collist(self):
        """ Lista de Colecciones. Si no se definen las colecciones en la
        creacion del objeto, se utiliza la lista priorizada segun la temporada
        :return: lista de colecciones que se usara segun los parametros
            que se usaron para la creacion del objeto
        :rtype: tuple
        """
        if self.col.familia() != "Landsat":
            return self.col.colecciones
        else:
            # Ids de las colecciones dadas
            s1 = set([col.ID for col in self.col.colecciones])

            # Ids de la lista de colecciones presentes en el rango de
            # temporadas
            s2 = set()
            for a in self.anios_range:
                s2 = s2.union(
                    set([col for col in temp.PrioridadTemporada.relacion[a]]))

            intersect = s1.intersection(s2)
            if Bap.debug:
                print "cols del grupo:", s1
                print "cols prioridad:", s2
                print "inteseccion de colecciones:", intersect
            return [satcol.Coleccion.from_id(ID) for ID in intersect]

    def coleccion(self, sitio, indices=None, normalizar=True, **kwargs):
        """
        :param indices: indices de vegetacion que se quieren calcular. Si es
            *None* no se calcula ningun indice
        :type indices: tuple
        :param sitio: La geometría del sitio, que puede provenir de distintos
            lugares. Usando este paquete: LugaresFT("sitio").filtro(id=id)
        :type sitio: ee.Geometry
        :return:
        """
        # Si no se pasa una funcion para aplicar antes de los puntajes, se
        # crea una que devuelva la misma imagen
        if self.fmap is None:
            fmap = lambda x: x
        else:
            fmap = self.fmap

        # colfinal = ee.ImageCollection()
        colfinal = ee.List([])

        # Obtengo la region del sitio
        try:
            region = sitio.geometry().bounds().getInfo()['coordinates'][0]
        except AttributeError:
            region = sitio.getInfo()['coordinates'][0]
        except:
            raise AttributeError

        # lista de nombres de los puntajes para sumarlos al final
        puntajes = self.nombre_puntajes
        maxpunt = reduce(
            lambda i, punt: i+punt.max, self.punt, 0) if self.punt else 1

        # Diccionario de cant de imagenes para incluir en las propiedades
        toMetadata = dict()

        if self.verbose: print "puntajes:", puntajes

        for colobj in self.collist():

            # Obtengo el ID de la coleccion
            cid = colobj.ID

            # Obtengo el nombre abreviado para agregar a los metadatos
            short = colobj.short

            # Imagen del bandID de la coleccion
            bid = colobj.bandIDimg

            # diccionario para agregar a los metadatos con la relacion entre
            # satelite y bandID
            # prop_codsat = {colobj.ID: colobj.bandID}
            toMetadata["codsat_"+short] = colobj.bandID

            # Coleccion completa de EE
            c = colobj.colEE

            # Filtro por el sitio
            # TODO: usar el bbox si está seteado
            if isinstance(sitio, ee.Feature): sitio = sitio.geometry()
            c2 = c.filterBounds(sitio)

            # Renombra las bandas aca?
            # c2 = c2.map(col.rename())

            if self.verbose: print "\nSatelite:", colobj.ID
            if self.debug: print " TAM DESP FILTRO SITIO:", c2.size().getInfo()

            # Filtro por los años
            for anio in self.anios_range:
                # Creo un nuevo objeto de coleccion con el id
                col = satcol.Coleccion.from_id(cid)
                # puntajes = []

                ini = self.temporada.add_anio(anio)[0]
                fin = self.temporada.add_anio(anio)[1]

                if self.verbose: print "ini:", ini, ",fin:", fin

                # Filtro por fecha
                c = c2.filterDate(ini, fin)

                if self.debug:
                    n = c.size().getInfo()
                    print "    TAM DESP DE FILTRO DATE:", n

                ## FILTROS ESTABAN ACA

                # Si despues de los filtros no quedan imgs, saltea..
                size = c.size().getInfo()
                if self.verbose: print "tam desp de filtros:", size
                if size == 0: continue  # 1

                # corto la imagen con la region para minimizar los calculos
                def cut(img):
                    return img.clip(sitio)
                c = c.map(cut)

                # Mascaras
                if self.masc:
                    for m in self.masc:
                        c = c.map(
                            m.map(col=col, anio=anio, colEE=c))
                        if self.debug:
                            print " DESP DE LA MASCARA "+m.nombre, \
                                ee.Image(c.first()).bandNames().getInfo()

                # Transformo los valores enmascarados a cero
                c = c.map(functions.antiMask)

                # Renombra las bandas con los datos de la coleccion
                c = c.map(col.rename(drop=True))

                # Cambio las bandas en comun de las colecciones
                bandasrel = []

                if self.debug:
                    print " DESP DE RENOMBRAR LAS BANDAS:", \
                        ee.Image(c.first()).bandNames().getInfo()

                # Escalo a 0-1
                c = c.map(col.escalar())
                if self.debug:
                    if c.size().getInfo() > 0:
                        print " DESP DE ESCALAR:", \
                            ee.Image(c.first()).bandNames().getInfo()

                # Indices
                if indices:
                    for i in indices:
                        f = col.INDICES[i]
                        c = c.map(f)
                        if self.debug: print c.size().getInfo()

                # Antes de aplicar los puntajes, aplico la funcion que pasa
                # el usuario
                c = c.map(fmap)



                # Puntajes
                if self.punt:
                    for p in self.punt:
                        if self.verbose: print "** "+p.nombre+" **"
                        # Espero el tiempo seteado en cada puntaje
                        sleep = p.sleep
                        for t in range(sleep):
                            sys.stdout.write(str(t+1)+".")
                            time.sleep(1)
                        c = c.map(p.map(col=col, anio=anio, colEE=c, geom=sitio))

                        # DEBUG
                        if self.debug and n > 0:
                            geom = sitio if isinstance(sitio, ee.Geometry)\
                                         else sitio.geometry()
                            print "puntaje:", functions.get_value(
                                ee.Image(c.first()), geom.centroid())

                # Filtros
                if self.filtros:
                    for filtro in self.filtros:
                        c = filtro.apply(c, col=col, anio=self.anio)

                ## INDICES ESTABA ACA

                ## ESCALAR ESTABA ACA

                # Selecciona solo las bandas que tienen en comun todas las
                # Colecciones

                # METODO ANTERIOR: funcionaba, pero si agregaba una banda
                # con fmap, no se seleccionaba
                '''
                def sel(img):
                    puntajes_ = puntajes if self.punt else []
                    indices_ = list(indices) if indices else []
                    relaciones = self.col.bandasrel()
                    return img.select(relaciones+puntajes_+indices_)
                c = c.map(sel)
                '''

                # METODO NUEVO: selecciono las bandas en comun desp de unir
                # todas las colecciones usando un metodo distinto

                if self.debug:
                    if c.size().getInfo() > 0:
                        print " DESP DE SELECCIONAR BANDAS EN COMUN:",\
                            ee.Image(c.first()).bandNames().getInfo()

                # Convierto los valores de las mascaras a 0
                c = c.map(functions.antiMask)

                # Agrego la banda de fecha a la imagen
                c = c.map(date.FechaEE.map())

                # Agrego la banda bandID de la coleccion
                def addBandID(img):
                    return img.addBands(bid)
                c = c.map(addBandID)

                if self.debug: print " DESP DE AGREGAR BANDA bandID:", \
                    ee.Image(c.first()).bandNames().getInfo()

                # Convierto a lista para agregar a la coleccion anterior
                c_list = c.toList(2500)
                colfinal = colfinal.cat(c_list)

                # Agrego col id y anio al diccionario para propiedades
                cant_imgs = "nro_imgs_{cid}_{a}".format(cid=short, a=anio)
                toMetadata[cant_imgs] = functions.get_size(c)

        # comprueba que la lista final tenga al menos un elemento
        # s_fin = colfinal.size().getInfo()  # 2
        s_fin = functions.get_size(colfinal)

        # DEBUG
        if self.verbose: print "tamanio col final:", s_fin

        if s_fin > 0:
            newcol = ee.ImageCollection(colfinal)

            # Selecciono las bandas en comun de todas las imagenes
            newcol = functions.select_match(newcol)

            if self.debug: print " ANTES DE CALC ptotal:", \
                ee.Image(newcol.first()).bandNames().getInfo()

            # Calcula el puntaje total sumando los puntajes
            ftotal = functions.sumBands("ptotal", puntajes)
            newcol = newcol.map(ftotal)

            if normalizar:
                newcol = newcol.map(
                    functions.parametrizar((0, maxpunt), (0, 1), ("ptotal",)))

            if self.debug:
                print " DESP DE CALC ptotal:", \
                    ee.Image(newcol.first()).bandNames().getInfo()

            output = namedtuple("ColBap", ("col", "dictprop"))
            return output(newcol, toMetadata)
        else:
            return None

    @staticmethod
    def calcUnpix_generic(col, puntaje):
        """
        """
        imgCol = col
        # tamcol = funciones.execli(imgCol.size().getInfo)()

        img = imgCol.qualityMosaic(puntaje)

        if Bap.debug:
            print " DESP DE qualityMosaic:", img.bandNames().getInfo()

        # CONVIERTO LOS VALORES ENMASCARADOS EN 0
        img = functions.antiMask(img)

        return img

    def calcUnpix(self, sitio, nombre="ptotal", bandas=None, **kwargs):
        """
        :param bandas: Nombre de las bandas a incluir en la img final. Si es
            *None* se incluyen todas
        :type bandas: tuple
        :param nombre:
        :type nombre: str
        :param sitio:
        :type sitio: ee.Geometry
        :param indices:
        :type indices: tuple
        :param normalizar:
        :type normalizar: bool
        :return:
        """
        colbap = self.coleccion(sitio=sitio, **kwargs)

        col = colbap.col
        prop = colbap.dictprop

        img = Bap.calcUnpix_generic(col, nombre)

        img = img if bandas is None else img.select(*bandas)

        fechaprop = {"system:time_start": self.date_to_set}
        prop.update(fechaprop)
        return img.set(prop)

    def calcUnpixLegacy(self, sitio, nombre="ptotal", bandas=None, **kwargs):
        """

        :param sitio:
        :param nombre:
        :param bandas:
        :param kwargs:
        :return:
        """
        colbap = self.coleccion(sitio=sitio, **kwargs)

        imgCol = colbap.col
        prop = colbap.dictprop

        # SI HAY ALGUNA IMAGEN
        if imgCol is not None:
            img0 = ee.Image(0)

            # ALTERNATIVA PARA OBTENER LA LISTA DE BANDAS
            primera = ee.Image(imgCol.first())
            listaband = primera.bandNames()
            cantBandas = functions.execli(listaband.size().getInfo)()

            lista = []

            # CREO LA IMAGEN INICIAL img0 CON LAS BANDAS NECESARIAS EN 0
            for r in range(0, cantBandas):
                img0 = ee.Image(0).addBands(img0)
                lista.append(r)

            img0 = img0.select(lista, listaband)

            def final(img, maxx):
                maxx = ee.Image(maxx)
                ptotal0 = maxx.select(nombre)
                ptotal0 = ptotal0.mask().where(1, ptotal0)

                ptotal1 = img.select(nombre)
                ptotal1 = ptotal1.mask().where(1, ptotal1)

                masc0 = ptotal0.gt(ptotal1)
                masc1 = masc0.Not()

                maxx = maxx.updateMask(masc0)
                maxx = maxx.mask().where(1, maxx)

                img = img.updateMask(masc1)
                img = img.mask().where(1, img)

                maxx = maxx.add(img)

                return ee.Image(maxx)

            img = ee.Image(imgCol.iterate(final, img0))

            # SETEO LAS PROPIEDADES
            fechaprop = {"system:time_start": self.date_to_set}
            # img = img.set(fechaprop)
            prop.update(fechaprop)

            # Elimino las barras invertidas
            prop = {k.replace("/","_"):v for k, v in prop.iteritems()}

            img = img if bandas is None else img.select(*bandas)

            output = namedtuple("calcUnpixLegacy", ("image", "col"))

            return output(self.setprop(img, **prop), imgCol)
        # SI NO HAY IMAGENES
        else:
            print "No se puede realizar el proceso porque las colecciones " \
                  "\n" + "no poseen imagenes. Devuelve: None"
            return None

    def setprop(self, img, **kwargs):
        """ Setea las propiedades que provienen del objeto Bap a una imagen
        :return:
        """
        d = {"fecha_ini": date.FechaEE.local(self.fecha_ini),
             "fecha_fin": date.FechaEE.local(self.fecha_fin),
             }

        # Agrega los argumentos como propiedades
        d.update(kwargs)

        return img.set(d)

    @classmethod
    def White(cls, anio, rango, temporada):
        psat = scores.Psat()
        pdist = scores.Pdist()
        pdoy = scores.Pdoy(temporada=temporada)
        pop = scores.Pop()
        colG = satcol.ColGroup.SR()
        masc = masks.Nubes()
        filt = filters.NubesPor()

        pjes = (psat, pdist, pdoy, pop)
        mascs = (masc,)
        filts = (filt,)

        return cls(anio, rango, puntajes=pjes, mascaras=mascs, filtros=filts,
                   colgroup=colG, temporada=temporada)

    @classmethod
    def Modis(cls, anio, rango, temporada, indice=None):
        """
        :param indice: Indice de vegetacion para el cual se va a calcular
            el puntaje. Debe coincidir con el que se usará en el metodo de
            generacion del Bap (ej: CalcUnpix). Si es None se omite el calculo
            del puntaje por indice, lo que puede genera malos resultados
        :return:
        """
        # Puntajes
        pdist = scores.Pdist()
        pdoy = scores.Pdoy(temporada=temporada)
        pmasc = scores.Pmascpor()
        pout = scores.Poutlier(("nirXred",))

        colG = satcol.ColGroup.Modis()
        masc = masks.Nubes()
        filt = filters.MascPor(0.3)

        pjes = [pdist, pdoy, pmasc, pout]

        if indice:
            pindice = scores.PIndice(indice)
            pout2 = scores.Poutlier((indice,))
            pjes.append(pindice)
            pjes.append(pout2)

        mascs = (masc,)
        filts = (filt,)

        nirxred = functions.nirXred()

        '''
        return cls(anio, rango, puntajes=pjes, mascaras=mascs, filtros=filts,
                   colgroup=colG, temporada=temporada, fmap=nirxred)
        '''
        return cls(anio, rango, colgroup=colG, temporada=temporada,
                   mascaras=mascs, puntajes=pjes, fmap=nirxred, filtros=filts)

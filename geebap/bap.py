#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Main module holding the Bap Class and its methods """

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

MIN_YEAR = 1970
MAX_YEAR = datetime.date.today().year

def check_type(name, param, type):
    if param and not isinstance(param, type):
        raise ValueError(
            "argument '{}' must be {}".format(name, type.__name__))
    else:
        return


class Bap(object):
    debug = False
    verbose = True
    def __init__(self, year=None, range=(0, 0), colgroup=None, scores=None,
                 masks=None, filters=None, bbox=0, season=None,
                 fmap=None):
        """ The Bap object is designed to be independet of the site and the
        method that will be used to generate the composite.

        :param year: The year of the final composite. If the season covers two
            years the last one will be used. Ej.

            ..code::

                season = Season(ini="15-12", end="15-01")
                bap = Bap(year=2000)

            to generate the composite the code will use images from
            15-12-1999 to 15-01-2000
        :type year: int
        :param range:
        :type range: tuple
        :param colgroup:
        :type colgroup: satcol.ColGroup
        :param scores:
        :type scores: tuple
        :param masks:
        :type masks: tuple
        :param filters:
        :type filters: tuple
        :param bbox:
        :param season:
        :type season: season.Season
        """
        check_type("colgroup", colgroup, satcol.ColGroup)
        # check_type("scores", scores, tuple)
        # check_type("masks", masks, tuple)
        # check_type("filters", filters, tuple)
        check_type("year", year, int)
        # check_type("range", range, tuple)
        # check_type("bbox", bbox, int)
        check_type("season", season, temp.Season)

        if year < MIN_YEAR or year > MAX_YEAR:
            raise ValueError(
        "The year must be greatre than {} and less than {}".format(
            MIN_YEAR, MAX_YEAR))

        self.year = year
        self.range = range
        self.col = colgroup
        self.scores = scores
        self.masks = masks
        self.filters = filters
        # self.bbox = bbox
        self.season = season
        self.fmap = fmap

    @property
    def date_to_set(self):
        return ee.Date(
            str(self.year) + "-" + self.season.doy).millis().getInfo()

    @property
    def ini_date(self):
        return self.season.add_year(self.year - self.range[0])[0]

    @property
    def end_date(self):
        return self.season.add_year(self.year + self.range[1])[1]

    @property
    def ini_season(self):
        return self.season.add_year(self.year)[0]

    @property
    def end_season(self):
        return self.season.add_year(self.year)[1]

    @property
    def date_range(self):
        try:
            i = self.year - abs(self.range[0])
            f = self.year + abs(self.range[1]) + 1

            return range(i, f)
        except:
            return None

    @property
    def score_names(self):
        if self.scores:
            punt = [p.name for p in self.scores]
            return functions.replace_duplicate(punt)
        else:
            return []


    def collist(self):
        """ List of Collections. If the list is not defined in the creation of
        the Bap object, a prioritized list is used according to the season.
        :return: list of collections that will be used
        :rtype: tuple
        """
        if self.col.family() != "Landsat":
            return self.col.collections
        else:
            # Ids de las collections dadas
            s1 = set([col.ID for col in self.col.collections])

            # Ids de la lista de collections presentes en el range de
            # temporadas
            s2 = set()
            for a in self.date_range:
                s2 = s2.union(
                    set([col for col in temp.SeasonPriority.relation[a]]))

            intersect = s1.intersection(s2)
            if Bap.debug:
                print "Collections inside ColGroup:", s1
                print "Prior Collections:", s2
                print "Intersection:", intersect
            return [satcol.Collection.from_id(ID) for ID in intersect]

    def collection(self, site, indices=None, normalize=True, bbox=0):
        """
        :param indices: vegetation indices to include in the final image. If
            None, no index is calculated
        :type indices: tuple
        :param site: Site geometry
        :type site: ee.Geometry
        :param normalize: Whether to normalize the final score from 0 to 1
            or not
        :type normalize: bool
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

        # Obtengo la region del site
        try:
            region = site.geometry().bounds().getInfo()['coordinates'][0]
        except AttributeError:
            region = site.getInfo()['coordinates'][0]
        except:
            raise AttributeError

        # lista de nombres de los puntajes para sumarlos al final
        scores = self.score_names
        maxpunt = reduce(
            lambda i, punt: i+punt.max, self.scores, 0) if self.scores else 1

        # Diccionario de cant de imagenes para incluir en las propiedades
        toMetadata = dict()

        if self.verbose: print "scores:", scores

        for colobj in self.collist():

            # Obtengo el ID de la coleccion
            cid = colobj.ID

            # Obtengo el name abreviado para agregar a los metadatos
            short = colobj.short

            # Imagen del col_id de la coleccion
            bid = colobj.bandIDimg

            # diccionario para agregar a los metadatos con la relation entre
            # satelite y col_id
            # prop_codsat = {colobj.ID: colobj.col_id}
            toMetadata["col_id_"+short] = colobj.col_id

            # Collection completa de EE
            c = colobj.colEE

            # Filtro por el site
            if isinstance(site, ee.Feature): site = site.geometry()
            c2 = c.filterBounds(site)

            # Renombra las bandas aca?
            # c2 = c2.map(col.rename())

            if self.verbose: print "\nSatellite:", colobj.ID
            if self.debug: print " SIZE AFTER FILTER SITE:", c2.size().getInfo()

            # Filtro por los años
            for anio in self.date_range:
                # Creo un nuevo objeto de coleccion con el id
                col = satcol.Collection.from_id(cid)
                # puntajes = []

                ini = self.season.add_year(anio)[0]
                end = self.season.add_year(anio)[1]

                if self.verbose: print "ini:", ini, ",end:", end

                # Filtro por fecha
                c = c2.filterDate(ini, end)

                if self.debug:
                    n = c.size().getInfo()
                    print "    SIZE AFTER FILTER DATE:", n

                ## FILTROS ESTABAN ACA

                # Si despues de los filters no quedan imgs, saltea..
                size = c.size().getInfo()
                if self.verbose: print "size after filters:", size
                if size == 0: continue  # 1

                # corto la imagen con la region para minimizar los calculos
                if bbox == 0:
                    def cut(img):
                        return img.clip(site)
                else:
                    def cut(img):
                        bounds = site.buffer(bbox)
                        return img.clip(bounds)

                c = c.map(cut)

                # Mascaras
                if self.masks:
                    for m in self.masks:
                        c = c.map(
                            m.map(col=col, year=anio, colEE=c))
                        if self.debug:
                            print " BANDS AFTER THE MASK "+m.nombre, \
                                ee.Image(c.first()).bandNames().getInfo()

                # Transformo los valores enmascarados a cero
                c = c.map(functions.antiMask)

                # Renombra las bandas con los datos de la coleccion
                c = c.map(col.rename(drop=True))

                # Cambio las bandas en comun de las collections
                bandasrel = []

                if self.debug:
                    print " AFTER RENAMING BANDS:", \
                        ee.Image(c.first()).bandNames().getInfo()

                # Escalo a 0-1
                c = c.map(col.do_scale())
                if self.debug:
                    if c.size().getInfo() > 0:
                        print " AFTER SCALING:", \
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
                if self.scores:
                    for p in self.scores:
                        if self.verbose: print "** "+p.name+" **"
                        # Espero el tiempo seteado en cada puntaje
                        sleep = p.sleep
                        for t in range(sleep):
                            sys.stdout.write(str(t+1)+".")
                            time.sleep(1)
                        c = c.map(p.map(col=col, year=anio, colEE=c, geom=site))

                        # DEBUG
                        if self.debug and n > 0:
                            geom = site if isinstance(site, ee.Geometry)\
                                         else site.geometry()
                            print "value:", functions.get_value(
                                ee.Image(c.first()), geom.centroid())

                # Filtros
                if self.filters:
                    for filtro in self.filters:
                        c = filtro.apply(c, col=col, anio=self.year)

                ## INDICES ESTABA ACA

                ## ESCALAR ESTABA ACA

                # Selecciona solo las bandas que tienen en comun todas las
                # Colecciones

                # METODO ANTERIOR: funcionaba, pero si agregaba una band
                # con fmap, no se seleccionaba
                '''
                def sel(img):
                    puntajes_ = puntajes if self.scores else []
                    indices_ = list(indices) if indices else []
                    relaciones = self.col.bandsrel()
                    return img.select(relaciones+puntajes_+indices_)
                c = c.map(sel)
                '''

                # METODO NUEVO: selecciono las bandas en comun desp de unir
                # todas las collections usando un metodo distinto

                if self.debug:
                    if c.size().getInfo() > 0:
                        print " AFTER SELECTING COMMON BANDS:",\
                            ee.Image(c.first()).bandNames().getInfo()

                # Convierto los valores de las mascaras a 0
                c = c.map(functions.antiMask)

                # Agrego la band de fecha a la imagen
                c = c.map(date.Date.map())

                # Agrego la band col_id de la coleccion
                def addBandID(img):
                    return img.addBands(bid)
                c = c.map(addBandID)

                if self.debug: print " AFTER ADDING col_id BAND:", \
                    ee.Image(c.first()).bandNames().getInfo()

                # Convierto a lista para agregar a la coleccion anterior
                c_list = c.toList(2500)
                colfinal = colfinal.cat(c_list)

                # Agrego col id y year al diccionario para propiedades
                cant_imgs = "n_imgs_{cid}_{a}".format(cid=short, a=anio)
                toMetadata[cant_imgs] = functions.get_size(c)

        # comprueba que la lista final tenga al menos un elemento
        # s_fin = colfinal.size().getInfo()  # 2
        s_fin = functions.get_size(colfinal)

        # DEBUG
        if self.verbose: print "final collection size:", s_fin

        if s_fin > 0:
            newcol = ee.ImageCollection(colfinal)

            # Selecciono las bandas en comun de todas las imagenes
            newcol = functions.select_match(newcol)

            if self.debug: print " BEFORE score:", scores, "\n", \
                ee.Image(newcol.first()).bandNames().getInfo()

            # Calcula el puntaje total sumando los puntajes
            ftotal = functions.sumBands("score", scores)
            newcol = newcol.map(ftotal)

            if self.debug:
                print " AFTER score:", \
                    ee.Image(newcol.first()).bandNames().getInfo()

            if normalize:
                newcol = newcol.map(
                    functions.parameterize((0, maxpunt), (0, 1), ("score",)))

            if self.debug:
                print " AFTER parametrize:", \
                    ee.Image(newcol.first()).bandNames().getInfo()

            output = namedtuple("ColBap", ("col", "dictprop"))
            return output(newcol, toMetadata)
        else:
            return None

    @staticmethod
    def calcUnpix_generic(col, score):
        """
        """
        imgCol = col
        # tamcol = funciones.execli(imgCol.size().getInfo)()

        img = imgCol.qualityMosaic(score)

        if Bap.debug:
            print " AFTER qualityMosaic:", img.bandNames().getInfo()

        # CONVIERTO LOS VALORES ENMASCARADOS EN 0
        img = functions.antiMask(img)

        return img

    def calcUnpix(self, site, name="score", bands=None, **kwargs):
        """ Generate the BAP composite using the pixels that have higher
        final score. This version uses GEE function 'qualiatyMosaic"

        :param site: Site geometry
        :type site: ee.Geometry
        :param name: name of the band that has the final score
        :type name: str
        :param bands: name of the bands to include in the final image
        :type bands: list
        :param kwargs:
        :return: A namedtuple:
            .image = the Best Available Pixel Composite (ee.Image)
            .col = the collection of images used to generate the BAP
                (ee.ImageCollection)
        :rtype: namedtuple
        """
        colbap = self.collection(site=site, **kwargs)

        col = colbap.col
        prop = colbap.dictprop

        img = Bap.calcUnpix_generic(col, name)

        img = img if bands is None else img.select(*bands)

        fechaprop = {"system:time_start": self.date_to_set}
        prop.update(fechaprop)
        return img.set(prop)

    def bestpixel(self, site, name="score", bands=None,
                  indices=None, normalize=True, bbox=0):
        """ Generate the BAP composite using the pixels that have higher
        final score. This is a custom method

        :param site: Site geometry
        :type site: ee.Geometry
        :param name: name of the band that has the final score
        :type name: str
        :param bands: name of the bands to include in the final image
        :type bands: list
        :param kwargs: see Bap.collection() method
        :return: A namedtuple:
            .image = the Best Available Pixel Composite (ee.Image)
            .col = the collection of images used to generate the BAP
                (ee.ImageCollection)
        :rtype: namedtuple
        """
        colbap = self.collection(site=site, indices=indices,
                                 normalize=normalize, bbox=bbox)

        imgCol = colbap.col
        prop = colbap.dictprop

        output = namedtuple("bestpixel", ("image", "col"))

        # SI HAY ALGUNA IMAGEN
        if imgCol is not None:
            img0 = ee.Image(0)

            # ALTERNATIVA PARA OBTENER LA LISTA DE BANDAS
            first = ee.Image(imgCol.first())
            listbands = first.bandNames()
            nbands = functions.execli(listbands.size().getInfo)()

            thelist = []

            # CREO LA IMAGEN INICIAL img0 CON LAS BANDAS NECESARIAS EN 0
            for r in range(0, nbands):
                img0 = ee.Image(0).addBands(img0)
                thelist.append(r)

            img0 = img0.select(thelist, listbands)

            def final(img, maxx):
                maxx = ee.Image(maxx)
                ptotal0 = maxx.select(name)
                ptotal0 = ptotal0.mask().where(1, ptotal0)

                ptotal1 = img.select(name)
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
            dateprop = {"system:time_start": self.date_to_set}
            # img = img.set(dateprop)
            prop.update(dateprop)

            # Elimino las barras invertidas
            prop = {k.replace("/","_"):v for k, v in prop.iteritems()}

            img = img if bands is None else img.select(*bands)

            return output(self.setprop(img, **prop), imgCol)
        # SI NO HAY IMAGENES
        else:
            print "The process can not be done because the Collections have " \
                  "no images. Returns None"
            return output(None, None)

    def setprop(self, img, **kwargs):
        """ Sets properties to the composite
        :return:
        """
        d = {"ini_date": date.Date.local(self.ini_date),
             "end_date": date.Date.local(self.end_date),
             }

        # Agrega los argumentos como propiedades
        d.update(kwargs)

        return img.set(d)

    @classmethod
    def White(cls, year, range, season):
        psat = scores.Satellite()
        pdist = scores.CloudDist()
        pdoy = scores.Doy(season=season)
        pop = scores.AtmosOpacity()
        colG = satcol.ColGroup.SR()
        masc = masks.Clouds()
        filt = filters.CloudsPercent()

        pjes = (psat, pdist, pdoy, pop)
        mascs = (masc,)
        filts = (filt,)

        return cls(year, range, scores=pjes, masks=mascs, filters=filts,
                   colgroup=colG, season=season)

    @classmethod
    def Modis(cls, year, range, season, index=None):
        """
        :param index: Indice de vegetacion para el cual se va a calcular
            el puntaje. Debe coincidir con el que se usará en el metodo de
            generacion del Bap (ej: CalcUnpix). Si es None se omite el calculo
            del puntaje por index, lo que puede genera malos resultados
        :return:
        """
        # Puntajes
        pdist = scores.CloudDist()
        pdoy = scores.Doy(season=season)
        pmasc = scores.MaskPercent()
        pout = scores.Outliers(("nirXred",))

        colG = satcol.ColGroup.Modis()
        masc = masks.Clouds()
        filt = filters.MaskPercent(0.3)

        pjes = [pdist, pdoy, pmasc, pout]

        if index:
            pindice = scores.PIndice(index)
            pout2 = scores.Outliers((index,))
            pjes.append(pindice)
            pjes.append(pout2)

        mascs = (masc,)
        filts = (filt,)

        nirxred = functions.nirXred()

        return cls(year, range, colgroup=colG, season=season,
                   masks=mascs, scores=pjes, fmap=nirxred, filters=filts)

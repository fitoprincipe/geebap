#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ee
import requests
import funciones
import traceback


class LugaresFT(object):
    """ El objeto LugaresFT contiene los sitios alojados en Fusion
        Tables

        :param nombre: nombre del sitio
        :type nombre: str

        :param fc: FeatureCollection que se usara si el nombre no esta en la
            tabla de sitios. Default: None
        :type fc: ee.FeatureCollection

        :param idname: Nombre de la columna que contiene los ids
        :type idname: str

        :Propiedades:

        :nombre: Nombre del objeto
        :nombres: Nombres posibles
        :id_ft: id de la fusion table (ej: 1oWq2NBh5F2VGdbdXDDmj-l2JpuKNP8WySYoOmtQH
        :id: nombre del campo que contiene el identificador unico (id)
        :ROI: la feature collection completa
        :name: nombre del campo que contiene nombres identificatorios
    """
    def __init__(self, nombre, fc=None, idname=None):

        if type(nombre) is not str:
            raise ValueError("'nombre' debe ser un string")

        self.nombre = nombre

        hoja1 = self.json()

        self.nombres = []
        for fila in hoja1:
            nomb = fila["NOMBRE"]
            if nomb != "":
                self.nombres.append(nomb)
            if nomb == self.nombre:
                self.id = fila["ID"].encode("utf8")
                self.id_ft = fila["ID_FT"].encode("utf8")
                self.name = fila["NAME"].encode("utf8")
                self.ROI = ee.FeatureCollection("ft:" + self.id_ft)

        if self.nombre not in self.nombres:
            if fc is None or idname is None:
                print "El sitio indicado no existe y los parametros 'fc' y" \
                      "'idname' no estan completos como para crear un objeto" \
                      "nuevo, las opciones son:"
                for n in self.nombres:
                    print n.encode("utf8")
                raise ValueError("El sitio indicado no existe y no pudo ser creado")
            elif type(fc) is ee.featurecollection.FeatureCollection and type(idname) is str:
                self.id = idname
                self.id_ft = None
                self.name = None
                self.ROI = fc

    @staticmethod
    def json():
        url = "https://script.google.com/macros/s/AKfycbygukdW3tt8sCPcFDlkM" \
              "nMuNu9bH5fpt7bKV50p2bM/exec?id=11hMJ-rI_VtRxcUl3GSpUtLQ1L3yfIj" \
              "eApRAaZczHK28&sheet=Hoja1"

        cont = requests.get(url)
        sheet = funciones.execli(cont.json, 10, 5)()

        hoja1 = sheet["Hoja1"]

        return hoja1

    @staticmethod
    def opciones():
        hoja = LugaresFT.json()
        print "Las opciones son:"
        for fila in hoja:
            nomb = fila["NOMBRE"]
            if nomb != "":
                print nomb

    def filtroID(self, un_id):
        """ Metodo para filtrar el lugar con un id

        :param un_id: el id que quiero filtrar
        :type un_id: int

        :return: tuple con dos parametros:
        :rtype: tuple

        :lugar [0]: la coleccion filtrada (ee.Feature)
        :region [1]: la region (list)
        """
        # self.un_id = un_id
        try:
            lugar = self.ROI.filterMetadata(self.id, "equals", un_id)
            lugar = ee.Feature(lugar.first())
            lugar = lugar.set("origen", self.nombre, "id", un_id)
            region = lugar.geometry().bounds().getInfo()['coordinates'][0]
            return lugar, region
        except Exception as e:
            print "Hubo un error al filtrar el ID"
            print e
            return None

    def filtroNombre(self, nombre):
        """
        Metodo para filtrar el lugar con el nombre
        Argumentos:
        nombre = el nombre que quiero filtrar (int)

        Devuelve:
        ROI (ee.Feature), region (lista python para usar en <exportar>)
        """
        lugar = self.ROI.filterMetadata(self.name, "equals", nombre)
        lugar = lugar.set("origen", self.nombre)
        region = lugar.geometry().bounds().getInfo()['coordinates'][0]
        return lugar, region

    def filtro(self, bbox=False, **kwargs):
        """
        Filtra la colección según el parametro que se pase.

        Obligatorios (excluyentes):
        id = filtra por el id. (int)
        nombre = filtra por nombre. (str)

        Opcionales:
        bbox = indica si se usara el rectangulo contenedor o no. (bool)

        Devuelve:
        ROI (ee.Feature), region (lista python para usar en <exportar>)
        """
        try:
            if "id" in kwargs.keys():
                self.un_id = kwargs["id"]
                # self.lugar = self.ROI.filterMetadata(self.id, "equals",self.un_id)
                lugar, region = self.filtroID(self.un_id)
            elif "nombre" in kwargs.keys():
                nombre = kwargs["nombre"]
                # self.lugar = self.ROI.filterMetadata(self.name, "equals",self.nombre)
                lugar, region = self.filtroNombre(nombre)
            elif "ids" in kwargs.keys():
                ids = kwargs["ids"]
                lugar = self.ROI.filter(ee.Filter.inList(self.id, ids))
                union = ee.Feature(lugar.union().first())
                region = union.geometry().bounds().getInfo()["coordinates"]
            else:
                "Se debe pasar al menos un argumento (id, ids o nombre)"
                return None
        except Exception as e:
            print "Hubo un error en el filtrado"
            print e
            traceback.print_exc()
            return None

        for i in range(11):
            try:
                if bbox:
                    roi = lugar.geometry().bounds()
                    area = roi.area(10)
                    buf = area.sqrt().divide(ee.Number(2))
                    roi = roi.buffer(buf)
                    region = roi.bounds().getInfo()['coordinates'][0]
                else:
                    region = lugar.geometry().bounds().getInfo()['coordinates'][0]
            except Exception as e:
                print "Hubo un error al obtener la region (CIEFAP.objetos.LugaresFT.filtro())"
                print e
            else:
                break

        return lugar, region

    def cantidad_imagenes(self, id, temporada, ventana=(0, 0), **kwargs):
        """ Imprime y devuelve la cantidad de imagenes totales de todos los
        satelites disponibles en esa temporada. Se pueden usar los kwargs de
        la clase PriorTempLand

        :param id: Id del tile a verificar
        :type id: int
        :param temporada: Temporada de crecimiento que se quiere comprobar.
            EJ: 1990 (se fija desde fines del año 1989 a principios de 1990)
        :type temporada: int
        :param ventana: ventana de años que se quiere comprobar. EJ: (2,2) y
            año 1990 se fija en 1988, 1989, 1990, 1991, 1992. Default: (0,0)
        :type ventana: tuple
        :return: la cantidad de imagenes en un diccionario, y la suma de todos
        :rtype: tuple
        """
        rango = range(temporada-ventana[0], temporada+ventana[1]+1)
        roi, region = self.filtro(id=id)
        imagenes = {}

        total = 0
        for anio in rango:
            temp = PriorTempLand(anio, **kwargs)
            lista = temp.idCol()
            ini = temp.tempini
            fin = temp.tempfin

            for sat in lista:
                col = ee.ImageCollection(sat).filterBounds(roi).filterDate(ini, fin)
                images = col.getInfo()["features"]
                size = len(images)
                imlist = []
                for img in images:
                    id = img["id"]
                    imlist.append(id)

                # cantidad[sat+"_"+str(anio)] = size
                imagenes[sat+"_"+str(anio)] = imlist
                total += int(size)

        for key, value in imagenes.iteritems():
            print key, ":", value

        return imagenes, total
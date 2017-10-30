import unittest
import ee
from .. import satcol, scores, bap, season, masks, filters

ee.Initialize()

class TestBAP(unittest.TestCase):

    def setUp(self):
        self.filtro = filters.NubesPor()
        self.nubes = masks.Nubes()
        self.temporada = season.Temporada.Crecimiento_patagonia()
        self.coleccion = satcol.ColGroup.Landsat()
        self.pmascpor = scores.Pmascpor()
        self.pindice = scores.Pindice()
        self.sitio = ee.Geometry.Polygon(
        [[[-71.78, -42.79],
          [-71.78, -42.89],
          [-71.57, -42.89],
          [-71.57, -42.79]]])

    def test_bap2016_0(self):
        objbap = bap.Bap(anio=2016, colgroup=self.coleccion,
                         temporada=self.temporada,
                         puntajes=(self.pindice, self.pmascpor),
                         mascaras=(self.nubes,), filtros=(self.filtro,))

        sitio = self.sitio

        unpix = objbap.calcUnpixLegacy(sitio, indices=("ndvi",))
        img = unpix.image
        col = unpix.col

        self.assertIsInstance(img, ee.Image)
        self.assertIsInstance(col, ee.ImageCollection)

        idict = img.getInfo()
        cdict = col.getInfo()
        self.assertIsInstance(idict, dict)
        self.assertIsInstance(cdict, dict)
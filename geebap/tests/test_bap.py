import unittest
import ee
from .. import satcol, scores, bap, season, masks, filters, functions

ee.Initialize()

class TestBAP(unittest.TestCase):

    def setUp(self):
        # FILTERS
        self.filtro = filters.NubesPor()

        # MASKS
        self.nubes = masks.Nubes()

        # SEASON
        self.temporada = season.Season.Crecimiento_patagonia()

        # COLLECTIONS
        self.coleccion = satcol.ColGroup.Landsat()

        # SCORES
        self.psat = scores.Psat()
        self.pop = scores.Pop()
        self.pmascpor = scores.Pmascpor()
        self.pindice = scores.Pindice()
        self.pout = scores.Poutlier(("ndvi",))
        self.pdoy = scores.Pdoy()

        # SITES
        self.sitio = ee.Geometry.Polygon(
        [[[-71.78, -42.79],
          [-71.78, -42.89],
          [-71.57, -42.89],
          [-71.57, -42.79]]])
        self.centroid = self.sitio.centroid()

    def test_bap2016_0(self):
        objbap = bap.Bap(year=2016, colgroup=self.coleccion,
                         season=self.temporada,
                         scores=(self.pindice, self.pmascpor, self.psat,
                                 self.pout, self.pop, self.pdoy),
                         masks=(self.nubes,), filters=(self.filtro,))

        sitio = self.sitio

        unpix = objbap.bestpixel(sitio, indices=("ndvi",))
        img = unpix.image
        col = unpix.col

        self.assertIsInstance(img, ee.Image)
        self.assertIsInstance(col, ee.ImageCollection)

        idict = img.getInfo()
        cdict = col.getInfo()
        self.assertIsInstance(idict, dict)
        self.assertIsInstance(cdict, dict)

        value = functions.get_value(img, self.centroid, 30)
        print value

        self.assertIsInstance(value, dict)
        # self.assertEqual(value["BLUE"], 0.008500000461935997)
        # self.assertEqual(value["bandID"], 12.0)
        # self.assertEqual(value["ndvi"], 0.872759222984314)
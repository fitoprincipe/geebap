import unittest
import ee
from .. import colecciones, puntajes, bap, temporada, mascaras, filtros, sitios

ee.Initialize()

class TestBAP(unittest.TestCase):

    def setUp(self):
        self.filtro = filtros.NubesPor()
        self.nubes = mascaras.Nubes()
        self.temporada = temporada.Temporada.Crecimiento_patagonia()
        self.coleccion = colecciones.ColGroup.Landsat()
        self.pmascpor = puntajes.Pmascpor()
        self.pindice = puntajes.Pindice()
        self.sitio = sitios.LugaresFT("continente")

    def test_bap2016_0(self):
        objbap = bap.Bap(anio=2016, colgroup=self.coleccion,
                         temporada=self.temporada,
                         puntajes=(self.pindice, self.pmascpor),
                         mascaras=(self.nubes,), filtros=(self.filtro,))

        sitio, region = self.sitio.filtroID(1)

        unpix = objbap.calcUnpixLegacy(sitio, indices=("ndvi",))
        img = unpix.image
        col = unpix.col

        self.assertIsInstance(img, ee.Image)
        self.assertIsInstance(col, ee.ImageCollection)

        idict = img.getInfo()
        cdict = col.getInfo()
        self.assertIsInstance(idict, dict)
        self.assertIsInstance(cdict, dict)

if __name__ == '__main__':
    unittest.main()
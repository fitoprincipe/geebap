import unittest
import ee
import os
from .. import sites

ee.Initialize()

class Test_sites(unittest.TestCase):

    def setUp(self):
        script_dir = os.path.dirname(__file__)
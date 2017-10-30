from geebap import sites
from geebap.tests import test_bap
import unittest

unittest.main(test_bap)

'''
listURL = sites.from_gsheet("https://script.google.com/macros/s/AKfycbygukdW3tt8sCPcFDlkM" \
                            "nMuNu9bH5fpt7bKV50p2bM/exec?id=11hMJ-rI_VtRxcUl3GSpUtLQ1L3yfIj" \
                            "eApRAaZczHK28&sheet=Hoja1", "Hoja1", "NOMBRE", "ID_FT", "ID")

for s in listURL:
    print s
    print s.name, s.id_ft, s.id_fld
'''


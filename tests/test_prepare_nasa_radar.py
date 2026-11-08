"""Tests for NASA radar preparation using generated rasters (no restricted imagery)."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.prepare_nasa_radar import convert


class TestNasaRadar(unittest.TestCase):
    def test_linear_to_db_and_georeference(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            profile=dict(driver="GTiff",height=520,width=520,count=1,dtype="float32",
                         crs="EPSG:4326",transform=from_origin(91.0,25.0,.0002,.0002))
            for name,value in (("vv",.1),("vh",.01)):
                with rasterio.open(root/f"{name}.tif","w",**profile) as dst:
                    dst.write(np.full((520,520),value,dtype="float32"),1)
            result=convert(root/"vv.tif",root/"vh.tif",root/"out.tif",units="linear")
            self.assertEqual(result["width"],512)
            self.assertEqual(result["valid_pixels"],512*512)
            with rasterio.open(root/"out.tif") as dst:
                self.assertEqual(str(dst.crs),"EPSG:4326")
                self.assertEqual(dst.count,2)
                self.assertTrue(np.allclose(dst.read(1),-10,atol=.001))
                self.assertTrue(np.allclose(dst.read(2),-20,atol=.001))
                self.assertEqual(dst.read_masks(1).min(),255)

    def test_misaligned_bands_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            profile=dict(driver="GTiff",height=512,width=512,count=1,dtype="float32",
                         crs="EPSG:4326",transform=from_origin(91,25,.0002,.0002))
            for name,origin in (("vv",91),("vh",92)):
                profile["transform"]=from_origin(origin,25,.0002,.0002)
                with rasterio.open(root/f"{name}.tif","w",**profile) as dst:
                    dst.write(np.ones((512,512),dtype="float32"),1)
            with self.assertRaisesRegex(ValueError,"identical CRS"):
                convert(root/"vv.tif",root/"vh.tif",root/"out.tif",units="linear")


if __name__=="__main__":
    unittest.main()

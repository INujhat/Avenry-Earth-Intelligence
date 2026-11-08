"""Unit tests for ESA SNAP graph construction; full processing needs SNAP and NASA data."""
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.process_nasa_grd import graph, process


class TestSnapGraph(unittest.TestCase):
    def test_required_processing_stages(self):
        with tempfile.TemporaryDirectory() as d:
            xml = graph(Path(d)/"source.zip", Path(d)/"out.tif", 20)
            root = ET.fromstring(xml)
            nodes = {n.attrib["id"]: n for n in root.findall("node")}
            self.assertEqual(nodes["Calibration"].findtext("operator"), "Calibration")
            self.assertEqual(nodes["Terrain"].findtext("operator"), "Terrain-Correction")
            self.assertEqual(nodes["Orbit"].findtext("operator"), "Apply-Orbit-File")
            self.assertEqual(nodes["Write"].findtext("operator"), "Write")
            self.assertEqual(nodes["Calibration"].findtext("./parameters/selectedPolarisations"), "VV,VH")
            self.assertEqual(nodes["Terrain"].findtext("./parameters/mapProjection"), "EPSG:4326")
            self.assertEqual(nodes["Calibration"].findtext("./sources/sourceProduct").attrib["refid"], "Orbit")
            self.assertEqual(nodes["Terrain"].findtext("./sources/sourceProduct").attrib["refid"], "Calibration")

    def test_refuse_missing_or_invalid_zip(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "GRD ZIP"):
                process(Path(d)/"missing.zip", Path(d)/"out.tif")


if __name__ == "__main__":
    unittest.main()

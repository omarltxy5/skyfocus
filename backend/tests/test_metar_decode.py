import unittest

from app.inference.metar_decode import decode_metar


class TestMetarDecode(unittest.TestCase):
    def test_sample_metar(self) -> None:
        raw = "KJFK 211051Z 01013KT 10SM FEW037 BKN065 17/07 A3013"
        d = decode_metar(raw)
        self.assertEqual(d.station, "KJFK")
        self.assertEqual(d.flight_category, "VFR")
        self.assertTrue(any("Wind from" in e for e in d.explanations))
        self.assertTrue(any("17" in e for e in d.explanations))


if __name__ == "__main__":
    unittest.main()

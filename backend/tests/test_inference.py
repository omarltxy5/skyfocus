"""Unit tests for Step 2 inference modules."""

from __future__ import annotations

import unittest

from app.inference.metar import parse_metar, parse_wind
from app.inference.models import FlightPhase
from app.inference.phase import classify_phase
from app.inference.runway import infer_active_runway, infer_from_metar, wind_components_kt
from app.inference.trajectory import douglas_peucker_latlon


class TestMetarParser(unittest.TestCase):
    def test_parse_wind_standard(self) -> None:
        metar = "KJFK 211751Z 27015G25KT 10SM FEW050 12/04 A3012"
        wind = parse_wind(metar)
        assert wind is not None
        self.assertEqual(wind.direction_deg, 270)
        self.assertEqual(wind.speed_kt, 15.0)
        self.assertEqual(wind.gust_kt, 25.0)

    def test_parse_wind_vrb(self) -> None:
        wind = parse_wind("KLAX 211851Z VRB03KT 6SM BR")
        assert wind is not None
        self.assertTrue(wind.variable)
        self.assertIsNone(wind.direction_deg)
        self.assertEqual(wind.speed_kt, 3.0)

    def test_parse_wind_calm(self) -> None:
        wind = parse_wind("KORD 211951Z 00000KT 10SM")
        assert wind is not None
        self.assertEqual(wind.speed_kt, 0.0)

    def test_parse_metar_full(self) -> None:
        report = parse_metar("KJFK 211751Z 36010KT 10SM")
        self.assertEqual(report.icao, "KJFK")
        assert report.wind is not None
        self.assertEqual(report.wind.direction_deg, 360)


class TestWindComponents(unittest.TestCase):
    def test_pure_headwind(self) -> None:
        hw, cw = wind_components_kt(270, 10, 270)
        self.assertAlmostEqual(hw, 10.0, places=5)
        self.assertAlmostEqual(cw, 0.0, places=5)

    def test_pure_tailwind(self) -> None:
        hw, cw = wind_components_kt(90, 10, 270)
        self.assertAlmostEqual(hw, -10.0, places=5)
        self.assertAlmostEqual(cw, 0.0, places=5)

    def test_crosswind_magnitude(self) -> None:
        hw, cw = wind_components_kt(360, 10, 270)
        self.assertAlmostEqual(hw, 0.0, places=5)
        self.assertAlmostEqual(abs(cw), 10.0, places=5)


class TestRunwayInference(unittest.TestCase):
    def test_kjfk_wind_from_310_favors_31(self) -> None:
        from app.inference.models import Wind

        wind = Wind(direction_deg=310, speed_kt=12)
        result = infer_active_runway("KJFK", wind)
        self.assertIn(result.active_runway, ("31L", "31R"))
        self.assertGreater(result.headwind_kt, 8.0)

    def test_infer_from_metar_integration(self) -> None:
        metar = "KJFK 211751Z 28018KT 10SM"
        result = infer_from_metar(metar)
        self.assertEqual(result.icao, "KJFK")
        self.assertGreater(len(result.all_runways), 0)
        self.assertEqual(result.active_runway, result.all_runways[0].designator)

    def test_vrb_raises(self) -> None:
        from app.inference.models import Wind

        with self.assertRaises(ValueError):
            infer_active_runway("KJFK", Wind(direction_deg=None, speed_kt=5, variable=True))


class TestPhaseStateMachine(unittest.TestCase):
    def test_climb_high_altitude(self) -> None:
        snap = classify_phase(15_000, 1_500)
        self.assertEqual(snap.phase, FlightPhase.CLIMB)

    def test_cruise_level(self) -> None:
        snap = classify_phase(35_000, 0)
        self.assertEqual(snap.phase, FlightPhase.CRUISE)

    def test_descent_enroute(self) -> None:
        snap = classify_phase(20_000, -1_200)
        self.assertEqual(snap.phase, FlightPhase.DESCENT)

    def test_approach_low_descent(self) -> None:
        snap = classify_phase(1_800, -800)
        self.assertEqual(snap.phase, FlightPhase.APPROACH)

    def test_go_around_from_approach(self) -> None:
        prev = classify_phase(2_000, -600)
        self.assertEqual(prev.phase, FlightPhase.APPROACH)

        ga = classify_phase(2_000, 2_500, previous=prev)
        self.assertEqual(ga.phase, FlightPhase.GO_AROUND)
        self.assertTrue(ga.go_around)

    def test_go_around_not_without_approach_history(self) -> None:
        snap = classify_phase(2_000, 2_500)
        self.assertNotEqual(snap.phase, FlightPhase.GO_AROUND)


class TestDouglasPeucker(unittest.TestCase):
    def test_keeps_endpoints(self) -> None:
        coords = [(40.64, -73.78), (40.65, -73.77), (40.66, -73.76)]
        out = douglas_peucker_latlon(coords, epsilon_m=5000)
        self.assertEqual(out[0], coords[0])
        self.assertEqual(out[-1], coords[-1])

    def test_thins_collinear_middle(self) -> None:
        # Nearly straight line — middle point should drop at tight epsilon
        coords = [
            (40.0, -74.0),
            (40.001, -73.999),
            (40.002, -73.998),
        ]
        out = douglas_peucker_latlon(coords, epsilon_m=5.0)
        self.assertEqual(len(out), 2)

    def test_preserves_corner(self) -> None:
        coords = [
            (40.0, -74.0),
            (40.0, -73.5),
            (40.5, -73.5),
        ]
        out = douglas_peucker_latlon(coords, epsilon_m=10.0)
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()

"""Testy kalibrace měřítka studs/m (M2.9/M2.10).

Pokrytí: převody jednotek, determinismus, nula/zápor, nekonzistence,
UNKNOWN, <2 nezávislé reference -> BLOCKED, M3 brána, tvar kontraktu.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Inspection.scale_calibration import (
    CalibrationBlockedError,
    CalibrationError,
    calibrate,
    default_references,
    require_verified_for_m3,
    usable_for_m3,
)
from src.common import units


def _meas(scale, refs=None, exclude=()):
    """Syntetická konzistentní měření: studs = SI * scale."""
    refs = refs if refs is not None else default_references()
    return {r["param"]: (None if r["param"] in exclude
                         else r["value_si"] * scale)
            for r in refs}


class TestUnitConversions(unittest.TestCase):
    def test_mm_m_roundtrip(self):
        self.assertAlmostEqual(units.m_to_mm(units.mm_to_m(2719.0)), 2719.0)
        self.assertAlmostEqual(units.mm_to_m(1585.0), 1.585)

    def test_tire_diameters_nominal(self):
        self.assertAlmostEqual(
            units.tire_diameter_mm(255, 40, 19), 686.6, places=6)
        self.assertAlmostEqual(
            units.tire_diameter_mm(275, 40, 19), 702.6, places=6)

    def test_tire_diameter_bad_input(self):
        for args in ((0, 40, 19), (-255, 40, 19), (255, 0, 19)):
            with self.assertRaises(ValueError):
                units.tire_diameter_mm(*args)

    def test_studs_m_roundtrip(self):
        self.assertAlmostEqual(
            units.studs_to_m(units.m_to_studs(2.719)), 2.719)


class TestCalibrationShape(unittest.TestCase):
    def test_contract_keys(self):
        res = calibrate(measurements_studs=_meas(3.0))
        self.assertEqual(
            sorted(res),
            ["blocked_reason", "deviations_pct", "estimates",
             "inspection_ref", "measurements_studs", "overall_status",
             "references", "uncertainty", "vehicle_id"])
        for ref in res["references"]:
            self.assertEqual(sorted(ref),
                             ["param", "source", "status", "unit", "value_si"])
            self.assertEqual(ref["unit"], "m")  # SI + studs, nic jiného

    def test_consistent_all_verified_is_verified(self):
        refs = [r for r in default_references() if r["status"] == "VERIFIED"]
        res = calibrate(references=refs,
                        measurements_studs=_meas(3.0, refs))
        self.assertEqual(res["overall_status"], "VERIFIED")
        self.assertIsNone(res["blocked_reason"])
        for est in res["estimates"]:
            self.assertAlmostEqual(est["studs_per_meter"], 3.0, places=9)

    def test_mixed_status_is_estimated(self):
        # Rozvor VERIFIED + pneu ESTIMATED, konzistentní -> ESTIMATED.
        res = calibrate(measurements_studs=_meas(3.0))
        self.assertEqual(res["overall_status"], "ESTIMATED")

    def test_determinism(self):
        kw = {"measurements_studs": _meas(3.0),
              "inspection_ref": "sha256:abc"}
        first = calibrate(**kw)
        again = calibrate(**dict(
            reversed(list(kw.items()))))  # jiné pořadí klíčů
        self.assertEqual(first, again)
        shuffled = dict(reversed(list(kw["measurements_studs"].items())))
        self.assertEqual(first,
                         calibrate(measurements_studs=shuffled,
                                   inspection_ref="sha256:abc"))


class TestBlockedConditions(unittest.TestCase):
    def test_fewer_than_two_independent_refs_blocked(self):
        # Jen rodina pneu (tire_d_f + tire_d_r = 1 nezávislá) -> BLOCKED.
        refs = [r for r in default_references()
                if r["param"].startswith("tire_d")]
        res = calibrate(references=refs,
                        measurements_studs=_meas(3.0, refs))
        self.assertEqual(res["overall_status"], "BLOCKED")
        self.assertTrue(res["blocked_reason"])

    def test_single_family_tracks_blocked(self):
        refs = [r for r in default_references()
                if r["param"].startswith("track")]
        res = calibrate(references=refs,
                        measurements_studs=_meas(3.0, refs))
        self.assertEqual(res["overall_status"], "BLOCKED")

    def test_inconsistency_blocked(self):
        # Rozvor naměřen o 20 % větší než zbytek -> rozptyl > 5 %.
        meas = _meas(3.0)
        assert meas["wheelbase"] is not None
        meas["wheelbase"] = meas["wheelbase"] * 1.20
        res = calibrate(measurements_studs=meas)
        self.assertEqual(res["overall_status"], "BLOCKED")
        self.assertIn("nekonzistent", res["blocked_reason"])

    def test_unknown_measurements(self):
        res = calibrate(measurements_studs={p: None for p in
                                            ("wheelbase", "track_f", "track_r",
                                             "tire_d_f", "tire_d_r")})
        self.assertEqual(res["overall_status"], "UNKNOWN")
        self.assertIsNone(res["blocked_reason"])
        self.assertEqual(res["estimates"], [])

    def test_zero_negative_measurement_rejected(self):
        for bad in (0, 0.0, -1.5):
            with self.assertRaises(CalibrationError):
                calibrate(measurements_studs={**_meas(3.0),
                                              "wheelbase": bad})

    def test_zero_negative_reference_rejected(self):
        refs = default_references()
        refs[0] = dict(refs[0], value_si=0.0)
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))
        refs[0] = dict(refs[0], value_si=-2.719)
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))

    def test_non_si_unit_rejected(self):
        refs = default_references()
        refs[0] = dict(refs[0], unit="mm", value_si=2719.0)
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))

    def test_missing_source_rejected(self):
        refs = default_references()
        refs[0] = dict(refs[0], source="")
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))


class TestM3Gate(unittest.TestCase):
    def test_verified_passes_gate(self):
        refs = [r for r in default_references() if r["status"] == "VERIFIED"]
        fam_meas = {r["param"]: r["value_si"] * 3.0 for r in refs}
        res = calibrate(references=refs, measurements_studs=fam_meas)
        self.assertEqual(res["overall_status"], "VERIFIED")
        self.assertTrue(usable_for_m3(res))
        self.assertIs(require_verified_for_m3(res), res)

    def test_unverified_never_reaches_m3(self):
        base = _meas(3.0)
        assert base["wheelbase"] is not None
        inconsistent = dict(base)
        inconsistent["wheelbase"] = base["wheelbase"] * 1.2
        for res in (
            calibrate(measurements_studs=base),  # ESTIMATED
            calibrate(measurements_studs={}),    # UNKNOWN
            calibrate(measurements_studs=inconsistent),  # BLOCKED
        ):
            self.assertNotEqual(res["overall_status"], "VERIFIED")
            self.assertFalse(usable_for_m3(res))
            with self.assertRaises(CalibrationBlockedError):
                require_verified_for_m3(res)

    def test_estimated_does_not_pass_gate(self):
        # Plná sada (VERIFIED rozvor/rozchody + ESTIMATED pneu) je
        # konzistentní, ale ESTIMATED — do M3 nesmí (pouze VERIFIED).
        res = calibrate(measurements_studs=_meas(3.0))
        self.assertEqual(res["overall_status"], "ESTIMATED")
        self.assertFalse(usable_for_m3(res))
        with self.assertRaises(CalibrationBlockedError):
            require_verified_for_m3(res)

    def test_gate_rejects_non_dict(self):
        self.assertFalse(usable_for_m3(None))  # type: ignore[arg-type]
        self.assertFalse(usable_for_m3("VERIFIED"))  # type: ignore[arg-type]
        with self.assertRaises(CalibrationBlockedError):
            require_verified_for_m3(None)  # type: ignore[arg-type]


class TestJeepTemplateGroundTruth(unittest.TestCase):
    """Reálná měření JeepTemplate (Studio ground-truth, Agent B/D):
    rozvor 10.5228 / rozchody 5.9907 / pneu 2.7 (Ball) proti
    mustangovským referencím M1 -> rozptyl 7.44 % -> BLOCKED."""

    JEEP_MEAS = {
        "wheelbase": 10.522796630859375,
        "track_f": 5.99066162109375,
        "track_r": 5.99072265625,
        "tire_d_f": 2.7,
        "tire_d_r": 2.7,
    }

    def test_jeep_template_is_blocked(self):
        res = calibrate(measurements_studs=dict(self.JEEP_MEAS))
        self.assertEqual(res["overall_status"], "BLOCKED")
        self.assertTrue(res["blocked_reason"])
        self.assertIn("7.44", res["blocked_reason"])
        self.assertEqual(res["estimates"], [])
        self.assertIsNone(res["uncertainty"]["combined_studs_per_meter"])
        self.assertIsNone(res["uncertainty"]["rel_pct"])

    def test_jeep_template_blocked_from_m3(self):
        res = calibrate(measurements_studs=dict(self.JEEP_MEAS))
        self.assertFalse(usable_for_m3(res))
        with self.assertRaises(CalibrationBlockedError):
            require_verified_for_m3(res)


class TestEdgeCases(unittest.TestCase):
    def test_nan_inf_measurement_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(CalibrationError):
                calibrate(measurements_studs={**_meas(3.0),
                                              "wheelbase": bad})

    def test_nan_inf_reference_rejected(self):
        for bad in (float("nan"), float("inf")):
            refs = default_references()
            refs[0] = dict(refs[0], value_si=bad)
            with self.assertRaises(CalibrationError):
                calibrate(references=refs, measurements_studs=_meas(3.0))

    def test_nan_inf_uncertainty_rejected(self):
        refs = default_references()
        refs[0] = dict(refs[0], uncertainty_si=float("nan"))
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))
        with self.assertRaises(CalibrationError):
            calibrate(measurements_studs=_meas(3.0),
                      u_studs=float("inf"))

    def test_negative_uncertainty_rejected(self):
        refs = default_references()
        refs[0] = dict(refs[0], uncertainty_si=-0.001)
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))
        with self.assertRaises(CalibrationError):
            calibrate(measurements_studs=_meas(3.0), u_studs=-0.1)

    def test_null_value_requires_unknown_status(self):
        refs = default_references()
        refs[0] = dict(refs[0], value_si=None)  # status VERIFIED -> chyba
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))

    def test_missing_unit_rejected(self):
        refs = default_references()
        refs[0] = dict(refs[0], unit=None)
        with self.assertRaises(CalibrationError):
            calibrate(references=refs, measurements_studs=_meas(3.0))

    def test_unknown_and_duplicate_param_rejected(self):
        refs = default_references()
        bad = dict(refs[0], param="wheelbase2")
        with self.assertRaises(CalibrationError):
            calibrate(references=[bad] + refs[1:],
                      measurements_studs=_meas(3.0))
        with self.assertRaises(CalibrationError):
            calibrate(references=refs + [dict(refs[0])],
                      measurements_studs=_meas(3.0))
        with self.assertRaises(CalibrationError):
            calibrate(measurements_studs={**_meas(3.0), "rozvor": 8.0})

    def test_wheelbase_only_blocked(self):
        # Jen 1 nezávislá rodina (rozvor) -> BLOCKED.
        refs = [r for r in default_references()
                if r["param"] == "wheelbase"]
        res = calibrate(references=refs,
                        measurements_studs=_meas(3.0, refs))
        self.assertEqual(res["overall_status"], "BLOCKED")

    def test_uncertainty_present_on_success(self):
        refs = [r for r in default_references() if r["status"] == "VERIFIED"]
        res = calibrate(references=refs,
                        measurements_studs=_meas(3.0, refs))
        self.assertEqual(res["overall_status"], "VERIFIED")
        u = res["uncertainty"]
        self.assertIsNotNone(u["combined_studs_per_meter"])
        self.assertIsNotNone(u["rel_pct"])
        self.assertTrue(u["combined_studs_per_meter"] > 0)
        self.assertTrue(u["rel_pct"] >= 0)
        self.assertTrue(u["method"])


if __name__ == "__main__":
    unittest.main()

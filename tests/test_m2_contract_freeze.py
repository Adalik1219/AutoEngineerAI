"""Freeze-audit M2 vystupu proti reports/M2-M3-CONTRACTS-FREEZE-v1.md (Agent B).

Vlastnik souboru: tests/test_m2_contract_freeze.py (Agent B).
Pouzívá POUZE synteticka data + default_references() (M1). Zadny test
nevydava syntetiku za mereni Mustangu; VERIFIED se vyskytuje jen jako
ocekavany stav konzistentni synteticke kalibrace, nikdy jako tvrzeni
o realnem voze. Nemeni zadne produkcni soubory. Zmenu kontraktu
NENAVRHUJE (needs-coordinator-approval by byla vyzadovana).
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Inspection.scale_calibration import (
    CalibrationBlockedError,
    calibrate,
    default_references,
    require_verified_for_m3,
    usable_for_m3,
)
from src.Inspection.wheel_detect import (
    COORDINATE_FRAME_ACTUAL,
    INSPECTION_REPORT_SCHEMA,
    WHEEL_DESIGNATIONS,
    build_inspection_report,
    report_from_assess,
)

# Freeze §inspection_report.json — povinne klice (mnozina, nadstavba
# known_non_wheels je povolena a evidovana zvlast).
FREEZE_REPORT_KEYS = {"report_id", "vehicle_id", "source_file",
                      "source_sha256", "parser_version", "code_version",
                      "wheels", "axles", "wheelbase_studs",
                      "tire_diameters_studs", "coordinate_frame",
                      "method", "warnings", "overall_status"}
FREEZE_WHEEL_KEYS = {"designation", "instance_id", "class_name",
                     "center_studs", "size_studs", "shape", "status",
                     "reason"}
FREEZE_REPORT_STATUSES = {"GEOMETRY_OK", "UNKNOWN", "BLOCKED"}

# Freeze §scale_calibration.json.
FREEZE_CAL_KEYS = {"vehicle_id", "inspection_ref", "references",
                   "measurements_studs", "estimates", "deviations_pct",
                   "uncertainty", "overall_status", "blocked_reason"}
FREEZE_REF_KEYS = {"param", "value_si", "unit", "source", "status"}
FREEZE_CAL_STATUSES = {"VERIFIED", "ESTIMATED", "UNKNOWN", "BLOCKED"}


def _synth_wheels(status="GEOMETRY_OK", reason=None):
    center = {"x": 1.0, "y": 2.0, "z": 3.0}
    size = {"x": 2.7, "y": 2.7, "z": 2.7}
    return {des: {"instance_id": 10 + i, "class_name": "Part",
                  "center_studs": dict(center), "size_studs": dict(size),
                  "shape": "Ball", "status": status, "reason": reason}
            for i, des in enumerate(WHEEL_DESIGNATIONS)}


def _synth_report(**kw):
    kw.setdefault("vehicle_id", "synth-freeze-audit")
    kw.setdefault("source_file", "synthetic/no-rbxm")
    kw.setdefault("source_sha256", "00" * 32)
    kw.setdefault("wheels", _synth_wheels())
    kw.setdefault("parser_version", "synth")
    kw.setdefault("code_version", "test_m2_contract_freeze")
    return build_inspection_report(**kw)


def _synth_meas(scale=3.0):
    return {r["param"]: r["value_si"] * scale
            for r in default_references()}


class TestFreezeInspectionReport(unittest.TestCase):
    def test_top_level_keys_match_freeze(self):
        rep = _synth_report()
        self.assertEqual(set(rep.keys()),
                         FREEZE_REPORT_KEYS | {"known_non_wheels"})

    def test_in_code_schema_required_matches_freeze(self):
        self.assertEqual(set(INSPECTION_REPORT_SCHEMA["required"]),
                         FREEZE_REPORT_KEYS)

    def test_wheel_entries_are_list_with_freeze_keys(self):
        rep = _synth_report()
        self.assertIsInstance(rep["wheels"], list)
        self.assertEqual(len(rep["wheels"]), 4)
        for entry in rep["wheels"]:
            self.assertEqual(set(entry.keys()), FREEZE_WHEEL_KEYS)

    def test_status_enum_matches_freeze(self):
        rep = _synth_report()
        self.assertIn(rep["overall_status"], FREEZE_REPORT_STATUSES)
        schema_enum = set(INSPECTION_REPORT_SCHEMA["properties"]
                          ["overall_status"]["enum"])
        self.assertTrue(FREEZE_REPORT_STATUSES <= schema_enum)


class TestFreezeScaleCalibration(unittest.TestCase):
    def test_top_level_keys_match_freeze(self):
        res = calibrate(measurements_studs=_synth_meas())
        self.assertEqual(set(res.keys()), FREEZE_CAL_KEYS)

    def test_reference_entries_match_freeze(self):
        res = calibrate(measurements_studs=_synth_meas())
        for ref in res["references"]:
            self.assertEqual(set(ref.keys()), FREEZE_REF_KEYS)
            self.assertEqual(ref["unit"], "m")

    def test_status_enum_matches_freeze(self):
        for meas in (_synth_meas(),
                     {p: None for p in ("wheelbase", "track_f", "track_r",
                                        "tire_d_f", "tire_d_r")}):
            res = calibrate(measurements_studs=dict(meas))
            self.assertIn(res["overall_status"], FREEZE_CAL_STATUSES)


class TestProvenanceUnits(unittest.TestCase):
    def test_report_carries_full_provenance(self):
        rep = _synth_report()
        for key in ("source_file", "source_sha256", "parser_version",
                    "code_version", "method", "report_id"):
            self.assertTrue(rep[key], msg=key)

    def test_calibration_carries_provenance(self):
        res = calibrate(measurements_studs=_synth_meas(),
                        inspection_ref="sha256:" + "ab" * 32)
        self.assertEqual(res["inspection_ref"], "sha256:" + "ab" * 32)
        for ref in res["references"]:
            self.assertTrue(ref["source"], msg=ref["param"])
            self.assertIn(ref["status"], ("VERIFIED", "ESTIMATED",
                                          "UNKNOWN"))

    def test_units_separated_studs_vs_si(self):
        rep = _synth_report()
        self.assertIsInstance(rep["wheelbase_studs"], (int, float))
        res = calibrate(measurements_studs=_synth_meas())
        for ref in res["references"]:
            self.assertEqual(ref["unit"], "m")
            self.assertIsInstance(ref["value_si"], (int, float))
        for key in ("wheelbase", "track_f", "track_r",
                    "tire_d_f", "tire_d_r"):
            self.assertIsInstance(res["measurements_studs"][key],
                                  (int, float))

    def test_coordinate_frame_is_actual(self):
        rep = _synth_report()
        self.assertEqual(rep["coordinate_frame"], COORDINATE_FRAME_ACTUAL)
        self.assertTrue(rep["coordinate_frame"]["verified_in_studio"])


class TestNullUnknownAndBlocking(unittest.TestCase):
    def test_null_never_invented_numbers(self):
        wheels = _synth_wheels()
        wheels["FL"]["center_studs"] = None
        wheels["FL"]["status"] = "UNKNOWN"
        wheels["FL"]["reason"] = "missing_position"
        rep = _synth_report(wheels=wheels)
        self.assertEqual(rep["overall_status"], "UNKNOWN")
        self.assertIsNone(rep["axles"]["front"]["track_studs"])
        fl = [w for w in rep["wheels"] if w["designation"] == "FL"][0]
        self.assertIsNone(fl["center_studs"])

    def test_unknown_measurements_give_unknown_no_estimates(self):
        res = calibrate(measurements_studs={p: None for p in
                                            ("wheelbase", "track_f",
                                             "track_r", "tire_d_f",
                                             "tire_d_r")})
        self.assertEqual(res["overall_status"], "UNKNOWN")
        self.assertEqual(res["estimates"], [])
        self.assertIsNone(res["blocked_reason"])

    def test_blocked_calibration_carries_reason_no_estimates(self):
        meas = _synth_meas()
        meas["wheelbase"] = meas["wheelbase"] * 1.20
        res = calibrate(measurements_studs=meas)
        self.assertEqual(res["overall_status"], "BLOCKED")
        self.assertTrue(res["blocked_reason"])
        self.assertEqual(res["estimates"], [])


class TestBlockPropagationToM3(unittest.TestCase):
    def test_assess_blocked_propagates_to_report(self):
        assess = {"wheels": {},
                  "blocked": True, "status": "BLOCKED",
                  "unidentified": [],
                  "blocked_reasons": ["synth-freeze-audit-block"]}
        rep = report_from_assess("synth", "synthetic/no-rbxm",
                                 "00" * 32, assess, "synth", "test")
        self.assertEqual(rep["overall_status"], "BLOCKED")
        self.assertTrue(any("synth-freeze-audit-block" in w
                            for w in rep["warnings"]))

    def test_non_verified_never_passes_m3_gate(self):
        base = _synth_meas()
        bad = dict(base)
        bad["wheelbase"] = base["wheelbase"] * 1.2
        for res in (calibrate(measurements_studs=base),       # ESTIMATED
                    calibrate(measurements_studs={}),         # UNKNOWN
                    calibrate(measurements_studs=bad)):       # BLOCKED
            self.assertFalse(usable_for_m3(res))
            with self.assertRaises(CalibrationBlockedError):
                require_verified_for_m3(res)

    def test_no_m3_outputs_without_verified_scale(self):
        # Brana zavrena pro vse krome VERIFIED: geometry_target.json ani
        # geometry_diff.json nesmi vzniknout — zadny producent bez brany.
        base = _synth_meas()
        res = calibrate(measurements_studs=base)
        self.assertEqual(res["overall_status"], "ESTIMATED")
        self.assertFalse(usable_for_m3(res))
        for name in ("geometry_target.json", "geometry_diff.json"):
            self.assertFalse(
                os.path.isfile(os.path.join(ROOT, name)),
                msg=name + " nesmi existovat bez VERIFIED brany")


class TestDeterminismReproducibility(unittest.TestCase):
    def test_report_json_roundtrip_stable(self):
        rep = _synth_report()
        self.assertEqual(json.loads(json.dumps(rep, sort_keys=True)),
                         rep)
        self.assertEqual(_synth_report(), _synth_report())

    def test_calibration_determinism_key_order_independent(self):
        kw = {"measurements_studs": _synth_meas(),
              "inspection_ref": "sha256:cc"}
        first = calibrate(**kw)
        again = calibrate(**dict(reversed(list(kw.items()))))
        self.assertEqual(first, again)


if __name__ == "__main__":
    unittest.main()

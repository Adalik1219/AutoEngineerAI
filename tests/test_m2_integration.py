"""Integracni testy M2 (Agent C): retezec RBXM -> parser -> detect ->
assess -> report -> kalibrace na realne kopii + brany G-01-G-07, G-10.

Vlastneny soubor: tests/test_m2_integration.py (Agent C).
Moduly A/B (rbxm_parser, wheel_detect, scale_calibration) se NEMENI —
pouze se ctou; nalezena chyba se zaznamena a preda vlastnikovi.

Vstup: verzovana fixture testgame/.../JeepTemplate.rbxm, fallback
assets/chassis-original/chasis-work-copy.rbxm (POUZE CTENI, nikdy zapis).
Ocekavany hash obou praconich kopii: dc8747e0...fefdf (230421 B) —
jediny distinctni model v repu (LIMIT, oba soubory se testuji zvlast).
Chybi-li oba soubory, testy cteni hlasi SKIP (PENDING), nikdy ERROR.
Vsechny behy jsou seriove (unittest default, zadna paralelizace).
"""
import hashlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Inspection.rbxm_parser import (
    assess_wheel_geometry,
    parse_rbxm,
)
from src.Inspection.scale_calibration import (
    CalibrationBlockedError,
    calibrate,
    require_verified_for_m3,
    usable_for_m3,
)
from src.Inspection.wheel_detect import (
    CHASSIS_PART_ALLOWLIST,
    WHEEL_DESIGNATIONS,
    build_inspection_report,
    detect_wheels,
    is_blocked,
    report_from_assess,
)

JEEP_COPY = os.path.join(ROOT, "testgame", "src", "ServerStorage",
                         "VehicleTemplates", "JeepTemplate.rbxm")
WORK_COPY = os.path.join(ROOT, "assets", "chassis-original",
                         "chasis-work-copy.rbxm")
EXPECTED_SHA256 = ("dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd"
                   "7c070c2c1fefdf")
EXPECTED_SIZE = 230421

# Freeze: povinne klice inspection_report.json (M2-M3-CONTRACTS-FREEZE-v1).
REPORT_KEYS = {"report_id", "vehicle_id", "source_file", "source_sha256",
               "parser_version", "code_version", "wheels", "axles",
               "wheelbase_studs", "tire_diameters_studs", "coordinate_frame",
               "method", "warnings", "overall_status"}
# "known_non_wheels" je dokumentovana nadstavba modulu (4-tier), ne
# povinny klic kontraktu.
WHEEL_ENTRY_KEYS = {"designation", "instance_id", "class_name",
                    "center_studs", "size_studs", "shape", "status", "reason"}

# Studio ground-truth (reports/STUDIO_GROUND_TRUTH.md §3): rozchod ≈ 5.99,
# rozvor ≈ 10.52 (studs).
TRACK_EXPECTED = 5.99
WHEELBASE_EXPECTED = 10.52


def _sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _existing_copies():
    """Realne kopie, ktere existuji (ocekavane obe, stejny hash)."""
    return [p for p in (JEEP_COPY, WORK_COPY) if os.path.isfile(p)]


def _require_real_copy(test):
    copies = _existing_copies()
    if not copies:
        test.skipTest("chybi obe pracovni kopie RBXM (PENDING, neni PASS)")
    return copies[0]


def _full_chain(path, vehicle_id="JeepTemplate"):
    """Cely retezec: parse -> detect -> assess -> report -> kalibrace."""
    before = _sha256(path)
    model = parse_rbxm(path)
    insts = model["instances"]
    det = detect_wheels(insts)
    geo = assess_wheel_geometry(
        insts, known_non_wheels=det["known_non_wheels"])
    rep = report_from_assess(vehicle_id, os.path.relpath(path, ROOT),
                             before, geo, "rbxm_parser M2/C05",
                             "test_m2_integration")
    meas = {"wheelbase": rep["wheelbase_studs"],
            "track_f": rep["axles"]["front"]["track_studs"],
            "track_r": rep["axles"]["rear"]["track_studs"],
            "tire_d_f": rep["tire_diameters_studs"]["FL"],
            "tire_d_r": rep["tire_diameters_studs"]["RL"]}
    cal = calibrate(measurements_studs=meas)
    after = _sha256(path)
    return {"sha_before": before, "sha_after": after, "model": model,
            "detect": det, "assess": geo, "report": rep,
            "measurements": meas, "calibration": cal}


class TestHashBeforeAfter(unittest.TestCase):
    """G-01: originalni RBXM nezmenen (SHA pred/po shodny)."""

    def test_both_copies_hash_and_size(self):
        copies = _existing_copies()
        if not copies:
            self.skipTest("chybi obe pracovni kopie RBXM (PENDING)")
        for path in copies:
            with self.subTest(copy=os.path.relpath(path, ROOT)):
                self.assertEqual(os.path.getsize(path), EXPECTED_SIZE)
                self.assertEqual(_sha256(path), EXPECTED_SHA256)

    def test_limit_single_distinct_model(self):
        """LIMIT: oba soubory maji stejny hash = jediny distinctni model."""
        copies = _existing_copies()
        if len(copies) < 2:
            self.skipTest("druha kopie chybi (PENDING)")
        self.assertEqual(_sha256(copies[0]), _sha256(copies[1]))

    def test_chain_does_not_modify_input(self):
        path = _require_real_copy(self)
        chain = _full_chain(path)
        self.assertEqual(chain["sha_before"], EXPECTED_SHA256)
        self.assertEqual(chain["sha_after"], chain["sha_before"])


class TestParserStage(unittest.TestCase):
    """Parser na realne kopii: 815 instanci, 37 typu, koren, Wheels, 4 Ball."""

    def test_census_root_wheels(self):
        model = parse_rbxm(_require_real_copy(self))
        self.assertEqual(model["num_types"], 37)
        self.assertEqual(model["num_instances"], 815)
        self.assertEqual(len(model["instances"]), 815)
        roots = [i for i in model["instances"]
                 if i["parent_id"] is None]
        self.assertEqual([i["id"] for i in roots], [0])
        wheels = [i for i in model["instances"]
                  if i["class_name"] == "Model" and i["name"] == "Wheels"]
        self.assertEqual(len(wheels), 1)

    def test_four_balls_msb_first(self):
        """N1: 4x Ball (kola id 3/52/101/150), 0 neprectenych shape-enumu."""
        model = parse_rbxm(_require_real_copy(self))
        by_id = {i["id"]: i for i in model["instances"]}
        for iid in (3, 52, 101, 150):
            self.assertEqual(by_id[iid]["shape"], "Ball")
            self.assertEqual(by_id[iid]["class_name"], "Part")
        unread = [i["id"] for i in model["instances"]
                  if i["props"].get("shape", {}).get("status") == "unread"
                  and i["props"]["shape"].get("reason", "").startswith(
                      "neznama hodnota enum")]
        self.assertEqual(unread, [])


class TestDetectStage(unittest.TestCase):
    """Detect: 4 kola (4 rundy), 44 known, determinismus."""

    def test_four_wheels_44_known(self):
        model = parse_rbxm(_require_real_copy(self))
        res = detect_wheels(model["instances"])
        self.assertFalse(is_blocked(res))
        self.assertEqual(res["status"], "OK")
        self.assertEqual(
            {d: res["wheels"][d]["instance_id"]
             for d in WHEEL_DESIGNATIONS},
            {"FL": 3, "FR": 52, "RL": 101, "RR": 150})
        for des in WHEEL_DESIGNATIONS:
            self.assertEqual(res["wheels"][des]["status"], "WHEEL")
            self.assertEqual(res["wheels"][des]["tier"], "VALID_WHEEL")
            self.assertEqual(res["wheels"][des]["failed_checks"], [])
        # 44 dilu podvozku: 11 jmen allowlistu x 4 instance, vse Part.
        self.assertEqual(len(res["known_non_wheels"]), 44)
        for entry in res["known_non_wheels"]:
            self.assertEqual(entry["tier"], "KNOWN_NON_WHEEL")
            self.assertIn(entry["name"], CHASSIS_PART_ALLOWLIST)
        self.assertEqual(len(CHASSIS_PART_ALLOWLIST), 11)
        self.assertEqual(res["unidentified"], [])
        self.assertEqual(res["blocked_reasons"], [])

    def test_determinism(self):
        model = parse_rbxm(_require_real_copy(self))
        self.assertEqual(detect_wheels(model["instances"]),
                         detect_wheels(model["instances"]))


class TestAssessStage(unittest.TestCase):
    """Assess: 4x GEOMETRY_OK, 44 known, celek BLOCKED (kalibrace)."""

    def test_assess_blocked_float_unverified(self):
        model = parse_rbxm(_require_real_copy(self))
        det = detect_wheels(model["instances"])
        geo = assess_wheel_geometry(
            model["instances"],
            known_non_wheels=det["known_non_wheels"])
        for des in WHEEL_DESIGNATIONS:
            self.assertEqual(geo["wheels"][des]["status"], "GEOMETRY_OK")
        self.assertEqual(geo["unidentified"], [])
        self.assertEqual(len(geo["known_non_wheels"]), 44)
        self.assertTrue(geo["blocked"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertEqual(len(geo["blocked_reasons"]), 1)
        self.assertIn("float_decode_unverified",
                      geo["blocked_reasons"][0])
        self.assertIsNone(
            geo["calibration"].get("studs_per_meter"))

    def test_assess_without_passthrough_same(self):
        """Predani detect-vystupu nemeni vysledek (44 evidovano)."""
        model = parse_rbxm(_require_real_copy(self))
        det = detect_wheels(model["instances"])
        plain = assess_wheel_geometry(model["instances"])
        fed = assess_wheel_geometry(
            model["instances"],
            known_non_wheels=det["known_non_wheels"])
        self.assertEqual(len(plain["known_non_wheels"]), 44)
        self.assertEqual(len(fed["known_non_wheels"]), 44)
        self.assertEqual(plain["unidentified"], [])
        self.assertEqual(fed["unidentified"], [])


class TestReportStage(unittest.TestCase):
    """Report: klice freeze, hodnoty, null != vymyslene, BLOCKED propagace."""

    def test_report_keys_match_freeze(self):
        chain = _full_chain(_require_real_copy(self))
        rep = chain["report"]
        self.assertEqual(set(rep.keys()), REPORT_KEYS | {"known_non_wheels"})
        for entry in rep["wheels"]:
            self.assertEqual(set(entry.keys()), WHEEL_ENTRY_KEYS)
        self.assertEqual(
            sorted(rep["axles"].keys()), ["front", "rear"])
        self.assertEqual(
            sorted(rep["tire_diameters_studs"].keys()),
            ["FL", "FR", "RL", "RR"])
        self.assertIn("verified_in_studio",
                      rep["coordinate_frame"])
        self.assertTrue(rep["coordinate_frame"]["verified_in_studio"])

    def test_report_values_track_wheelbase(self):
        chain = _full_chain(_require_real_copy(self))
        rep = chain["report"]
        self.assertAlmostEqual(
            rep["axles"]["front"]["track_studs"], TRACK_EXPECTED, places=2)
        self.assertAlmostEqual(
            rep["axles"]["rear"]["track_studs"], TRACK_EXPECTED, places=2)
        self.assertAlmostEqual(
            rep["wheelbase_studs"], WHEELBASE_EXPECTED, places=2)
        for des in WHEEL_DESIGNATIONS:
            self.assertAlmostEqual(
                rep["tire_diameters_studs"][des], 2.7, places=4)

    def test_null_not_invented(self):
        """G-04: chybejici kolo -> instance_id/center/size None + reason,
        zadna cisla; UNKNOWN bez reason se nedovoli."""
        rep = build_inspection_report(
            "X", "f.rbxm", "00" * 32, {}, "p", "c")
        self.assertEqual(rep["overall_status"], "BLOCKED")
        for entry in rep["wheels"]:
            self.assertIsNone(entry["instance_id"])
            self.assertIsNone(entry["center_studs"])
            self.assertIsNone(entry["size_studs"])
            self.assertEqual(entry["status"], "UNKNOWN")
            self.assertEqual(entry["reason"], "missing_wheel")
        self.assertIsNone(rep["wheelbase_studs"])

    def test_assess_blocked_propagates_to_report(self):
        """BLOCKED propagace assess -> report (freeze M3: BLOCKED vstup ->
        BLOCKED vystup). Assess na realnych datech je BLOCKED
        (float_decode_unverified); report nesmi byt GEOMETRY_OK.

        I-1 OPRAVENO (vlastnik wheel_detect.py, Agent B):
        report_from_assess preda kazdy assess blocked_reason do
        build_inspection_report (assess_blocked_reasons) -> report BLOCKED,
        per-kolo GEOMETRY_OK detaily zustavaji v tele reportu.
        """
        chain = _full_chain(_require_real_copy(self))
        self.assertTrue(chain["assess"]["blocked"])
        self.assertEqual(chain["report"]["overall_status"], "BLOCKED",
                         "DIVERGENCE: assess BLOCKED "
                         "(%r) ale report %s; vlastnik: Agent B "
                         "(report_from_assess v wheel_detect.py)" % (
                             chain["assess"]["blocked_reasons"],
                             chain["report"]["overall_status"]))


class TestCalibrationStage(unittest.TestCase):
    """Kalibrace z reportovych mereni: BLOCKED 7.44 %, brana M3 zavrena."""

    def test_real_measurements_blocked(self):
        chain = _full_chain(_require_real_copy(self))
        cal = chain["calibration"]
        self.assertEqual(
            sorted(cal.keys()),
            ["blocked_reason", "deviations_pct", "estimates",
             "inspection_ref", "measurements_studs", "overall_status",
             "references", "uncertainty", "vehicle_id"])
        self.assertEqual(cal["overall_status"], "BLOCKED")
        self.assertTrue(cal["blocked_reason"])
        self.assertIn("7.44", cal["blocked_reason"])
        # G-04: pri BLOCKED zadna vymyslena cisla (prazdne odhady, null).
        self.assertEqual(cal["estimates"], [])
        self.assertIsNone(
            cal["uncertainty"]["combined_studs_per_meter"])
        # G-02: reference vzdy value_si + unit==m.
        for ref in cal["references"]:
            self.assertEqual(
                sorted(ref.keys()),
                ["param", "source", "status", "unit", "value_si"])
            self.assertEqual(ref["unit"], "m")

    def test_unknown_measurements_not_invented(self):
        """G-04: vse None -> UNKNOWN, estimates [], zadna cisla."""
        cal = calibrate(measurements_studs={
            "wheelbase": None, "track_f": None, "track_r": None,
            "tire_d_f": None, "tire_d_r": None})
        self.assertEqual(cal["overall_status"], "UNKNOWN")
        self.assertIsNone(cal["blocked_reason"])
        self.assertEqual(cal["estimates"], [])

    def test_m3_gate_closed_on_real_data(self):
        """Brana M3: kalibrace realnych dat = BLOCKED -> M3 neotevirat."""
        chain = _full_chain(_require_real_copy(self))
        self.assertFalse(usable_for_m3(chain["calibration"]))
        with self.assertRaises(CalibrationBlockedError):
            require_verified_for_m3(chain["calibration"])

    def test_calibration_determinism(self):
        chain = _full_chain(_require_real_copy(self))
        again = calibrate(
            measurements_studs=dict(chain["measurements"]))
        self.assertEqual(again, chain["calibration"])


class TestFullChainDeterminism(unittest.TestCase):
    """G-10: stejny vstup + stejna verze = stejny vystup (cely retezec)."""

    def test_chain_twice_identical(self):
        path = _require_real_copy(self)
        first = _full_chain(path)
        second = _full_chain(path)
        for key in ("detect", "assess", "report", "calibration"):
            self.assertEqual(first[key], second[key],
                             "nondeterminismus v kroku %s" % key)
        self.assertEqual(
            json.dumps(first["report"], sort_keys=True),
            json.dumps(second["report"], sort_keys=True))


class TestGatesNoRuntimeClaims(unittest.TestCase):
    """G-06/G-07: zadny runtime verdikt bez Studia (jen code-verified)."""

    def test_report_carries_no_runtime_proof(self):
        chain = _full_chain(_require_real_copy(self))
        blob = json.dumps(chain["report"])
        for token in ("run_id", "studio_play", "RUNTIME-VERIFIED",
                      "roblox-runtime"):
            self.assertNotIn(token, blob)

    def test_missing_file_never_silent(self):
        """Chybejici soubor -> RbxmCorruptError kontrakt, nikdy tichy PASS
        ani BROKEN vystup (G-04: zadna vymyslena data)."""
        from src.Inspection.rbxm_parser import RbxmCorruptError
        with self.assertRaises(RbxmCorruptError):
            parse_rbxm(os.path.join(ROOT, "neexistuje-xyz.rbxm"))


if __name__ == "__main__":
    unittest.main()

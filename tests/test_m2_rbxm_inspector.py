"""Dukazni testy Agenta A (RBXM Inspector): podpora formatu, read-only,
determinismus, odmitnuti vstupu. POUZE ROZSIRENI - nemeni existujici testy.
Vstup: realna kopie (cteni), chybi-li, SKIP (PENDING), nikdy ERROR.
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
    RbxmCorruptError,
    RbxmError,
    RbxmUnsupportedError,
    assess_wheel_geometry,
    parse_bytes,
    parse_rbxm,
)

WORK_COPY = os.path.join(ROOT, "assets", "chassis-original",
                         "chasis-work-copy.rbxm")
JEEP_COPY = os.path.join(ROOT, "testgame", "src", "ServerStorage",
                         "VehicleTemplates", "JeepTemplate.rbxm")
EXPECTED_SHA256 = ("dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd"
                   "7c070c2c1fefdf")


def _require_real_copy(testcase):
    for path in (JEEP_COPY, WORK_COPY):
        if os.path.exists(path):
            return path
    testcase.skipTest("PENDING: realny RBXM model neni k dispozici")
    raise AssertionError("nedosazitelne")


def _sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class TestRbxmInspectorEvidence(unittest.TestCase):
    """Dukazy pro RBXM-INSPECTOR-REPORT (Agent A)."""

    def test_readonly_hash_before_after(self):
        path = _require_real_copy(self)
        before = _sha256(path)
        parse_rbxm(path)
        assess_wheel_geometry(parse_rbxm(path)["instances"])
        self.assertEqual(_sha256(path), before)
        self.assertEqual(before, EXPECTED_SHA256)

    def test_supported_census_and_meta(self):
        model = parse_rbxm(_require_real_copy(self))
        self.assertEqual(model["num_types"], 37)
        self.assertEqual(model["num_instances"], 815)
        self.assertEqual(model["chunk_census"]["PROP"], 928)
        self.assertEqual(model["meta"], {"ExplicitAutoJoints": "true"})
        self.assertEqual(model["sstr"]["shared_strings"], 0)
        self.assertEqual(model["missing_name_count"], 0)

    def test_deterministic_parse(self):
        path = _require_real_copy(self)
        first = json.dumps(parse_rbxm(path), sort_keys=True, default=str)
        second = json.dumps(parse_rbxm(path), sort_keys=True, default=str)
        self.assertEqual(first, second)

    def test_shape_ball_read_block_unread_lane_evidence(self):
        """N1: kola Ball read/trusted; 105x Part shape unread (0x01000000)."""
        model = parse_rbxm(_require_real_copy(self))
        parts = [i for i in model["instances"]
                 if i["class_name"] == "Part"]
        self.assertEqual(len(parts), 109)
        balls = [i for i in parts if i.get("shape") == "Ball"]
        self.assertEqual(len(balls), 4)
        for wheel in balls:
            self.assertTrue(wheel["props"]["shape"]["trusted"])
        unread = [i for i in parts if i.get("shape") is None]
        self.assertEqual(len(unread), 105)
        self.assertIn("16777216",
                      unread[0]["props"]["shape"]["reason"])

    def test_unsupported_and_corrupt_inputs(self):
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(b"")
        with self.assertRaises(RbxmError):
            parse_bytes(open(_require_real_copy(self), "rb").read()[:1000])
        with self.assertRaises(RbxmCorruptError):
            parse_rbxm(os.path.join(ROOT, "tento-soubor-neexistuje.rbxm"))

    def test_assess_blocked_with_geometry_ok_wheels(self):
        model = parse_rbxm(_require_real_copy(self))
        result = assess_wheel_geometry(model["instances"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["blocked"])
        for designation in ("FL", "FR", "RL", "RR"):
            self.assertEqual(result["wheels"][designation]["status"],
                             "GEOMETRY_OK")
        self.assertEqual(
            result["calibration"]["status"], "NOT_IMPLEMENTED")

    def test_skipped_props_are_explicit_not_silent(self):
        model = parse_rbxm(_require_real_copy(self))
        self.assertGreaterEqual(len(model["skipped_props"]), 800)
        for entry in model["skipped_props"]:
            self.assertEqual(entry["status"], "unread")


if __name__ == "__main__":
    unittest.main()

"""Unit testy rozhodovaciho pravidla kol (M2.2) na syntetickych fixturech.

Zadny skutecny RBXM parser se netestuje jako hotovy — fixture jsou rucne
stavene seznamy instanci {id, name, class_name, shape, parent_id}.
Pravidlo: (a) v Model:Wheels + (b) FL/FR/RL/RR + (c) tvar Ball, jinak
UNKNOWN se zaznamem; BLOCKED podminky viz src/Inspection/wheel_detect.py.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Inspection.wheel_detect import (
    INSPECTION_REPORT_SCHEMA,
    classify_candidate,
    detect_wheels,
    is_blocked,
)


def _part(iid, name, shape="Ball", parent_id=2):
    return {"id": iid, "name": name, "class_name": "Part",
            "shape": shape, "parent_id": parent_id}


def _ok_model():
    # Minimalni zdrava hierarchie: koren 0:Model <- 2:Model:Wheels <- 4 kola.
    insts = [
        {"id": 0, "name": "", "class_name": "Model",
         "shape": None, "parent_id": None},
        {"id": 2, "name": "Wheels", "class_name": "Model",
         "shape": None, "parent_id": 0},
        _part(3, "FL"), _part(52, "FR"), _part(101, "RL"), _part(150, "RR"),
        # Prislusenstvi kol: constrainty/modely uvnitr Wheels nejsou kola
        # ani UNKNOWN — nesmi blokovat.
        {"id": 200, "name": "Spring", "class_name": "SpringConstraint",
         "shape": None, "parent_id": 3},
        {"id": 201, "name": "SuspensionGeometry", "class_name": "Model",
         "shape": None, "parent_id": 3},
    ]
    return insts


class TestWheelDecisionRule(unittest.TestCase):
    def test_all_four_wheels_detected(self):
        res = detect_wheels(_ok_model())
        self.assertFalse(is_blocked(res))
        self.assertEqual(res["status"], "OK")
        for des, iid in (("FL", 3), ("FR", 52), ("RL", 101), ("RR", 150)):
            self.assertEqual(res["wheels"][des]["status"], "WHEEL")
            self.assertEqual(res["wheels"][des]["instance_id"], iid)
            self.assertEqual(res["wheels"][des]["failed_checks"], [])

    def test_determinism(self):
        self.assertEqual(detect_wheels(_ok_model()),
                         detect_wheels(_ok_model()))

    def test_ball_outside_wheels_never_wheel(self):
        insts = _ok_model() + [_part(999, "FR", parent_id=0)]
        # Ochrana pred zamenou: Ball mimo Wheels se kolem nikdy nestane.
        status, failed = classify_candidate(insts[-1], False)
        self.assertEqual(status, "UNKNOWN")
        self.assertIn("not_in_wheels", failed)
        # A neotravi vysledek (duplicita FR mimo Wheels neblokuje).
        res = detect_wheels(insts)
        self.assertFalse(is_blocked(res))
        self.assertEqual(res["wheels"]["FR"]["instance_id"], 52)

    def test_wrong_name_is_unknown_with_record(self):
        insts = _ok_model()
        insts[2] = _part(3, "FrontLeft")  # (b) poruseno
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["wheels"]["FL"]["status"], "UNKNOWN")
        recs = [u for u in res["unidentified"]
                if u["instance_id"] == 3]
        self.assertEqual(len(recs), 1)
        self.assertIn("bad_designation", recs[0]["failed_checks"])

    def test_wrong_shape_is_unknown_with_record(self):
        insts = _ok_model()
        insts[3] = _part(52, "FR", shape="Block")  # (c) poruseno
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        recs = [u for u in res["unidentified"]
                if u["instance_id"] == 52]
        self.assertEqual(len(recs), 1)
        self.assertIn("bad_shape", recs[0]["failed_checks"])

    def test_missing_wheels_model_blocked(self):
        insts = [i for i in _ok_model() if i["id"] != 2]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertTrue(any("missing Model:Wheels" in r
                            for r in res["blocked_reasons"]))

    def test_three_wheels_blocked(self):
        insts = [i for i in _ok_model() if i["id"] != 150]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["wheels"]["RR"]["status"], "UNKNOWN")
        self.assertTrue(any("!= 4" in r for r in res["blocked_reasons"]))

    def test_duplicate_designation_blocked(self):
        insts = _ok_model() + [_part(151, "RR", parent_id=2)]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["wheels"]["RR"]["status"], "UNKNOWN")
        self.assertIn("duplicate_designation",
                      res["wheels"]["RR"]["failed_checks"])

    def test_any_unknown_blocks_analysis(self):
        insts = _ok_model() + [_part(160, "Spare", parent_id=2)]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertTrue(any("UNKNOWN" in r for r in res["blocked_reasons"]))

    def test_classify_conjunction_all_three_required(self):
        # Kazda z 8 kombinaci: jen (True,True,True) je WHEEL.
        for in_w in (False, True):
            for name_ok in (False, True):
                for shape_ok in (False, True):
                    inst = {"id": 1,
                            "name": "FL" if name_ok else "X",
                            "class_name": "Part",
                            "shape": "Ball" if shape_ok else "Block",
                            "parent_id": 2}
                    status, failed = classify_candidate(inst, in_w)
                    if in_w and name_ok and shape_ok:
                        self.assertEqual(status, "WHEEL")
                        self.assertEqual(failed, [])
                    else:
                        self.assertEqual(status, "UNKNOWN")
                        self.assertTrue(failed)


class TestInspectionReportSchema(unittest.TestCase):
    def test_schema_has_required_top_level_keys(self):
        for key in ("vehicle_id", "rbxm_sha256", "status", "wheels",
                    "scale", "blocked_reasons"):
            self.assertIn(key, INSPECTION_REPORT_SCHEMA["required"])
        wheels = INSPECTION_REPORT_SCHEMA["properties"]["wheels"]
        self.assertIn("^(FL|FR|RL|RR)$", wheels["patternProperties"])
        scale = INSPECTION_REPORT_SCHEMA["properties"]["scale"]
        self.assertEqual(scale["properties"]["unit"]["const"], "studs/m")


    def test_duplicate_wheels_model_blocked(self):
        # Dva Model:Wheels = nejednoznacny vstup -> BLOCKED (dosud netestovano).
        insts = _ok_model() + [{"id": 9, "name": "Wheels",
                               "class_name": "Model", "shape": None,
                               "parent_id": 0}]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertTrue(any("ambiguous Model:Wheels" in r
                            for r in res["blocked_reasons"]))

    def test_cycle_in_parents_is_blocked(self):
        # P0: cyklus v parent_id je poskozena hierarchie — nikdy nesmi
        # projit jako validni. Vyzaduje BLOCKED s duvodem parent_cycle.
        insts = _ok_model() + [_part(160, "Spare", parent_id=160)]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("parent_cycle" in r
                            for r in res["blocked_reasons"]))

    def test_missing_parent_id_blocked(self):
        # Odkaz na neexistujici parent ID = poskozena hierarchie.
        insts = _ok_model()
        insts[2] = _part(3, "FL", parent_id=9999)
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("missing parent id" in r
                            for r in res["blocked_reasons"]))
        recs = [u for u in res["unidentified"]
                if u["instance_id"] == 3]
        self.assertEqual(len(recs), 1)
        self.assertIn("missing_parent", recs[0]["failed_checks"])

    def test_duplicate_instance_id_blocked(self):
        # Duplicitni instance ID = poskozeny vstup, nelze klasifikovat.
        insts = _ok_model() + [_part(3, "FL", parent_id=2)]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("duplicate instance id" in r
                            for r in res["blocked_reasons"]))

    def test_cycle_through_wheels_model_blocked(self):
        # Cyklus zasahujici primo Model:Wheels (Wheels -> FL -> Wheels).
        insts = _ok_model()
        for inst in insts:
            if inst["id"] == 2:
                inst["parent_id"] = 3
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("parent_cycle" in r
                            for r in res["blocked_reasons"]))

    def test_cycle_elsewhere_affecting_wheels_blocked(self):
        # Cyklus v jine casti hierarchie, kudy prochazi retez kola:
        # mezimodel 300 pod Wheels, kolo FL pod nim, cyklus 300 -> 3 -> 300.
        insts = _ok_model()
        insts.append({"id": 300, "name": "Suspension",
                      "class_name": "Model", "shape": None, "parent_id": 3})
        for inst in insts:
            if inst["id"] == 3:
                inst["parent_id"] = 300
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("parent_cycle" in r
                            for r in res["blocked_reasons"]))

    def test_long_cycle_through_wheel_blocked(self):
        # Dlouhy cyklus 3 -> 301 -> 302 -> 303 -> 3 pres kolo FL.
        insts = _ok_model()
        insts += [
            {"id": 301, "name": "M1", "class_name": "Model",
             "shape": None, "parent_id": 302},
            {"id": 302, "name": "M2", "class_name": "Model",
             "shape": None, "parent_id": 303},
            {"id": 303, "name": "M3", "class_name": "Model",
             "shape": None, "parent_id": 3},
        ]
        for inst in insts:
            if inst["id"] == 3:
                inst["parent_id"] = 301
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("parent_cycle" in r
                            for r in res["blocked_reasons"]))

    def test_offchain_model_cycle_does_not_block(self):
        # Cyklus 600 <-> 601 mezi Modely mimo retez kol nesmi
        # blokovat jinak validni detekci (specificita, zadny falesny BLOCKED).
        insts = _ok_model()
        insts += [
            {"id": 600, "name": "M1", "class_name": "Model",
             "shape": None, "parent_id": 601},
            {"id": 601, "name": "M2", "class_name": "Model",
             "shape": None, "parent_id": 600},
        ]
        res = detect_wheels(insts)
        self.assertFalse(is_blocked(res))
        self.assertEqual(res["status"], "OK")
        for des in ("FL", "FR", "RL", "RR"):
            self.assertEqual(res["wheels"][des]["status"], "WHEEL")


if __name__ == "__main__":
    unittest.main()

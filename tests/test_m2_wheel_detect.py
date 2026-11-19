"""Unit testy rozhodovaciho pravidla kol (M2.2) na syntetickych fixturech.

Zadny skutecny RBXM parser se netestuje jako hotovy — fixture jsou rucne
stavene seznamy instanci {id, name, class_name, shape, parent_id}.
Pravidlo: (a) v Model:Wheels + (b) FL/FR/RL/RR + (c) tvar Ball, jinak
UNKNOWN se zaznamem; BLOCKED podminky viz src/Inspection/wheel_detect.py.
"""
import os
import sys
import json
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Inspection.wheel_detect import (
    COORDINATE_FRAME_ACTUAL,
    INSPECTION_REPORT_SCHEMA,
    WHEEL_DESIGNATIONS,
    build_inspection_report,
    classify_candidate,
    detect_wheels,
    is_blocked,
    report_from_assess,
)

# Empiricka cisla: Studio ground-truth (reports/STUDIO_GROUND_TRUTH.md §3)
# + parser na chasis-work-copy.rbxm (sha256 dc8747e0...fefdf).
STUDIO_CENTERS = {
    "FL": (-45.187889099121094, 23.622142791748047, -203.2503662109375),
    "FR": (-51.178550720214844, 23.622142791748047, -203.25039672851562),
    "RL": (-45.18785858154297, 23.622142791748047, -213.77316284179688),
    "RR": (-51.17858123779297, 23.622142791748047, -213.77316284179688),
}
STUDIO_SIZE = (2.700000047683716, 2.700000047683716, 2.700000047683716)
STUDIO_IDS = {"FL": 3, "FR": 52, "RL": 101, "RR": 150}


def _ok_wheels(center_override=None, size_override=None, status_override=None,
               reason_override=None):
    wheels = {}
    for des in WHEEL_DESIGNATIONS:
        center = (center_override or {}).get(des, STUDIO_CENTERS[des])
        size = (size_override or {}).get(des, STUDIO_SIZE)
        wheels[des] = {
            "instance_id": STUDIO_IDS[des],
            "class_name": "Part",
            "center_studs": {"x": center[0], "y": center[1], "z": center[2]},
            "size_studs": {"x": size[0], "y": size[1], "z": size[2]},
            "shape": "Ball",
            "status": (status_override or {}).get(des, "GEOMETRY_OK"),
            "reason": (reason_override or {}).get(des),
        }
    return wheels


def _ok_report(**kwargs):
    kwargs.setdefault("vehicle_id", "JeepTemplate")
    kwargs.setdefault("source_file",
                      "assets/chassis-original/chasis-work-copy.rbxm")
    kwargs.setdefault("source_sha256",
                      "dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf")
    kwargs.setdefault("wheels", _ok_wheels())
    kwargs.setdefault("parser_version", "rbxm_parser M2/C05")
    kwargs.setdefault("code_version", "test")
    return build_inspection_report(**kwargs)


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
    def test_schema_has_contract_top_level_keys(self):
        # ZAVAZNY kontrakt M2-M3-CONTRACTS-FREEZE-v1 §inspection_report.json.
        for key in ("report_id", "vehicle_id", "source_file",
                    "source_sha256", "parser_version", "code_version",
                    "wheels", "axles", "wheelbase_studs",
                    "tire_diameters_studs", "coordinate_frame",
                    "method", "warnings", "overall_status"):
            self.assertIn(key, INSPECTION_REPORT_SCHEMA["required"])
        frame = INSPECTION_REPORT_SCHEMA["properties"]["coordinate_frame"]
        for key in ("x", "y", "z", "verified_in_studio"):
            self.assertIn(key, frame["required"])
        self.assertIn("GEOMETRY_OK", INSPECTION_REPORT_SCHEMA["properties"]
                      ["overall_status"]["enum"])
        self.assertIn("BLOCKED", INSPECTION_REPORT_SCHEMA["properties"]
                      ["overall_status"]["enum"])


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

    def test_forest_two_roots_blocked(self):
        # Les o 2 korenech: explicitni politika BLOCKED (format-audit
        # §3/F2) — zadny tichy pruchod, ani pri zdravych kolech.
        insts = _ok_model() + [{"id": 900, "name": "Other",
                               "class_name": "Model", "shape": None,
                               "parent_id": None}]
        res = detect_wheels(insts)
        self.assertTrue(is_blocked(res))
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("forest" in r
                            for r in res["blocked_reasons"]))

    def test_self_loop_on_wheel_blocked(self):
        # Explicitni self-loop na kole (FL -> FL): cyklus delky 1,
        # vzdy BLOCKED s duvodem parent_cycle.
        insts = _ok_model()
        for inst in insts:
            if inst["id"] == 3:
                inst["parent_id"] = 3
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


class TestBuildInspectionReport(unittest.TestCase):
    def test_four_wheels_geometry_ok_with_studio_numbers(self):
        rep = _ok_report()
        self.assertEqual(rep["overall_status"], "GEOMETRY_OK")
        self.assertEqual([w["designation"] for w in rep["wheels"]],
                         ["FL", "FR", "RL", "RR"])
        self.assertAlmostEqual(rep["axles"]["front"]["track_studs"],
                               5.99066162109375, places=9)
        self.assertAlmostEqual(rep["axles"]["rear"]["track_studs"],
                               5.99072265625, places=9)
        self.assertAlmostEqual(rep["wheelbase_studs"], 10.522781372070312,
                               places=9)
        for des in WHEEL_DESIGNATIONS:
            self.assertAlmostEqual(rep["tire_diameters_studs"][des],
                                   2.700000047683716, places=9)
        for w in rep["wheels"]:
            self.assertEqual(w["status"], "GEOMETRY_OK")
            self.assertIsNone(w["reason"])

    def test_coordinate_frame_is_actual_not_command_convention(self):
        # ROZPOR: prikazova konvence X=vpred/Y=vlevo/Z=vzhuru na datech
        # neplati — rozchod se meri na X, rozvor na Z, Y je konstantni.
        rep = _ok_report()
        frame = rep["coordinate_frame"]
        self.assertTrue(frame["verified_in_studio"])
        self.assertIn("lateral", frame["x"])
        self.assertIn("up", frame["y"])
        self.assertIn("longitudinal", frame["z"])
        self.assertEqual(frame, COORDINATE_FRAME_ACTUAL)
        xs = [STUDIO_CENTERS[d][0] for d in WHEEL_DESIGNATIONS]
        ys = [STUDIO_CENTERS[d][1] for d in WHEEL_DESIGNATIONS]
        zs = [STUDIO_CENTERS[d][2] for d in WHEEL_DESIGNATIONS]
        self.assertGreater(max(xs) - min(xs), 5.0)   # rozchod na X
        self.assertGreater(max(zs) - min(zs), 10.0)  # rozvor na Z
        self.assertEqual(max(ys) - min(ys), 0.0)      # Y = vyska, konst.

    def test_missing_wheel_blocked(self):
        wheels = _ok_wheels()
        del wheels["RR"]
        rep = _ok_report(wheels=wheels)
        self.assertEqual(rep["overall_status"], "BLOCKED")
        rr = [w for w in rep["wheels"] if w["designation"] == "RR"][0]
        self.assertEqual(rr["reason"], "missing_wheel")
        self.assertTrue(any("missing_wheel" in w for w in rep["warnings"]))

    def test_fifth_ball_spare_blocked(self):
        # Paty Ball uvnitr Wheels (rezerva, ne oznaceni FL/FR/RL/RR)
        # = UNKNOWN kandidat -> vzdy BLOCKED.
        rep = _ok_report(unidentified=[{"instance_id": 999,
                                        "name": "Spare",
                                        "reason": "bad_designation"}])
        self.assertEqual(rep["overall_status"], "BLOCKED")
        self.assertTrue(any("999" in w for w in rep["warnings"]))

    def test_duplicate_designation_blocked(self):
        wheels = _ok_wheels(
            status_override={"FR": "BLOCKED"},
            reason_override={"FR": "duplicate_designation: 2 candidates"})
        rep = _ok_report(wheels=wheels)
        self.assertEqual(rep["overall_status"], "BLOCKED")
        fr = [w for w in rep["wheels"] if w["designation"] == "FR"][0]
        self.assertEqual(fr["status"], "BLOCKED")
        self.assertIn("duplicate_designation", fr["reason"])

    def test_side_swap_blocked(self):
        # Prohozeni stran: oznaceni FL nese stred pravého kola.
        centers = dict(STUDIO_CENTERS)
        centers["FL"], centers["FR"] = centers["FR"], centers["FL"]
        rep = _ok_report(wheels=_ok_wheels(center_override=centers))
        self.assertEqual(rep["overall_status"], "BLOCKED")
        self.assertTrue(any("side_or_axle_swap" in w
                            for w in rep["warnings"]))

    def test_axle_swap_blocked(self):
        # Prohozeni naprav: FL <-> RL (predni/zadni).
        centers = dict(STUDIO_CENTERS)
        centers["FL"], centers["RL"] = centers["RL"], centers["FL"]
        rep = _ok_report(wheels=_ok_wheels(center_override=centers))
        self.assertEqual(rep["overall_status"], "BLOCKED")
        self.assertTrue(any("side_or_axle_swap" in w
                            for w in rep["warnings"]))

    def test_diameter_asymmetry_blocked(self):
        sizes = {des: STUDIO_SIZE for des in WHEEL_DESIGNATIONS}
        sizes["RR"] = (3.0, 3.0, 3.0)
        rep = _ok_report(wheels=_ok_wheels(size_override=sizes))
        self.assertEqual(rep["overall_status"], "BLOCKED")
        rr = [w for w in rep["wheels"] if w["designation"] == "RR"][0]
        self.assertEqual(rr["reason"], "diameter_asymmetry")

    def test_height_asymmetry_blocked(self):
        centers = dict(STUDIO_CENTERS)
        fl = centers["FL"]
        centers["FL"] = (fl[0], fl[1] + 0.5, fl[2])
        rep = _ok_report(wheels=_ok_wheels(center_override=centers))
        self.assertEqual(rep["overall_status"], "BLOCKED")
        self.assertTrue(any("height_asymmetry" in w
                            for w in rep["warnings"]))

    def test_unverified_frame_caps_at_unknown(self):
        frame = dict(COORDINATE_FRAME_ACTUAL)
        frame["verified_in_studio"] = False
        rep = _ok_report(coordinate_frame=frame)
        self.assertEqual(rep["overall_status"], "UNKNOWN")

    def test_missing_geometry_unknown(self):
        wheels = _ok_wheels()
        wheels["FL"]["center_studs"] = None
        wheels["FL"]["status"] = "UNKNOWN"
        wheels["FL"]["reason"] = "missing_position"
        rep = _ok_report(wheels=wheels)
        self.assertEqual(rep["overall_status"], "UNKNOWN")
        self.assertIsNone(rep["axles"]["front"]["track_studs"])

    def test_determinism_and_json_roundtrip(self):
        rep1 = _ok_report()
        rep2 = _ok_report()
        self.assertEqual(rep1, rep2)
        self.assertEqual(json.loads(json.dumps(rep1, sort_keys=True)), rep1)
        self.assertEqual(rep1["report_id"], "JeepTemplate@dc8747e016e1")

    def test_report_from_assess_blocked_on_real_chassis_parts(self):
        # 44 dilu podvozku ve Wheels = legitimni podvozek, ne kola:
        # assess je eviduje jako unidentified -> report drzi BLOCKED.
        assess = {
            "wheels": {
                des: {"status": "GEOMETRY_OK",
                      "instance_id": STUDIO_IDS[des],
                      "shape": "Ball", "size": STUDIO_SIZE,
                      "position": STUDIO_CENTERS[des],
                      "failed_checks": []}
                for des in WHEEL_DESIGNATIONS},
            "unidentified": [{"instance_id": 9 + i, "name": "Hub",
                              "failed_checks": ["not_a_wheel"]}
                             for i in range(44)],
            "blocked_reasons": ["UNKNOWN candidate(s) inside Model:Wheels: 44",
                                "float_decode_unverified:erne overena kalibrace"],
        }
        rep = report_from_assess(
            "JeepTemplate",
            "assets/chassis-original/chasis-work-copy.rbxm",
            "dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf",
            assess, "rbxm_parser M2/C05", "test")
        self.assertEqual(rep["overall_status"], "BLOCKED")
        self.assertEqual(rep["wheelbase_studs"] is not None, True)
        self.assertTrue(any("unidentified inside Wheels" in w
                            for w in rep["warnings"]))


if __name__ == "__main__":
    unittest.main()

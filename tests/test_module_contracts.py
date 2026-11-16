"""Integracni/kontraktni testy modulu vlny 1 (ARCHITECTURE §5, §7).

Strategie: testovat SKUTECNE chovani existujicich modulu proti
nezavislym orakulum (pravda o fyzice, ne opis implementace).
Chybi-li modul nebo jeho cast, test hlasi PENDING (skip), nikoli
PASS ani FAIL — dle pravidla 'neschvaluj nehotove'.

Aktualni stav vlny 1 (overeno ctenim src/, 2026-11-16):
  src/Physics/{engine,gearbox,diff,tires,brakes,mass}.py ... EXISTUJE
  src/Chassis/base.py (ChassisAdapter ABC) .................. EXISTUJE
  src/Telemetry/metrics.py (compute_metrics) ................ EXISTUJE
  src/Reference/ ............................................ PRAZDNE -> PENDING
  Sim (run_scenario), Optimizer (propose/A1-A5) ............. CHYBI -> PENDING
  konkretni adaptér achassis-v1 ............................. CHYBI -> PENDING
"""
import csv
import math
import os
import tempfile
import unittest

try:
    from _helpers import try_import
except ImportError:  # unittest discover z korene: tests jako balik
    from tests._helpers import try_import

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

G = 9.81


def need(modname):
    mod, _ = try_import(modname)
    return mod


class TestPhysicsEngine(unittest.TestCase):
    """src/Physics/engine.py: momentova krivka, konverze, rev-gate."""

    def setUp(self):
        mod = need("src.Physics.engine")
        if mod is None:
            self.skipTest("PENDING: src/Physics.engine ve vlne 1 zatim neexistuje")
        self.eng = mod
        self.curve = [(1000, 150.0), (3000, 220.0), (5000, 200.0)]

    def test_rpm_conversion_roundtrip(self):
        self.assertAlmostEqual(
            self.eng.rad_s_to_rpm(self.eng.rpm_to_rad_s(3000.0)),
            3000.0, places=9)

    def test_torque_interpolation(self):
        # Stred mezi (1000,150) a (3000,220) pri 2000 rpm = 185 Nm.
        self.assertAlmostEqual(
            self.eng.torque_at_rpm(self.curve, 2000.0), 185.0, places=9)

    def test_torque_clamps_outside(self):
        self.assertEqual(self.eng.torque_at_rpm(self.curve, 500.0), 150.0)
        self.assertEqual(self.eng.torque_at_rpm(self.curve, 9000.0), 200.0)

    def test_bad_curve_rejected(self):
        with self.assertRaises(ValueError):
            self.eng.validate_curve([(1000, 100.0)])
        with self.assertRaises(ValueError):
            self.eng.validate_curve([(2000, 100.0), (2000, 120.0)])
        with self.assertRaises(ValueError):
            self.eng.validate_curve([(1000, -5.0), (2000, 100.0)])

    def test_power_relation(self):
        # P = M * omega musi platit presne (SI konzistence).
        out = self.eng.engine_output(self.curve, 3000.0, 1.0, 6500.0)
        omega = 3000.0 * 2.0 * math.pi / 60.0
        self.assertAlmostEqual(out["power_w"], out["torque_nm"] * omega,
                               places=6)
        self.assertAlmostEqual(out["power_kw"], out["power_w"] / 1000.0,
                               places=9)

    def test_rev_gate_cuts_torque(self):
        out = self.eng.engine_output(self.curve, 7000.0, 1.0, 6500.0)
        self.assertEqual(out["torque_nm"], 0.0)
        self.assertTrue(out["at_redline"])


class TestPhysicsGearbox(unittest.TestCase):
    """src/Physics/gearbox.py: prevody, neutral, razeni s hysterezi."""

    def setUp(self):
        mod = need("src.Physics.gearbox")
        if mod is None:
            self.skipTest("PENDING: src/Physics.gearbox ve vlne 1 zatim neexistuje")
        self.gb = mod
        self.gears = [3.2, 2.1, 1.5]
        self.fd = 3.7

    def test_ratio_multiplication(self):
        out = self.gb.gear_output(200.0, 300.0, 1, self.gears, self.fd,
                                  efficiency=1.0)
        self.assertAlmostEqual(out["total_ratio"], 3.2 * 3.7, places=9)
        self.assertAlmostEqual(out["torque_out_nm"], 200.0 * 3.2 * 3.7,
                               places=6)
        # Vykon se zachovava (idealni prevod, eff=1): M1*w1 = M2*w2.
        self.assertAlmostEqual(out["torque_out_nm"] * out["omega_out_rads"],
                               200.0 * 300.0, places=3)

    def test_neutral(self):
        out = self.gb.gear_output(200.0, 300.0, 0, self.gears, self.fd)
        self.assertEqual(out["torque_out_nm"], 0.0)
        self.assertEqual(out["total_ratio"], 0.0)

    def test_bad_ratios_rejected(self):
        with self.assertRaises(ValueError):
            self.gb.validate_ratios([], self.fd)
        with self.assertRaises(ValueError):
            self.gb.validate_ratios([3.2, -1.0], self.fd)
        with self.assertRaises(ValueError):
            self.gb.validate_ratios(self.gears, 0.0)

    def test_shift_hysteresis(self):
        up = self.gb.update_gear(1, 6200.0, 1.0, 20.0, self.gears,
                                 shift_up_rpm=6000.0, shift_down_rpm=2500.0)
        self.assertEqual((up["gear"], up["shift_event"]), (2, "up"))
        hold = self.gb.update_gear(2, 4000.0, 1.0, 25.0, self.gears,
                                   shift_up_rpm=6000.0, shift_down_rpm=2500.0)
        self.assertEqual((hold["gear"], hold["shift_event"]), (2, None))
        dn = self.gb.update_gear(2, 2000.0, 0.2, 15.0, self.gears,
                                 shift_up_rpm=6000.0, shift_down_rpm=2500.0)
        self.assertEqual((dn["gear"], dn["shift_event"]), (1, "down"))


class TestPhysicsDiff(unittest.TestCase):
    """src/Physics/diff.py: invariant souctu momentu, nehnana naprava = 0."""

    def setUp(self):
        mod = need("src.Physics.diff")
        if mod is None:
            self.skipTest("PENDING: src/Physics.diff ve vlne 1 zatim neexistuje")
        self.diff = mod

    def test_sum_invariant(self):
        t = self.diff.distribute(1000.0, "AWD", front_bias=0.4,
                                 efficiency=1.0)
        self.assertAlmostEqual(sum(t.values()), 1000.0, places=6)

    def test_rwd_rear_only(self):
        t = self.diff.distribute(800.0, "RWD")
        self.assertEqual(t["FL"], 0.0)
        self.assertEqual(t["FR"], 0.0)
        self.assertGreater(t["RL"] + t["RR"], 0.0)

    def test_fwd_front_only(self):
        t = self.diff.distribute(800.0, "FWD")
        self.assertEqual(t["RL"], 0.0)
        self.assertEqual(t["RR"], 0.0)
        self.assertGreater(t["FL"] + t["FR"], 0.0)

    def test_open_diff_equal_split(self):
        left, right = self.diff.shaft_split(500.0, 0.0, 50.0, 50.0)
        self.assertAlmostEqual(left, right, places=9)

    def test_bad_drive_type(self):
        with self.assertRaises(ValueError):
            self.diff.distribute(100.0, "4WD")


class TestPhysicsTires(unittest.TestCase):
    """src/Physics/tires.py: skluz, Magic Formula, treci kruznice."""

    def setUp(self):
        mod = need("src.Physics.tires")
        if mod is None:
            self.skipTest("PENDING: src/Physics.tires ve vlne 1 zatim neexistuje")
        self.tr = mod

    def test_no_slip_zero(self):
        s = self.tr.compute_slip(30.0, 0.33, 9.9, 0.0, 0.0)
        self.assertAlmostEqual(s["kappa"], 0.0, places=9)
        self.assertAlmostEqual(s["alpha_rad"], 0.0, places=9)

    def test_crosscheck_oracle_kappa(self):
        # Nezavisly oracle: kappa = (w*r - vx)/max(|vx|, eps), eps vlny 1 = 0.5.
        s = self.tr.compute_slip(40.0, 0.33, 9.9, 0.0, 0.0)
        expected = (40.0 * 0.33 - 9.9) / max(abs(9.9), 0.5)
        self.assertAlmostEqual(s["kappa"], expected, places=9)
        self.assertGreater(s["kappa"], 0.2)  # prokluz dle §4.2

    def test_magic_formula_origin_and_sign(self):
        self.assertEqual(self.tr.magic_formula(0.0, 10.0, 1.9, 5000.0), 0.0)
        self.assertGreater(self.tr.magic_formula(0.1, 10.0, 1.9, 5000.0), 0.0)
        self.assertLess(self.tr.magic_formula(-0.1, 10.0, 1.9, 5000.0), 0.0)

    def test_friction_circle(self):
        # |F| <= mu*Fz vzdy, i pri kombinovanem skluzu.
        g = self.tr.compute_grip(0.3, 0.2, 4000.0, 1.0)
        self.assertLessEqual(math.hypot(g["fx_N"], g["fy_N"]),
                             1.0 * 4000.0 + 1e-9)
        self.assertLessEqual(g["rho"], 1.0 + 1e-12)

    def test_airborne_zero_force(self):
        g = self.tr.compute_grip(0.5, 0.3, 0.0, 1.0)
        self.assertEqual((g["fx_N"], g["fy_N"]), (0.0, 0.0))

    def test_bad_radius_rejected(self):
        with self.assertRaises(ValueError):
            self.tr.compute_slip(10.0, 0.0, 5.0, 0.0, 0.0)


class TestPhysicsMass(unittest.TestCase):
    """src/Physics/mass.py: hmotnost, teziste, tiha, setrvacnost."""

    def setUp(self):
        mod = need("src.Physics.mass")
        if mod is None:
            self.skipTest("PENDING: src/Physics.mass ve vlne 1 zatim neexistuje")
        self.mass = mod

    def test_total_and_weight(self):
        self.assertAlmostEqual(self.mass.total_mass([1000.0, 400.0]),
                               1400.0, places=9)
        self.assertAlmostEqual(self.mass.weight_N(1400.0), 1400.0 * G,
                               places=6)

    def test_center_of_mass_symmetric(self):
        com = self.mass.center_of_mass([700.0, 700.0],
                                       [(-1.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
        self.assertAlmostEqual(com[0], 0.0, places=9)
        self.assertAlmostEqual(com[1], 0.0, places=9)
        self.assertAlmostEqual(com[2], 0.5, places=9)

    def test_inertia_cuboid_order(self):
        # Dlouhy kvadr (lx>ly): Izz > Ixx (osa z nejvetsi setrvacnost).
        ixx, _iyy, izz = self.mass.inertia_cuboid(1400.0, 4.4, 1.8, 1.4)
        self.assertGreater(izz, ixx)
        self.assertGreater(ixx, 0.0)

    def test_negative_mass_rejected(self):
        with self.assertRaises(ValueError):
            self.mass.total_mass([100.0, -5.0])


class TestPhysicsBrakes(unittest.TestCase):
    """src/Physics/brakes.py: rozdeleni bias, rucni brzda, ABS prah."""

    def setUp(self):
        mod = need("src.Physics.brakes")
        if mod is None:
            self.skipTest("PENDING: src/Physics.brakes ve vlne 1 zatim neexistuje")
        self.br = mod

    def test_bias_split(self):
        t = self.br.service_brake(1.0, 4000.0, 0.6)
        self.assertAlmostEqual(t["FL"] + t["FR"], 2400.0, places=9)
        self.assertAlmostEqual(t["RL"] + t["RR"], 1600.0, places=9)
        self.assertAlmostEqual(sum(t.values()), 4000.0, places=9)

    def test_zero_pedal_zero_torque(self):
        t = self.br.service_brake(0.0, 4000.0, 0.6)
        self.assertEqual(sum(t.values()), 0.0)

    def test_handbrake_rear_only(self):
        t = self.br.handbrake(1.0, 2000.0)
        self.assertEqual(set(t.keys()), {"RL", "RR"})
        self.assertAlmostEqual(sum(t.values()), 2000.0, places=9)

    def test_abs_below_threshold_full(self):
        r = self.br.abs_modulate(3000.0, 0.1, threshold=0.2)
        val = r.get("applied_nm", r.get("torque_nm", list(r.values())[0]))
        self.assertAlmostEqual(val, 3000.0, places=9)


class TestChassisAdapterContract(unittest.TestCase):
    """src/Chassis/base.py: ChassisAdapter dle ARCH §5.4."""

    def setUp(self):
        mod = need("src.Chassis.base")
        if mod is None:
            self.skipTest("PENDING: src/Chassis.base ve vlne 1 zatim neexistuje")
        self.base = mod

    def test_interface_methods_abstract(self):
        for m in ("detect", "list_parameters", "apply_config", "limits"):
            self.assertTrue(hasattr(self.base.ChassisAdapter, m),
                            "ChassisAdapter.%s chybi (ARCH §5.4)" % m)
        self.assertTrue(getattr(self.base.ChassisAdapter,
                                "__abstractmethods__", set()),
                        "ChassisAdapter ma byt ABC")

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            self.base.ChassisAdapter()

    def test_parameter_def_fields(self):
        import dataclasses
        names = {f.name for f in dataclasses.fields(self.base.ParameterDef)}
        for req in ("name", "tune_key", "config_path", "provenance",
                    "mutable", "default", "source_ref"):
            self.assertIn(req, names)

    def test_concrete_adapter_detect(self):
        from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter
        import tempfile
        a = AChassisV1Adapter()
        self.assertEqual(a.id, "achassis-v1")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(a.detect(d), 0.0)
            open(os.path.join(d, "jine.rbxm"), "w").close()
            self.assertEqual(a.detect(d), 0.4)
            open(os.path.join(d, "chasis-work-copy.rbxm"), "w").close()
            self.assertEqual(a.detect(d), 0.85)
        self.assertEqual(a.detect(os.path.join("neexistujici-adresar-xyz")),
                         0.0)
        for v in (0.0, 0.4, 0.85):
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_concrete_adapter_parameters(self):
        from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter
        a = AChassisV1Adapter()
        params = a.list_parameters()
        self.assertGreater(len(params), 0)
        for p in params:
            self.assertIn(p.provenance, self.base.PROVENANCE_VALUES,
                          "neplatna provenance u %s" % p.name)
            if p.mutable:
                self.assertTrue(p.tune_key,
                                "mutable %s bez tune_key" % p.name)
        self.assertTrue(all(isinstance(s, str) and s for s in a.limits()),
                        "limits() musi vratit neprazdne retezce")

    def test_concrete_adapter_apply_config(self):
        from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter
        a = AChassisV1Adapter()
        mutable_keys = [p.tune_key for p in a.list_parameters()
                        if p.mutable and p.tune_key]
        # Neznamy klic = rejected, nikdy tichy zapis.
        rep = a.apply_config("some/dir", {"parameters": {"tune": {
            "NEEXISTUJE_XYZ": 1}}})
        self.assertEqual(len(rep.applied), 0)
        self.assertEqual(len(rep.rejected), 1)
        # Chybna struktura configu = warning, nic neaplikovano.
        rep2 = a.apply_config("some/dir", {"nonsense": True})
        self.assertEqual(len(rep2.applied), 0)
        self.assertTrue(rep2.warnings)
        # Mutable klic (je-li jaky) projde do applied.
        if mutable_keys:
            rep3 = a.apply_config("some/dir", {"parameters": {"tune": {
                mutable_keys[0]: 12345}}})
            self.assertEqual(len(rep3.rejected), 0)
            self.assertEqual(len(rep3.applied), 1)


def _synthetic_rows():
    """Synteticka telemetrie: 0-8 s akcelerace 4 m/s², pak brzdeni 8 m/s²."""
    rows = []
    dt = 1.0 / 60.0
    t, v = 0.0, 0.0
    r = 0.33
    x = 0.0
    while t <= 8.0:
        v += 4.0 * dt
        x += v * dt
        rows.append([t, x, 0.0, v, 4.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                     2, 4000.0, 200.0,
                     v / r, v / r, v / r, v / r, 0.0, 0.0, 0.0, 0.0,
                     3433.5, 3433.5, 3433.5, 3433.5, 0.0, 0.0, 0.0, 0.0])
        t += dt
    while v > 0.0:
        v = max(0.0, v - 8.0 * dt)
        x += v * dt
        rows.append([t, x, 0.0, v, -8.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0,
                     2, 1500.0, 0.0,
                     v / r, v / r, v / r, v / r, 0.0, 0.0, 0.0, 0.0,
                     4119.0, 4119.0, 2746.0, 2746.0, 0.0, 0.0, 0.0, 0.0])
        t += dt
    return rows


class TestTelemetryMetrics(unittest.TestCase):
    """src/Telemetry/metrics.py vs nezavisla orakula (TESTING §4.2)."""

    def setUp(self):
        mod = need("src.Telemetry.metrics")
        if mod is None:
            self.skipTest("PENDING: src/Telemetry.metrics ve vlne 1 zatim "
                          "neexistuje")
        self.mx = mod

    def _dicts(self):
        cols = list(self.mx.TELEMETRY_COLUMNS)
        return [dict(zip(cols, r)) for r in _synthetic_rows()]

    def test_t_0_100_matches_analytic(self):
        m = self.mx.compute_metrics(self._dicts())
        # Analyticky: v0=0, a=4 => t(27.78) = 6.944 s ± vzorkovani.
        self.assertIsNotNone(m["t_0_100_s"])
        self.assertAlmostEqual(m["t_0_100_s"], (100.0 / 3.6) / 4.0,
                               delta=2.0 / 60.0)

    def test_brake_distance_matches_analytic(self):
        dicts = self._dicts()
        m = self.mx.compute_metrics(dicts)
        v0 = next(r["v_mps"] for r in dicts if r["brake"] >= 0.9)
        expected = v0 * v0 / (2.0 * 8.0)
        self.assertIsNotNone(m["brake_distance_100_0_m"])
        self.assertAlmostEqual(m["brake_distance_100_0_m"], expected,
                               delta=1.0)
        # Konzistence §6.3 bod 2: mean_decel = v0²/(2s).
        self.assertAlmostEqual(m["mean_decel_mps2"], 8.0, delta=0.3)

    def test_load_csv_roundtrip(self):
        rows = _synthetic_rows()
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False, newline="",
                                         encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(self.mx.TELEMETRY_COLUMNS)
            w.writerows(rows)
            path = fh.name
        try:
            loaded = self.mx.load_telemetry(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(loaded), len(rows))
        self.assertAlmostEqual(loaded[0]["v_mps"], rows[0][3], places=9)

    def test_bad_header_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False, newline="",
                                         encoding="utf-8") as fh:
            fh.write("time_s,v_mps\n0.0,0.0\n0.1,1.0\n")
            path = fh.name
        try:
            with self.assertRaises(ValueError):
                self.mx.load_telemetry(path)
        finally:
            os.unlink(path)

    def test_vertical_force_balance_on_telemetry(self):
        # ΣFz = m*g: syntetika pouziva 4x3433.5 N = 1400 kg x 9.81.
        cols = list(self.mx.TELEMETRY_COLUMNS)
        i = cols.index("fz_FL")
        total = sum(_synthetic_rows()[0][i:i + 4])
        self.assertAlmostEqual(total, 1400.0 * G, delta=1.0)

    def test_evaluate_wrapper_pending(self):
        self.skipTest("PENDING: ARCH §5.3 'evaluate()->TestResult(score, "
                      "environment.mode)' nad compute_metrics ve vlne 1 "
                      "zatim neexistuje (Agent F)")


class TestReferenceProvenance(unittest.TestCase):
    """Provenance v referencnich datech (ARCH §3.2, TESTING §8.1 F5)."""

    def _walk(self, node, path=""):
        bad = []
        n = 0
        if isinstance(node, dict):
            if "value" in node:
                n += 1
                v, c, s = (node.get("value"), node.get("confidence"),
                           node.get("source"))
                if not isinstance(c, (int, float)) or not 0 <= c <= 1:
                    bad.append((path, "confidence mimo [0,1]", c))
                if v is None and c != 0:
                    bad.append((path, "null musi mit confidence 0", c))
                if v is not None and not s:
                    bad.append((path, "chybi source", s))
            for k, v in node.items():
                b, c = self._walk(v, path + "/" + str(k))
                bad += b
                n += c
        elif isinstance(node, list):
            for i, v in enumerate(node):
                b, c = self._walk(v, path + "/%d" % i)
                bad += b
                n += c
        return bad, n

    def test_example_vehicle_provenance(self):
        import json
        path = os.path.join(ROOT, "vehicle-data", "references",
                            "example-vehicle.json")
        if not os.path.exists(path):
            self.skipTest("PENDING: example-vehicle.json zatim neexistuje")
        with open(path, encoding="utf-8") as fh:
            profile = json.load(fh)
        bad, n = self._walk(profile)
        self.assertGreater(n, 0, "zadne provenance zaznamy nenalezeny")
        self.assertEqual(bad, [], "poruseni provenance (ARCH §3.2): %s" % bad)

    def test_schema_conformance_pending(self):
        self.skipTest("PENDING: shoda example-vehicle.json s "
                      "contracts/reference_profile.schema.json "
                      "(specs/target_metrics, ARCH §3.2) — Faze 5")


class TestSimContract(unittest.TestCase):
    """Kontrakt Sim/TestEnvironment: run_scenario(config, scenario, mode)."""

    def test_run_scenario_api(self):
        mod = need("Sim")
        if mod is None:
            mod = need("src.Sim")
        if mod is None:
            self.skipTest("PENDING: modul Sim/TestEnvironment (Faze 9) ve vlne "
                          "1 zatim neexistuje (ARCH §5.3)")
        self.assertTrue(hasattr(mod, "run_scenario"))


class TestOptimizerContract(unittest.TestCase):
    """Kontrakt Optimizeru: propose + A1–A5, best_config_id, rollback."""

    def test_propose_api(self):
        mod = need("Optimizer")
        if mod is None:
            mod = need("src.Optimizer")
        if mod is None:
            self.skipTest("PENDING: modul Optimizer (Faze 10) ve vlne 1 "
                          "zatim neexistuje (ARCH §5.2, TESTING §5)")
        for fn in ("propose", "acceptance_decision"):
            self.assertTrue(hasattr(mod, fn), "Optimizer.%s chybi" % fn)


if __name__ == "__main__":
    unittest.main()

"""M4 oracle tests: physics invariants on synthetic inputs.

Covers engine, gearbox, diff, tires, brakes, load_transfer, mass, aero.
All inputs are synthetic (no vehicle constants asserted); each test checks
a structural invariant of the model, not a measured value.
"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Physics import aero as aero_mod  # noqa: E402
from src.Physics import brakes as brakes_mod  # noqa: E402
from src.Physics import diff as diff_mod  # noqa: E402
from src.Physics import engine as engine_mod  # noqa: E402
from src.Physics import gearbox as gearbox_mod  # noqa: E402
from src.Physics import load_transfer as load_mod  # noqa: E402
from src.Physics import mass as mass_mod  # noqa: E402
from src.Physics import tires as tires_mod  # noqa: E402

# Synthetic fixtures (arbitrary, not vehicle data).
CURVE = [(1000.0, 100.0), (3000.0, 200.0), (5000.0, 150.0)]
GEARS = [3.0, 2.0, 1.4, 1.0]
FINAL_DRIVE = 4.0
MASS = 1200.0
A_M, B_M = 1.2, 1.5
WHEELBASE = A_M + B_M
TRACK = 1.6
G = 9.81


class TestM4Oracles(unittest.TestCase):
    def test_fz_equilibrium_static(self):
        """Static corner loads sum to vehicle weight."""
        loads = load_mod.static_loads(MASS, A_M, B_M, WHEELBASE, G)
        total = sum(loads[w] for w in ("FL", "FR", "RL", "RR"))
        self.assertAlmostEqual(total, MASS * G, delta=1e-6 * MASS * G)
        self.assertTrue(load_mod.check_load_sum(loads, MASS, G))

    def test_fz_equilibrium_quasistatic_no_lift(self):
        """Quasistatic loads (no lift/clamp) preserve total weight + aero."""
        out = load_mod.compute_loads(MASS, A_M, B_M, 0.5, WHEELBASE, TRACK,
                                     a_long_mps2=2.0, a_lat_mps2=1.0, g=G,
                                     aero_N=500.0, front_aero_bias=0.5)
        self.assertFalse(out["lifted"])
        total = sum(out[w] for w in ("FL", "FR", "RL", "RR"))
        self.assertAlmostEqual(total, MASS * G + 500.0, delta=1e-6 * MASS * G)

    def test_power_consistency(self):
        """Engine power equals torque times angular speed."""
        rpm = 3000.0
        out = engine_mod.engine_output(CURVE, rpm, 0.8, 6000.0)
        omega = rpm * engine_mod.RPM_TO_RADS
        self.assertAlmostEqual(out["power_w"], out["torque_nm"] * omega,
                               delta=1e-9)

    def test_gear_chain_efficiency(self):
        """Gearbox conserves power up to efficiency: T_out*w_out = T_in*w_in*eff."""
        tin, win, eff = 200.0, 300.0, 0.93
        for gear in (1, 2, 3, 4):
            out = gearbox_mod.gear_output(tin, win, gear, GEARS, FINAL_DRIVE, eff)
            self.assertAlmostEqual(out["torque_out_nm"] * out["omega_out_rads"],
                                   tin * win * eff, delta=1e-9)
        rev = gearbox_mod.gear_output(tin, win, -1, GEARS, FINAL_DRIVE, eff,
                                      reverse_ratio=3.2)
        self.assertAlmostEqual(abs(rev["torque_out_nm"] * rev["omega_out_rads"]),
                               tin * win * eff, delta=1e-9)

    def test_diff_sum_invariant(self):
        """Drivetrain split preserves total torque: sum(wheels) = T_in * eff."""
        for drive in ("FWD", "RWD", "AWD"):
            got = diff_mod.distribute(500.0, drive, front_bias=0.4,
                                      lock_front=0.3, lock_rear=0.5,
                                      lock_center=0.2,
                                      omega={"FL": 10.0, "FR": 12.0,
                                             "RL": 11.0, "RR": 11.5},
                                      efficiency=0.95)
            total = sum(got[w] for w in ("FL", "FR", "RL", "RR"))
            self.assertAlmostEqual(total, 500.0 * 0.95, delta=1e-9,
                                   msg=f"drive={drive}")

    def test_friction_circle(self):
        """Resultant tire force never exceeds mu * Fz."""
        for kappa, alpha, fz, mu in [(0.05, 0.02, 4000.0, 1.0),
                                     (0.5, 0.3, 3000.0, 0.8),
                                     (2.0, 1.0, 5000.0, 1.2),
                                     (-0.8, -0.5, 2500.0, 0.6)]:
            g = tires_mod.compute_grip(kappa, alpha, fz, mu)
            resultant = math.hypot(g["fx_N"], g["fy_N"])
            self.assertLessEqual(resultant, mu * fz + 1e-9)
            self.assertLessEqual(g["rho"], 1.0 + 1e-12)

    def test_rev_gate_blocks(self):
        """Above redline the engine produces zero torque/power."""
        out = engine_mod.engine_output(CURVE, 6500.0, 1.0, 6000.0)
        self.assertEqual(out["torque_nm"], 0.0)
        self.assertEqual(out["power_w"], 0.0)
        self.assertTrue(out["at_redline"])
        below = engine_mod.engine_output(CURVE, 5999.0, 1.0, 6000.0)
        self.assertGreater(below["torque_nm"], 0.0)

    def test_shift_hysteresis(self):
        """Upshift threshold strictly above downshift; deadband holds gear."""
        with self.assertRaises(ValueError):
            gearbox_mod.update_gear(2, 3000.0, 0.5, 20.0, GEARS, 3000.0, 3000.0)
        up = gearbox_mod.update_gear(2, 5500.0, 0.8, 30.0, GEARS, 5000.0, 2500.0)
        self.assertEqual((up["gear"], up["shift_event"]), (3, "up"))
        # Same rpm band middle: no oscillation, gear held.
        hold = gearbox_mod.update_gear(3, 4000.0, 0.8, 30.0, GEARS, 5000.0, 2500.0)
        self.assertEqual((hold["gear"], hold["shift_event"]), (3, None))
        down = gearbox_mod.update_gear(3, 2000.0, 0.3, 30.0, GEARS, 5000.0, 2500.0)
        self.assertEqual((down["gear"], down["shift_event"]), (2, "down"))

    def test_brake_bias_in_range(self):
        """Bias splits total pedal torque; outside [0, 1] is rejected."""
        tmax, bias = 4000.0, 0.6
        got = brakes_mod.service_brake(1.0, tmax, bias)
        front = got["FL"] + got["FR"]
        rear = got["RL"] + got["RR"]
        self.assertAlmostEqual(front, tmax * bias, delta=1e-9)
        self.assertAlmostEqual(rear, tmax * (1.0 - bias), delta=1e-9)
        self.assertAlmostEqual(front + rear, tmax, delta=1e-9)
        for bad in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                brakes_mod.service_brake(0.5, tmax, bad)

    def test_mass_positive(self):
        """Total mass and weight are positive; empty/non-positive rejected."""
        self.assertGreater(mass_mod.total_mass([400.0, 500.0, 300.0]), 0.0)
        self.assertGreater(mass_mod.weight_N(MASS), 0.0)
        with self.assertRaises(ValueError):
            mass_mod.total_mass([])
        with self.assertRaises(ValueError):
            mass_mod.total_mass([100.0, -5.0])
        with self.assertRaises(ValueError):
            mass_mod.total_mass([0.0, 0.0])

    def test_symmetry_left_right(self):
        """Zero lateral offset keeps left/right loads equal."""
        out = load_mod.compute_loads(MASS, A_M, B_M, 0.5, WHEELBASE, TRACK,
                                     a_long_mps2=3.0, a_lat_mps2=0.0, g=G)
        self.assertAlmostEqual(out["FL"], out["FR"], delta=1e-9)
        self.assertAlmostEqual(out["RL"], out["RR"], delta=1e-9)
        # Open diff with equal wheel speeds splits axle torque 50/50.
        left, right = diff_mod.shaft_split(1000.0, 0.0, 20.0, 20.0)
        self.assertAlmostEqual(left, right, delta=1e-12)

    def test_determinism(self):
        """Same synthetic inputs give bit-identical outputs twice."""
        first = load_mod.compute_loads(MASS, A_M, B_M, 0.5, WHEELBASE, TRACK,
                                       a_long_mps2=2.0, a_lat_mps2=1.0)
        second = load_mod.compute_loads(MASS, A_M, B_M, 0.5, WHEELBASE, TRACK,
                                        a_long_mps2=2.0, a_lat_mps2=1.0)
        self.assertEqual(first, second)
        eng1 = engine_mod.engine_output(CURVE, 3500.0, 0.7, 6000.0)
        eng2 = engine_mod.engine_output(CURVE, 3500.0, 0.7, 6000.0)
        self.assertEqual(eng1, eng2)
        tire1 = tires_mod.tire_forces(50.0, 0.33, 15.0, 0.5, 0.05, 4000.0, 1.0)
        tire2 = tires_mod.tire_forces(50.0, 0.33, 15.0, 0.5, 0.05, 4000.0, 1.0)
        self.assertEqual(tire1, tire2)

    def test_aero_scales_with_v_squared(self):
        """Drag/downforce are non-negative and scale with v^2."""
        d1 = aero_mod.drag_force(10.0)
        d2 = aero_mod.drag_force(20.0)
        self.assertGreaterEqual(d1, 0.0)
        self.assertAlmostEqual(d2 / d1, 4.0, places=9)
        loads = aero_mod.aero_loads(30.0, ClA_m2=0.5, front_bias=0.4)
        self.assertAlmostEqual(loads["front_N"] + loads["rear_N"],
                               loads["downforce_N"], delta=1e-9)


if __name__ == "__main__":
    unittest.main()

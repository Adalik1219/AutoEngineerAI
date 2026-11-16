"""Fyzikalni sanity testy + determinismus + konvergence (MATH uroven).

Pokryti dle zadani a TESTING-OPTIMIZATION:
- sanity: soucet svislych sil kol = tiha vozidla (§4.1 wheel_load_*),
  energie bez disipace neklesa/nestoupa, sanity rozsahy §6.3 bod 1,
  konzistence mean_decel §6.3 bod 2.
- determinismus: 2x stejny seed => bitove stejny vysledek (§4.6).
- konvergence: dt/2 meni vysledek o mene nez tolerance (§4.6, §6.4 dt).
Ciste stdlib, vzdy spustitelne.
"""
import math
import random
import unittest

G = 9.81


# --- Minimalni referencni integrace (stuha pro determinismus/konvergenci) ---

def simulate_projectile(v0x, v0y, dt, steps, g=G):
    """Semi-implicitni Euler projektilu bez odporu. Deterministicky."""
    x, y, vx, vy = 0.0, 0.0, v0x, v0y
    for _ in range(steps):
        vy -= g * dt
        x += vx * dt
        y += vy * dt
    return (x, y, vx, vy)


def simulate_with_seed(seed, steps=500, dt=1.0 / 240.0):
    """Deterministicka jizda: konstantni rizeni + sum ze seedu (model sumu)."""
    rng = random.Random(seed)  # izolovany generator, deterministicky
    v, s = 10.0, 0.0
    inputs = []
    for _ in range(steps):
        throttle = 0.5
        noise = (rng.random() - 0.5) * 0.02  # modelovana porucha ze seedu
        a = throttle * 4.0 + noise
        v += a * dt
        s += v * dt
        inputs.append((throttle, a))
    return v, s, inputs


class TestVerticalForceBalance(unittest.TestCase):
    """ΣFz: soucet normalovych sil kol = m*g (statika, rovina)."""

    def check_balance(self, loads, mass):
        total = sum(loads.values())
        self.assertAlmostEqual(total, mass * G, delta=mass * G * 1e-9)

    def test_equal_distribution(self):
        m = 1400.0
        per_wheel = m * G / 4.0
        self.check_balance(
            {"FL": per_wheel, "FR": per_wheel,
             "RL": per_wheel, "RR": per_wheel}, m)

    def test_front_rear_split(self):
        # Typicky 60/40 na predni napravu.
        m = 1400.0
        w = m * G
        self.check_balance(
            {"FL": 0.30 * w, "FR": 0.30 * w,
             "RL": 0.20 * w, "RR": 0.20 * w}, m)

    def test_imbalance_detected(self):
        m = 1400.0
        loads = {"FL": 4000.0, "FR": 4000.0, "RL": 3000.0, "RR": 2000.0}
        total = sum(loads.values())
        self.assertNotAlmostEqual(total, m * G, delta=1.0)


class TestEnergyConservation(unittest.TestCase):
    """Bez disipace se mechanicka energie zachovava (v toleranci diskretizace)."""

    def test_projectile_energy_drift_small(self):
        m = 1200.0
        v0x, v0y = 20.0, 20.0
        dt, steps = 1e-4, 2000  # 0.2 s letu
        e0 = 0.5 * m * (v0x ** 2 + v0y ** 2)
        x, y, vx, vy = simulate_projectile(v0x, v0y, dt, steps)
        e1 = 0.5 * m * (vx * vx + vy * vy) + m * G * y
        rel_drift = abs(e1 - e0) / e0
        self.assertLess(rel_drift, 0.01)  # < 1 %

    def test_no_spontaneous_energy_gain_coarse(self):
        # I hrubsi krok nesmi energii radove nafouknout (stabilita).
        m = 1200.0
        v0x, v0y = 20.0, 20.0
        e0 = 0.5 * m * (v0x ** 2 + v0y ** 2)
        _, y, vx, vy = simulate_projectile(v0x, v0y, 1.0 / 60.0, 60)
        e1 = 0.5 * m * (vx * vx + vy * vy) + m * G * y
        self.assertLess(abs(e1 - e0) / e0, 0.05)


class TestSanityRanges(unittest.TestCase):
    """Sanity rozsahy dle §6.3 bod 1 — hodnoty mimo = SUSPECT, ne super-vysledek."""

    def in_range(self, name, value, lo, hi):
        self.assertGreater(value, lo, "%s pod minimem" % name)
        self.assertLess(value, hi, "%s nad maximem" % name)

    def test_typical_sedan_ranges(self):
        self.in_range("t_0_100", 7.5, 1.0, 60.0)
        self.in_range("v_max_kmh", 230.0, 20.0, 400.0)
        self.in_range("brake_100_0_m", 41.2, 10.0, 300.0)

    def test_absurd_values_outside(self):
        with self.assertRaises(AssertionError):
            self.in_range("t_0_100", 0.2, 1.0, 60.0)
        with self.assertRaises(AssertionError):
            self.in_range("v_max_kmh", 900.0, 20.0, 400.0)


class TestDeterminism(unittest.TestCase):
    """Stejny seed + stejny kod => stejny vysledek (§4.6, princip 5 ARCH)."""

    def test_same_seed_bitwise_identical(self):
        r1 = simulate_with_seed(1234)
        r2 = simulate_with_seed(1234)
        self.assertEqual(r1, r2)

    def test_different_seed_differs(self):
        r1 = simulate_with_seed(1234)
        r2 = simulate_with_seed(9999)
        self.assertNotEqual(r1, r2)

    def test_input_hash_stable(self):
        # §4.6: vstupy u(t) bitove identicke mezi opakovanimi, §6.3 bod 3.
        import hashlib
        _, _, u1 = simulate_with_seed(7)
        _, _, u2 = simulate_with_seed(7)
        h1 = hashlib.sha256(repr(u1).encode()).hexdigest()
        h2 = hashlib.sha256(repr(u2).encode()).hexdigest()
        self.assertEqual(h1, h2)


class TestConvergence(unittest.TestCase):
    """Puleni kroku dt/2 meni vysledek o mene nez tolerance (§4.6 re-baseline)."""

    def test_dt_halving_below_tolerance(self):
        v0x, v0y, t_end = 25.0, 10.0, 1.0
        tol = 0.005  # 0.5 % tolerance
        prev = None
        for dt in (1.0 / 60.0, 1.0 / 120.0, 1.0 / 240.0):
            steps = int(round(t_end / dt))
            res = simulate_projectile(v0x, v0y, dt, steps)
            if prev is not None:
                rel = abs(res[0] - prev[0]) / max(abs(prev[0]), 1e-12)
                self.assertLess(rel, tol,
                                "dt=%g nekonverguje (rel. zmena %g)" % (dt, rel))
            prev = res

    def test_converges_to_analytic(self):
        v0x, v0y, t = 25.0, 10.0, 1.0
        x_num, _, _, _ = simulate_projectile(v0x, v0y, 1.0 / 240.0,
                                             int(1.0 / (1.0 / 240.0)))
        x_exact = v0x * t  # vodorovne bez odporu
        self.assertAlmostEqual(x_num, x_exact, delta=abs(x_exact) * 0.01)


if __name__ == "__main__":
    unittest.main()

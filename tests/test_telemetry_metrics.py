"""Unit testy metrik telemetrie dle TESTING-OPTIMIZATION §4.1–§4.4 (MATH uroven).

Overuji vzorce z §4.2 na syntetickych RunTrace datech: interpolace
t_0_100, integrace brzdne drahy, v_kmh, ustalena V-max, RMS, slip ratio,
understeer gradient znamenko, sideslip beta. Ciste stdlib, vzdy spustitelne.

Jakmile vlna 1 doda modul Telemetry/Sim, tyto referencni implementace
slouzi jako oracle proti src implementaci (viz test_module_contracts).
"""
import math
import unittest

V_100 = 100.0 / 3.6  # 27.777... m/s
V_60 = 60.0 / 3.6


def kmh(v_long, v_lat=0.0):
    return 3.6 * math.sqrt(v_long ** 2 + v_lat ** 2)


def time_at_threshold(times, speeds, threshold):
    """Prvni t, kdy v >= threshold, s linearni interpolaci (§4.2)."""
    for i in range(1, len(times)):
        if speeds[i] >= threshold:
            t0, t1 = times[i - 1], times[i]
            v0, v1 = speeds[i - 1], speeds[i]
            if v1 == v0:
                return t1
            frac = (threshold - v0) / (v1 - v0)
            return t0 + frac * (t1 - t0)
    raise ValueError("threshold never reached")


def braking_distance(times, speeds, brake_start_idx=0):
    """Lichobeznikova integrace v_long dt od brzdeni do v < 0.1 m/s (§4.2)."""
    s = 0.0
    for i in range(brake_start_idx + 1, len(times)):
        dt = times[i] - times[i - 1]
        v0, v1 = speeds[i - 1], speeds[i]
        if v0 < 0.1 and v1 < 0.1:
            break
        s += 0.5 * (v0 + v1) * dt
    return s


def settled_vmax(speeds):
    """Prumer poslednich 5 s okna; pokud std > 0.5 m/s, flag not_settled (§4.2)."""
    window = speeds[-5:] if len(speeds) >= 5 else speeds
    mean = sum(window) / len(window)
    var = sum((x - mean) ** 2 for x in window) / len(window)
    return mean, (math.sqrt(var) >= 0.5)


def rms(values):
    return math.sqrt(sum(x * x for x in values) / len(values))


def slip_ratio(omega, r, v_wx, eps=1.0):
    """kappa = (omega*r - v_wx) / max(|v_wx|, eps) (§4.2)."""
    return (omega * r - v_wx) / max(abs(v_wx), eps)


def sideslip_beta(v_long, v_lat):
    """beta = atan2(v_lat, |v_long|); pri |v_long| < 1 m/s neplatne (§4.1)."""
    if abs(v_long) < 1.0:
        return None
    return math.atan2(v_lat, abs(v_long))


def understeer_gradient(a_lat_list, delta_list):
    """Smernice K_us = d(delta)/d(a_lat) nejmensimi ctverci (§4.2)."""
    n = len(a_lat_list)
    if n < 3:
        return None  # vyzaduje min. 3 platne kroky
    mx = sum(a_lat_list) / n
    my = sum(delta_list) / n
    denom = sum((x - mx) ** 2 for x in a_lat_list)
    if denom == 0:
        return None
    return sum((x - mx) * (y - my)
               for x, y in zip(a_lat_list, delta_list)) / denom


def make_accel_trace(a=4.0, dt=1.0 / 60.0, t_end=12.0):
    times, speeds = [], []
    t, v = 0.0, 0.0
    while t <= t_end:
        times.append(t)
        speeds.append(v)
        v += a * dt
        t += dt
    return times, speeds


class TestKmh(unittest.TestCase):
    def test_straight(self):
        self.assertAlmostEqual(kmh(V_100), 100.0, places=6)

    def test_combined(self):
        self.assertAlmostEqual(kmh(3.0, 4.0), 18.0, places=9)


class TestAccelTimes(unittest.TestCase):
    def test_t_0_100_constant_accel(self):
        # a = 4 m/s^2 => t = 27.78/4 = 6.944 s (analyticky).
        times, speeds = make_accel_trace(a=4.0)
        t = time_at_threshold(times, speeds, V_100)
        self.assertAlmostEqual(t, V_100 / 4.0, delta=1.0 / 60.0)

    def test_t_0_60(self):
        times, speeds = make_accel_trace(a=5.0)
        t = time_at_threshold(times, speeds, V_60)
        self.assertAlmostEqual(t, V_60 / 5.0, delta=1.0 / 60.0)

    def test_never_reached(self):
        with self.assertRaises(ValueError):
            time_at_threshold([0.0, 1.0], [0.0, 5.0], V_100)


class TestBraking(unittest.TestCase):
    def test_constant_decel_matches_analytic(self):
        # v0 = 100 km/h, a = 8 m/s^2 => s = v0^2/16.
        v0, a, dt = V_100, 8.0, 1.0 / 240.0
        times, speeds, t, v = [0.0], [v0], 0.0, v0
        while v > 0.0:
            t += dt
            v = max(0.0, v - a * dt)
            times.append(t)
            speeds.append(v)
        s = braking_distance(times, speeds)
        self.assertAlmostEqual(s, v0 * v0 / (2 * a), delta=0.5)

    def test_mean_decel_consistency(self):
        # §6.3 bod 2: mean_decel = v0^2/(2s) v ±5 %.
        v0, a = V_100, 8.0
        s = v0 * v0 / (2 * a)
        self.assertAlmostEqual(v0 * v0 / (2 * s), a, delta=0.05 * a)


class TestVmax(unittest.TestCase):
    def test_settled(self):
        speeds = [55.0 + 0.01 * ((i % 2) * 2 - 1) for i in range(10)]
        mean, flag = settled_vmax(speeds)
        self.assertFalse(flag)
        self.assertAlmostEqual(mean, 55.0, delta=0.05)

    def test_not_settled(self):
        speeds = [50.0, 52.0, 54.0, 56.0, 58.0]
        _, flag = settled_vmax(speeds)
        self.assertTrue(flag)


class TestSlipAndBeta(unittest.TestCase):
    def test_no_slip(self):
        self.assertAlmostEqual(slip_ratio(30.0, 0.33, 9.9), 0.0, places=9)

    def test_driven_slip_positive(self):
        k = slip_ratio(40.0, 0.33, 9.9)
        self.assertGreater(k, 0.2)  # |k| > 0.2 = prokluz (§4.2)

    def test_launch_epsilon_guard(self):
        # Pri rozjezdu (v ~ 0) deleni chraneno eps = 1.0, zadny ZeroDivision.
        k = slip_ratio(5.0, 0.33, 0.0)
        self.assertTrue(math.isfinite(k))

    def test_beta_invalid_at_standstill(self):
        self.assertIsNone(sideslip_beta(0.5, 0.2))

    def test_beta_zero_straight(self):
        self.assertAlmostEqual(sideslip_beta(20.0, 0.0), 0.0, places=9)


class TestUndersteerGradient(unittest.TestCase):
    def test_understeer_positive(self):
        k = understeer_gradient([2.0, 4.0, 6.0], [0.05, 0.08, 0.12])
        self.assertIsNotNone(k)
        assert k is not None
        self.assertGreater(k, 0.0)

    def test_oversteer_negative(self):
        k = understeer_gradient([2.0, 4.0, 6.0], [0.10, 0.08, 0.05])
        self.assertIsNotNone(k)
        assert k is not None
        self.assertLess(k, 0.0)

    def test_needs_three_points(self):
        self.assertIsNone(understeer_gradient([2.0, 4.0], [0.05, 0.08]))


class TestRms(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(rms([0.0, 0.0, 0.0]), 0.0)

    def test_known(self):
        self.assertAlmostEqual(rms([3.0, 4.0]), math.sqrt(12.5), places=9)


if __name__ == "__main__":
    unittest.main()

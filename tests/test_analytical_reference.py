"""Analyticke referencni testy, uroven MATH (TESTING-OPTIMIZATION §6.1, §8.4).

Overuji vzorce proti uzavrenym analytickym resenim. Ciste stdlib,
bez zavislosti na modulech vlny 1 — vzdy spustitelne.

Zdroje: TESTING-OPTIMIZATION §4.2 (definice metrik), §6.3 (sanity).
"""
import math
import unittest

G = 9.81


def free_fall_distance(t, g=G, v0=0.0, s0=0.0):
    return s0 + v0 * t + 0.5 * g * t * t


def free_fall_velocity(t, g=G, v0=0.0):
    return v0 + g * t


def uniform_motion_position(x0, v, t):
    return x0 + v * t


def steady_turn_speed(a_lat, radius):
    """Ustalena zatacka: a_lat = v^2 / R  =>  v = sqrt(a_lat * R)."""
    if a_lat < 0 or radius <= 0:
        raise ValueError("a_lat >= 0 a R > 0")
    return math.sqrt(a_lat * radius)


def brake_distance(v0, decel):
    """Draha zastaveni pri konstantnim zpomaleni: s = v0^2 / (2*a)."""
    if decel <= 0:
        raise ValueError("decel > 0")
    return v0 * v0 / (2.0 * decel)


class TestFreeFall(unittest.TestCase):
    """Volny pad: s = 1/2 g t^2, v = g t."""

    def test_distance_1s(self):
        self.assertAlmostEqual(free_fall_distance(1.0), 0.5 * G, places=9)

    def test_distance_2s(self):
        self.assertAlmostEqual(free_fall_distance(2.0), 2.0 * G, places=9)

    def test_velocity(self):
        self.assertAlmostEqual(free_fall_velocity(3.0), 3.0 * G, places=9)

    def test_energy_conservation_fall(self):
        # m=1: E = 1/2 v^2 - g*h vuci startu; pri padu o s musi platit
        # 1/2 v^2 = g*s (nezavislost na hmotnosti).
        m, h = 1200.0, 10.0
        t = math.sqrt(2.0 * h / G)
        v = free_fall_velocity(t)
        kinetic = 0.5 * m * v * v
        potential_loss = m * G * h
        self.assertAlmostEqual(kinetic / potential_loss, 1.0, places=9)

    def test_with_initial_velocity(self):
        t = 2.0
        self.assertAlmostEqual(free_fall_distance(t, v0=5.0),
                               5.0 * t + 0.5 * G * t * t, places=9)


class TestUniformMotion(unittest.TestCase):
    """Rovnomerny pohyb: x = x0 + v*t."""

    def test_position(self):
        self.assertAlmostEqual(uniform_motion_position(0.0, 27.78, 10.0),
                               277.8, places=6)

    def test_zero_velocity(self):
        self.assertAlmostEqual(uniform_motion_position(5.0, 0.0, 100.0),
                               5.0, places=9)

    def test_negative_velocity(self):
        self.assertAlmostEqual(uniform_motion_position(100.0, -20.0, 5.0),
                               0.0, places=9)

    def test_100kmh_ms_conversion(self):
        # 100 km/h = 27.777... m/s (konvence dle §4.2: v_long >= 27.78 m/s)
        self.assertAlmostEqual(100.0 / 3.6, 27.7777777777, places=6)


class TestSteadyTurn(unittest.TestCase):
    """Ustalena zatacka: v = sqrt(a_lat * R).

    Poznamka ke kontraktu: zadani uvadi 'v = lateral-a*R', coz je
    rozmerove spatne (m^2/s^2 neni rychlost). Spravny vztah z
    a_lat = v^2/R je v = sqrt(a_lat*R); testuje se spravna fyzika.
    """

    def test_r30_a8(self):
        # R = 30 m (navrh S4, §3), a_lat = 8 m/s^2
        v = steady_turn_speed(8.0, 30.0)
        self.assertAlmostEqual(v, math.sqrt(240.0), places=9)
        # zpetna vazba: v^2 / R = a_lat
        self.assertAlmostEqual(v * v / 30.0, 8.0, places=9)

    def test_zero_lateral_accel(self):
        self.assertEqual(steady_turn_speed(0.0, 30.0), 0.0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            steady_turn_speed(-1.0, 30.0)
        with self.assertRaises(ValueError):
            steady_turn_speed(5.0, 0.0)

    def test_typical_corner_speed_range(self):
        # Pri 1g (9.81) na R=30 m: v ~ 17.2 m/s ~ 61.8 km/h — ocekavany rad S4.
        v = steady_turn_speed(9.81, 30.0)
        self.assertGreater(v, 15.0)
        self.assertLess(v, 20.0)


class TestBrakeDistance(unittest.TestCase):
    """Kontrola: s = v0^2/(2a) a mean_decel = v0^2/(2s) (§4.2, §6.3 bod 2)."""

    def test_100_0_typical(self):
        v0 = 100.0 / 3.6
        s = brake_distance(v0, 8.0)
        self.assertAlmostEqual(s, v0 * v0 / 16.0, places=9)
        # zpetna konzistence dle §6.3: mean_decel ≈ v0^2/(2s)
        self.assertAlmostEqual(v0 * v0 / (2.0 * s), 8.0, places=9)

    def test_order_of_magnitude(self):
        # §6.3: brake_distance_100_0 v (10, 300) m
        v0 = 100.0 / 3.6
        for a in (4.0, 6.0, 8.0, 10.0):
            s = brake_distance(v0, a)
            self.assertGreater(s, 10.0)
            self.assertLess(s, 300.0)


if __name__ == "__main__":
    unittest.main()

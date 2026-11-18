"""F7.2 ServerSteer — numericky mirror A-Chassis 'New' rizeni (P0).

Overuje MATEMATIKU portu (Drive r. 325-326, 344-359, 365-376) v Pythonu:
ocekavane uhly 31.2/28.08°, znamenka, Ackermann asymetrii, rampu a sDecay.
Zive hodnoty Tune (ServerStorage template, overeno ctenim 2026-11-18):
SteeringType='New', SteerRatio=15, LockToLock=2.6, Ackerman=0.9,
SteerSpeed=0.05, ReturnSpeed=0.1, SteerDecay=330, MinSteer=10, SteerInner=45.

Neni dukazem runtime chovani v Robloxu — ten podava SelfTestSandbox v T0.
"""

import math
import unittest

TUNE = {
    "SteeringType": "New",
    "SteerSpeed": 0.05,
    "ReturnSpeed": 0.1,
    "SteerDecay": 330,
    "MinSteer": 10,
    "SteerRatio": 15,
    "LockToLock": 2.6,
    "Ackerman": 0.9,
    "SteerInner": 45,
}


def drive_consts(t):
    outer = (t["LockToLock"] * 180) / t["SteerRatio"]
    inner = min(outer - (outer * (1 - t["Ackerman"])), outer * 1.2)
    return outer, inner


def ramp(sc, cmd, ticks, t):
    """Doslovny Drive 344-356 (jednotky prikazu -1..1)."""
    if sc < cmd:
        sc = min(cmd, sc + t["ReturnSpeed"] * ticks) if sc < 0 else min(cmd, sc + t["SteerSpeed"] * ticks)
    else:
        sc = max(cmd, sc - t["ReturnSpeed"] * ticks) if sc > 0 else max(cmd, sc - t["SteerSpeed"] * ticks)
    return sc


def sdec(v, t):
    return 1 - min(v / t["SteerDecay"], 1 - t["MinSteer"] / 100)


def wheel_deg(sc, s, outer, inner, sd):
    """Doslovny Drive 365-376: stupnova cisla, prevod az pri zapisu.
    Vraci STUPNE (miri k CFrame pres math.rad); znamenko dle Drive."""
    if s == "F":
        return -(sc * TUNE["SteerInner"] * sd)
    if s == "FL":
        return -(sc * (outer if sc >= 0 else inner) * sd)
    return -(sc * (inner if sc >= 0 else outer) * sd)


class TestServerSteerMath(unittest.TestCase):
    def test_konstanty(self):
        outer, inner = drive_consts(TUNE)
        self.assertAlmostEqual(outer, 31.2, places=6)
        self.assertAlmostEqual(inner, 28.08, places=6)

    def test_steer_nula(self):
        outer, inner = drive_consts(TUNE)
        for s in ("F", "FL", "FR"):
            self.assertAlmostEqual(wheel_deg(0.0, s, outer, inner, 1.0), 0.0, places=9)

    def test_steer_plus1_vnejsi_vnitrni(self):
        outer, inner = drive_consts(TUNE)
        self.assertAlmostEqual(wheel_deg(1.0, "FL", outer, inner, 1.0), -31.2, places=6)
        self.assertAlmostEqual(wheel_deg(1.0, "FR", outer, inner, 1.0), -28.08, places=6)

    def test_steer_minus1_ackermann_symetrie(self):
        outer, inner = drive_consts(TUNE)
        self.assertAlmostEqual(wheel_deg(-1.0, "FL", outer, inner, 1.0), 28.08, places=6)
        self.assertAlmostEqual(wheel_deg(-1.0, "FR", outer, inner, 1.0), 31.2, places=6)
        # asymetrie se preklopi se znamenkem (vnitrni kolo vzdy vetsi rejd)
        self.assertGreater(abs(wheel_deg(-1.0, "FR", outer, inner, 1.0)),
                           abs(wheel_deg(-1.0, "FL", outer, inner, 1.0)))

    def test_rampa_ticku(self):
        sc, n = 0.0, 0
        while sc < 1.0 and n < 1000:
            sc = ramp(sc, 1.0, 1.0, TUNE)
            n += 1
        self.assertEqual(n, 20)  # 1/0.05
        n = 0
        while sc > 0.0 and n < 1000:
            sc = ramp(sc, 0.0, 1.0, TUNE)
            n += 1
        # 1/0.1 = 10; float-prach muze pridat 1 tick (stejne v Luau) — 10..11 OK
        self.assertGreaterEqual(n, 10)
        self.assertLessEqual(n, 11)

    def test_dt_strop(self):
        # ticks=min(dt*60,3): velky vypadek max 3/60s prispevku
        self.assertEqual(min(5.0 * 60, 3), 3)
        self.assertAlmostEqual(min((1 / 60) * 60, 3), 1.0)

    def test_sdecay(self):
        self.assertAlmostEqual(sdec(0, TUNE), 1.0)
        self.assertAlmostEqual(sdec(165, TUNE), 0.5)
        self.assertAlmostEqual(sdec(100000, TUNE), 0.1)  # MinSteer podlaha


if __name__ == "__main__":
    unittest.main()

# engine.py — spalovací motor: momentová křivka, výkon, redline, volnoběh.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: křivka [(rpm, Nm)], otáčky [rpm], plyn [0..1], redline/idle [rpm],
#           derate [0..1]. Výstupy: moment [Nm], výkon [W].
# PŘEDPOKLADY
#   - Moment roste s plynem lineárně; křivka se lineárně interpoluje mezi body.
#   - Výkon P = M * omega (omega v rad/s).
# LIMITY
#   - Žádná dynamika plnění, teplota, klepání; rev-gate je ostrý řez (zjednodušení).
#   - Volnoběh drží otáčky jen jako dolní mez výstupu, ne regulátor.
# ZDROJE (principy):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Powertrain/Engine.luau
#     (struktura: hradla rev/fuel, P = tau*omega; plochou křivku NEpřebíráme,
#     nahrazujeme skutečnou mapou tau(omega)).
# FLAG source: "measured" / "estimated" / "simplified".

"""Motor: interpolace momentové křivky, výkon, redline, volnoběh."""

from __future__ import annotations

import math

SOURCES = {
    "torque_curve": "measured",     # body z brzdy/OEM kotvy; jinak estimated
    "redline_rpm": "measured",      # tovární údaj
    "idle_rpm": "estimated",        # často odhad z manuálu
    "throttle_linearity": "simplified",  # lineární vliv plynu
    "rev_gate_cut": "simplified",        # ostrý řez místo omezovače
}

RPM_TO_RADS = 2.0 * math.pi / 60.0


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def rpm_to_rad_s(rpm: float) -> float:
    """[rpm] -> [rad/s]."""
    return _finite(rpm, "rpm") * RPM_TO_RADS


def rad_s_to_rpm(omega: float) -> float:
    """[rad/s] -> [rpm]."""
    return _finite(omega, "omega") / RPM_TO_RADS


def validate_curve(curve: list) -> list:
    """Kontrola křivky [(rpm, Nm)]: min. 2 body, rostoucí rpm, Nm >= 0, konečná čísla.
    Vrací seřazenou kopii."""
    if len(curve) < 2:
        raise ValueError("krivka potrebuje aspon 2 body")
    pts = []
    for i, pt in enumerate(curve):
        if len(pt) != 2:
            raise ValueError(f"bod {i} musi mit (rpm, Nm)")
        rpm = _finite(pt[0], f"curve[{i}].rpm")
        nm = _finite(pt[1], f"curve[{i}].Nm")
        if nm < 0.0 or rpm < 0.0:
            raise ValueError("rpm i Nm musi byt >= 0")
        pts.append((rpm, nm))
    pts.sort(key=lambda p: p[0])
    for i in range(1, len(pts)):
        if pts[i][0] <= pts[i - 1][0]:
            raise ValueError("rpm musi byt ostre rostouci")
    return pts


def torque_at_rpm(curve: list, rpm: float) -> float:
    """Lineární interpolace křivky. Mimo rozsah drží krajní hodnotu (clamp).
    Vstup: [(rpm, Nm)], [rpm]. Výstup: [Nm] při plném plynu."""
    pts = validate_curve(curve)
    rpm = _finite(rpm, "rpm")
    if rpm <= pts[0][0]:
        return pts[0][1]
    if rpm >= pts[-1][0]:
        return pts[-1][1]
    for (r0, t0), (r1, t1) in zip(pts, pts[1:]):
        if r0 <= rpm <= r1:
            f = (rpm - r0) / (r1 - r0)
            return t0 + f * (t1 - t0)
    raise AssertionError("nedostupny stav interpolace")


def engine_output(curve: list, rpm: float, throttle: float, redline_rpm: float,
                  idle_rpm: float = 800.0, derate: float = 1.0,
                  fuel_ok: bool = True) -> dict:
    """Výstup motoru. Vstup: křivka, otáčky [rpm], plyn [0..1], redline/idle [rpm],
    derate [0..1] (chlazení/poškození), palivo bool. Výstup: {"torque_nm", "power_w", "rpm_out"}.
    rpm_out drží dolní mez volnoběhu; nad redline je moment 0 (rev-gate)."""
    rpm = _finite(rpm, "rpm")
    thr = _finite(throttle, "throttle")
    red = _finite(redline_rpm, "redline_rpm")
    idle = _finite(idle_rpm, "idle_rpm")
    der = _finite(derate, "derate")
    if not 0.0 <= thr <= 1.0:
        raise ValueError("throttle musi byt v [0, 1]")
    if not 0.0 <= der <= 1.0:
        raise ValueError("derate musi byt v [0, 1]")
    if red <= 0.0 or idle < 0.0 or idle >= red:
        raise ValueError("nevhodne idle/redline")
    fuel_gate = 1.0 if fuel_ok else 0.0
    rev_gate = 1.0 if rpm < red else 0.0
    base = torque_at_rpm(curve, max(rpm, 0.0))
    torque = thr * base * der * rev_gate * fuel_gate
    omega = max(rpm, 0.0) * RPM_TO_RADS
    return {
        "torque_nm": torque,
        "power_w": torque * omega,  # P = M * omega
        "power_kw": torque * omega / 1000.0,
        "rpm_out": max(rpm, idle),
        "at_redline": rpm >= red,
    }


def curve_from_config(peak_torque_nm: float, peak_power_kw: float,
                      redline_rpm: float, idle_rpm: float = 800.0) -> dict:
    """Náhradní 3-bodová křivka z VehicleConfig.parameters.engine
    ({peak_torque_nm, peak_power_kw} dle ARCHITECTURE §3.3), pokud není měřená křivka.
    Vrchol momentu u 0.55*redline, vrchol výkonu u 0.93*redline. FLAG: estimated."""
    pt = _finite(peak_torque_nm, "peak_torque_nm")
    pp = _finite(peak_power_kw, "peak_power_kw")
    if pt <= 0.0 or pp <= 0.0:
        raise ValueError("peak hodnoty musi byt > 0")
    rpm_t = 0.55 * redline_rpm
    rpm_p = 0.93 * redline_rpm
    t_at_p = pp * 1000.0 / (rpm_p * RPM_TO_RADS)  # M = P / omega
    t_at_p = min(t_at_p, pt)
    return {
        "curve": [(idle_rpm, 0.6 * pt), (rpm_t, pt), (rpm_p, t_at_p)],
        "source": "estimated",
    }

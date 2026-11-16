# gearbox.py — převodovka: poměry, řazení, stálý převod.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: moment [Nm], úhlová rychlost [rad/s], poměry [-], stálý převod [-],
#           účinnost [-], stupeň (0=neutrál, >0 vpřed, -1 zpátečka), otáčky [rpm].
#   Výstupy: moment [Nm], otáčky [rad/s], stupeň, událost řazení.
# PŘEDPOKLADY
#   - Bezestavový ideální převod; invariant M_out*w_out = M_in*w_in*eff.
#   - Stálý převod (final drive) žije právě zde (dle Gearbox.luau).
#   - Řazení s hysterezí prahů up/down; okamžité v jednom kroku (čas řazení
#     řeší volající přes shift_time_s jako výpadek momentu, viz limit).
# LIMITY
#   - Žádná setrvačnost kol/synchronizace, žádný prokluz spojky (spojka = stub).
#   - Automat bez horního stropu stupně — strop drží volající/konfig.
# ZDROJE (principy):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Powertrain/Gearbox.luau
#     (tau_out = sign*tau_in*ratio*finalDrive*eff; gear 0 -> (0,0); R sign=-1)
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Powertrain/Transmission.luau
#     (prahy + hystereze + R-interlock; clutch/shiftTimer legacy).
# FLAG source: "measured" / "estimated" / "simplified".

"""Převodovka: ideální převod + logika řazení s hysterezí."""

from __future__ import annotations

import math

SOURCES = {
    "gear_ratios": "measured",      # OEM převody (factory)
    "final_drive": "measured",      # stálý převod (factory)
    "efficiency": "estimated",      # účinnost ~0.9-0.95, typicky odhad
    "shift_rpm": "estimated",       # práh řazení z VehicleConfig
    "shift_time_s": "estimated",    # simulační parametr výpadku momentu
    "ideal_shift": "simplified",    # okamžité řazení bez synchronizace
}


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def validate_ratios(gears: list, final_drive: float) -> tuple:
    """Kontrola poměrů: >0, konečné; final_drive > 0. Vrací (list, float)."""
    if not gears:
        raise ValueError("gears nesmi byt prazdne")
    out = []
    for i, r in enumerate(gears):
        r = _finite(r, f"gears[{i}]")
        if r <= 0.0:
            raise ValueError("prevod musi byt > 0")
        out.append(r)
    fd = _finite(final_drive, "final_drive")
    if fd <= 0.0:
        raise ValueError("final_drive musi byt > 0")
    return out, fd


def gear_output(torque_in_nm: float, omega_in_rads: float, gear: int,
                gears: list, final_drive: float, efficiency: float = 0.95,
                reverse_ratio: float | None = None) -> dict:
    """Ideální převod jednoho stupně. gear: 0=neutrál, 1..N vpřed, -1 zpátečka.
    Vrací {"torque_out_nm", "omega_out_rads", "total_ratio"}."""
    tin = _finite(torque_in_nm, "torque_in_nm")
    win = _finite(omega_in_rads, "omega_in_rads")
    eff = _finite(efficiency, "efficiency")
    if not 0.0 < eff <= 1.0:
        raise ValueError("efficiency musi byt v (0, 1]")
    ratios, fd = validate_ratios(gears, final_drive)
    if gear == 0:
        return {"torque_out_nm": 0.0, "omega_out_rads": 0.0, "total_ratio": 0.0}
    if gear == -1:
        if reverse_ratio is None:
            raise ValueError("zpatecka vyzaduje reverse_ratio")
        rr = _finite(reverse_ratio, "reverse_ratio")
        if rr <= 0.0:
            raise ValueError("reverse_ratio musi byt > 0")
        total = rr * fd
        return {"torque_out_nm": -tin * total * eff,
                "omega_out_rads": -win / total, "total_ratio": total}
    if not 1 <= gear <= len(ratios):
        raise ValueError(f"gear mimo rozsah 1..{len(ratios)}")
    total = ratios[gear - 1] * fd
    return {"torque_out_nm": tin * total * eff,
            "omega_out_rads": win / total, "total_ratio": total}


def update_gear(current_gear: int, rpm: float, throttle: float, vehicle_speed_mps: float,
                gears: list, shift_up_rpm: float, shift_down_rpm: float,
                reverse_max_speed_mps: float = 3.0, want_reverse: bool = False) -> dict:
    """Logika řazení s hysterezí (čistá, bez mutace stavu).
    Vrací {"gear", "shift_event"} kde shift_event je None/"up"/"down"/"to_reverse"/"from_reverse".
    R-interlock: do zpátečky jen při |v| < reverse_max_speed_mps."""
    rpm = _finite(rpm, "rpm")
    _finite(throttle, "throttle")
    v = _finite(vehicle_speed_mps, "vehicle_speed_mps")
    up = _finite(shift_up_rpm, "shift_up_rpm")
    dn = _finite(shift_down_rpm, "shift_down_rpm")
    if up <= dn:
        raise ValueError("shift_up_rpm musi byt > shift_down_rpm")
    n = len(gears)
    g = current_gear
    if g == -1:
        if not want_reverse:
            return {"gear": 1, "shift_event": "from_reverse"}
        return {"gear": -1, "shift_event": None}
    if not 1 <= g <= n:
        raise ValueError(f"current_gear mimo rozsah 1..{n}")
    if want_reverse and abs(v) < reverse_max_speed_mps:
        return {"gear": -1, "shift_event": "to_reverse"}
    if rpm >= up and g < n:
        return {"gear": g + 1, "shift_event": "up"}
    if rpm <= dn and g > 1:
        return {"gear": g - 1, "shift_event": "down"}
    return {"gear": g, "shift_event": None}


def total_ratio_for_gear(gear: int, gears: list, final_drive: float,
                         reverse_ratio: float | None = None) -> float:
    """Celkový poměr (převod * final_drive) pro sondu otáček motoru."""
    out = gear_output(1.0, 1.0, gear, gears, final_drive, 1.0, reverse_ratio)
    return abs(out["total_ratio"])

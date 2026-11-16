# steering.py — řízení: rate-limit + ořez rychlostí + Ackermann.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: povel [−1..1], max. úhel [rad], rychlost [m/s], referenční rychlost [m/s],
#           max. rychlost natáčení [rad/s], krok [s], rozvor/rozchod [m].
#   Výstupy: úhly delta / deltaL / deltaR [rad] + nový stav [rad].
# PŘEDPOKLADY
#   - Stav se nemutuje; geometrie čísly parametrem; |v| symetrie (bez rozdílu zpátečky).
#   - Ackermann z poloměru R = L/tan|δ|: inner = atan(L/(R−T/2)), outer = atan(L/(R+T/2)).
# LIMITY
#   - Čistá kinematika záměru: bez poddajnosti, bez momentu ve volantu, bez zpoždění
#     aktuátoru; ořez 1/(1+r²) je heuristika.
# ZDROJE (principy + vzorce):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Controls/Steering.luau ř. 64–88
#     (target = clamp·maxAngle/(1+(|v|/vref)²); rate-limit δnew = δold + clamp(target−δold,
#     ±maxRate·dt); Ackermann inner/outer; validate maxAngle ∈ (0,1] rad).
# FLAG source: "measured" / "estimated" / "simplified".

"""Řízení: rychlostní ořez, rate-limit, Ackermann."""

from __future__ import annotations

import math

SOURCES = {
    "max_angle": "measured",        # z modelu řízení / rešerše
    "wheelbase_track": "measured",  # geometrie modelu
    "vref": "estimated",            # referenční rychlost ořezu, kalibrační
    "max_rate": "estimated",        # rychlost natáčení, kalibrační
    "speed_cut": "simplified",      # heuristika 1/(1+r²)
    "no_compliance": "simplified",  # bez poddajnosti řízení
}

MAX_ANGLE_RAD = 1.0  # validační strop dle Steering.luau


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def target_angle(steer_input: float, max_angle_rad: float, speed_mps: float,
                 vref_mps: float = 20.0) -> float:
    """Záměr: clamp(input,−1,1)·maxAngle / (1 + (|v|/vref)²). Vstup: [−], [rad], [m/s].
    Výstup: [rad]."""
    u = _clamp(_finite(steer_input, "steer_input"), -1.0, 1.0)
    mx = _finite(max_angle_rad, "max_angle_rad")
    v = _finite(speed_mps, "speed_mps")
    vr = _finite(vref_mps, "vref_mps")
    if not 0.0 < mx <= MAX_ANGLE_RAD:
        raise ValueError(f"max_angle_rad musi byt v (0, {MAX_ANGLE_RAD}]")
    if vr <= 0.0:
        raise ValueError("vref_mps musi byt > 0")
    r = abs(v) / vr
    return u * mx / (1.0 + r * r)


def rate_limit(current_rad: float, target_rad: float, max_rate_rads: float,
               dt_s: float) -> float:
    """δnew = δold + clamp(target − δold, ±maxRate·dt). Vstup: [rad], [rad/s], [s]."""
    cur = _finite(current_rad, "current_rad")
    tgt = _finite(target_rad, "target_rad")
    mr = _finite(max_rate_rads, "max_rate_rads")
    dt = _finite(dt_s, "dt_s")
    if mr <= 0.0 or dt <= 0.0:
        raise ValueError("max_rate_rads a dt_s musi byt > 0")
    d = _clamp(tgt - cur, -mr * dt, mr * dt)
    return cur + d


def ackermann(delta_rad: float, wheelbase_m: float, track_m: float) -> dict:
    """Ackermann L/P. R = L/tan|δ|; inner = atan(L/(R−T/2)), outer = atan(L/(R+T/2)).
    Znaménko dědí stranu: δ > 0 = vlevo → inner je LEFT. Vrací {"left_rad","right_rad"}."""
    d = _finite(delta_rad, "delta_rad")
    L = _finite(wheelbase_m, "wheelbase_m")
    T = _finite(track_m, "track_m")
    if L <= 0.0 or T <= 0.0:
        raise ValueError("wheelbase_m a track_m musi byt > 0")
    if abs(d) < 1e-9:
        return {"left_rad": 0.0, "right_rad": 0.0}
    R = L / math.tan(abs(d))
    inner = math.atan(L / (R - T / 2.0))
    outer = math.atan(L / (R + T / 2.0))
    if d > 0.0:  # vlevo: levé je vnitřní
        return {"left_rad": inner, "right_rad": outer}
    return {"left_rad": -outer, "right_rad": -inner}


def compute(steer_input: float, current_rad: float, speed_mps: float, dt_s: float,
            wheelbase_m: float, track_m: float, max_angle_rad: float,
            vref_mps: float = 20.0, max_rate_rads: float = 3.0) -> dict:
    """Celý krok řízení v jednom volání. Vrací {"delta", "delta_left", "delta_right",
    "state"} [rad]; state = nová δ k předání do dalšího kroku (bez mutace vstupu)."""
    tgt = target_angle(steer_input, max_angle_rad, speed_mps, vref_mps)
    new = rate_limit(current_rad, tgt, max_rate_rads, dt_s)
    ack = ackermann(new, wheelbase_m, track_m)
    return {"delta": new, "delta_left": ack["left_rad"],
            "delta_right": ack["right_rad"], "state": new}

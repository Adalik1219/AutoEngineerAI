# brakes.py — brzdy: provozní moment, bias, ruční brzda, zjednodušené ABS.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: pedál [0..1], max. moment [Nm], bias předku [0..1], skluz [-].
#   Výstupy: brzdné momenty na kola [Nm], skluz [-], ABS flag.
# PŘEDPOKLADY
#   - Provozní okruh: předek = p*Tmax*bias, zadek = p*Tmax*(1−bias), děleno na 2 kola.
#   - Ruční brzda: nezávislý zadní okruh (přičítá se k zadku).
#   - Brzdný moment působí proti směru otáčení (řeší Wheel/integrátor znaménkem).
# LIMITY
#   - ABS je zjednodušené škrcení požadavku nad prahem skluzu; žádná hydraulika,
#     žádné zpoždění modulátoru, žádný zásah do řízení.
# ZDROJE (principy):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Controls/Brakes.luau
#     (service split; handbrake zadní okruh; brakeSlip = clamp(1 − ωR/vx, 0, 1),
#     |vx| < eps → 0; ABS záměrně odstraněno → zde jen zjednodušená obdoba).
# FLAG source: "measured" / "estimated" / "simplified".

"""Brzdy: rozdělení momentu, ruční brzda, skluz, zjednodušené ABS."""

from __future__ import annotations

import math

SOURCES = {
    "max_torque_nm": "estimated",   # z průměru kotoučů / měření; často odhad
    "bias_front": "estimated",      # typicky ~0.6–0.65, kalibrační
    "abs_threshold": "simplified",  # práh + škrcení je náhražka modulátoru
}

WHEELS = ("FL", "FR", "RL", "RR")


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def service_brake(pedal: float, max_torque_nm: float, bias_front: float) -> dict:
    """Provozní brzda na 4 kola. Vstup: pedál [0..1], Tmax [Nm] (součet všech kol),
    bias [0..1] podíl předku. Výstup: {FL, FR, RL, RR} [Nm] (nezáporné velikosti)."""
    p = _finite(pedal, "pedal")
    tmax = _finite(max_torque_nm, "max_torque_nm")
    bias = _finite(bias_front, "bias_front")
    if not 0.0 <= p <= 1.0:
        raise ValueError("pedal musi byt v [0, 1]")
    if tmax < 0.0:
        raise ValueError("max_torque_nm nesmi byt zaporne")
    if not 0.0 <= bias <= 1.0:
        raise ValueError("bias_front musi byt v [0, 1]")
    front_each = p * tmax * bias / 2.0
    rear_each = p * tmax * (1.0 - bias) / 2.0
    return {"FL": front_each, "FR": front_each, "RL": rear_each, "RR": rear_each}


def handbrake(pull: float, max_rear_torque_nm: float) -> dict:
    """Ruční brzda: jen zadní náprava. Vstup: [0..1], Tmax zadku [Nm].
    Výstup: {RL, RR} [Nm]."""
    p = _finite(pull, "pull")
    tmax = _finite(max_rear_torque_nm, "max_rear_torque_nm")
    if not 0.0 <= p <= 1.0:
        raise ValueError("pull musi byt v [0, 1]")
    if tmax < 0.0:
        raise ValueError("max_rear_torque_nm nesmi byt zaporne")
    each = p * tmax / 2.0
    return {"RL": each, "RR": each}


def brake_slip(omega_rads: float, radius_m: float, vx_mps: float,
               eps_mps: float = 0.5) -> float:
    """Brzdný skluz: clamp(1 − ωR/vx, 0, 1); |vx| < eps → 0. Vstup: [rad/s], [m], [m/s]."""
    w = _finite(omega_rads, "omega_rads")
    r = _finite(radius_m, "radius_m")
    vx = _finite(vx_mps, "vx_mps")
    eps = _finite(eps_mps, "eps_mps")
    if r <= 0.0 or eps <= 0.0:
        raise ValueError("radius_m a eps_mps musi byt > 0")
    if abs(vx) < eps:
        return 0.0
    return _clamp01(1.0 - w * r / vx)


def abs_modulate(requested_nm: float, slip: float, threshold: float = 0.2) -> dict:
    """Zjednodušené ABS: pod prahem propouští plný požadavek, nad prahem škrtí
    úměrně překročení (min. 30 % požadavku). Vstup: [Nm], [-], [-].
    Výstup: {"torque_nm", "abs_active"}."""
    req = _finite(requested_nm, "requested_nm")
    sl = _finite(slip, "slip")
    th = _finite(threshold, "threshold")
    if req < 0.0:
        raise ValueError("requested_nm nesmi byt zaporne")
    if not 0.0 < th < 1.0:
        raise ValueError("threshold musi byt v (0, 1)")
    if sl <= th:
        return {"torque_nm": req, "abs_active": False}
    over = (sl - th) / (1.0 - th)
    scale = max(0.3, 1.0 - over)
    return {"torque_nm": req * scale, "abs_active": True}

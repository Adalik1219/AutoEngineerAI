# aero.py — aerodynamika: odpor vzduchu a přítlak.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: rychlost [m/s], hustota [kg/m^3], Cx*S / Cl*S [m^2], podíl předku [-].
#   Výstupy: síly [N], ztrátový výkon [W].
# PŘEDPOKLADY
#   - ½·ρ·v²·plocha; odpor proti směru pohybu (vrací nezápornou velikost);
#     přítlak kolmo k vozovce (+z je vzhůru → přítlak záporný příspěvek Fz).
#   - Rozdělení přítlaku předek/zadek podílem (CoP zjednodušeně číslem).
# LIMITY
#   - Žádný vliv stáčení/náklonu, země, ani kompletní mapa CoP; hustota konstantní.
# ZDROJE: ve zdroji je Aerodynamics STUB (jen validateConfig + zamýšlená matematika
#   ½ρv²CdA/ClA + CoP) — viz C:/.DATA/RobloxSimulator/game/shared/vehicle/ (Assists/
#   a Systems STUBY, §2.7 KNOWLEDGE-TRANSFER.md). Implementace je NOVÁ dle této
#   zamýšlené matematiky, nepřevzatý kód.
# FLAG source: "measured" / "estimated" / "simplified".

"""Aerodynamika: odpor ½ρv²CdA, přítlak ½ρv²ClA, ztrátový výkon."""

from __future__ import annotations

import math

RHO_AIR = 1.225  # kg/m^3, MSA při 15 °C

SOURCES = {
    "rho_air": "measured",          # standardní hustota
    "CdA": "estimated",             # Cx i plocha často null → odhad 0.85*š*v
    "ClA": "estimated",             # přítlak sériových vozů typicky odhad
    "cop_split": "simplified",      # CoP jedním číslem místo mapy
}


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def drag_force(speed_mps: float, rho: float = RHO_AIR, CdA_m2: float = 0.7) -> float:
    """Odpor: ½·ρ·v²·CdA. Vstup: [m/s], [kg/m^3], [m^2]. Výstup: velikost [N] (>= 0)."""
    v = _finite(speed_mps, "speed_mps")
    rho = _finite(rho, "rho")
    cda = _finite(CdA_m2, "CdA_m2")
    if rho <= 0.0 or cda < 0.0:
        raise ValueError("rho musi byt > 0 a CdA >= 0")
    return 0.5 * rho * v * v * cda


def downforce(speed_mps: float, rho: float = RHO_AIR, ClA_m2: float = 0.0) -> float:
    """Přítlak (kladná velikost směrem k vozovce). ½·ρ·v²·ClA. Výstup: [N] (>= 0)."""
    v = _finite(speed_mps, "speed_mps")
    rho = _finite(rho, "rho")
    cla = _finite(ClA_m2, "ClA_m2")
    if rho <= 0.0 or cla < 0.0:
        raise ValueError("rho musi byt > 0 a ClA >= 0")
    return 0.5 * rho * v * v * cla


def aero_loads(speed_mps: float, rho: float = RHO_AIR, CdA_m2: float = 0.7,
               ClA_m2: float = 0.0, front_bias: float = 0.5) -> dict:
    """Odpor + přítlak v jednom kroku. Vstup + front_bias [0..1] podíl předku.
    Výstup: {"drag_N", "downforce_N", "front_N", "rear_N", "power_loss_W"}."""
    v = _finite(speed_mps, "speed_mps")
    fb = _finite(front_bias, "front_bias")
    if not 0.0 <= fb <= 1.0:
        raise ValueError("front_bias musi byt v [0, 1]")
    drag = drag_force(v, rho, CdA_m2)
    down = downforce(v, rho, ClA_m2)
    return {"drag_N": drag,
            "downforce_N": down,
            "front_N": down * fb,
            "rear_N": down * (1.0 - fb),
            "power_loss_W": drag * abs(v)}

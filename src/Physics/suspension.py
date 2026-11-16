# suspension.py — čtvrtinový model kola: pružina + tlumič + zdvih.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: zdvih/stlačení [m], rychlost stlačení [m/s], tuhost [N/m],
#           předpětí [N], útlum bump/rebound [N*s/m], motion ratio [-], zdvih [m].
#   Výstupy: síly [N], využití zdvihu [m], flagy dorazů.
# PŘEDPOKLADY
#   - Kladné x = stlačení; kladné v = rychlost stlačení.
#   - Síla na kolo = r²*(F_pružina + F_tlumič) (virtuální práce, motion ratio).
#   - Pružina F = k*x + preload [+ dorazy]; tlumič F = bump*v (v>0) | rebound*v (v<0).
# LIMITY
#   - Algebraická mapa bez integračního kroku; hotové síly dodává volající
#     (kontakt/integrátor); drop-test/statickou rovnováhu modul neřeší.
# ZDROJE (principy):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Chassis/Suspension.luau
#     (F_kolo = r²·(F_pružina + F_tlumič); zdvih sevřen, flagy topped/bottomed)
#   - Springs (F = k·x + preload; guard stiffness < 1000 N/m = podezření na N/mm)
#   - Dampers (čistě rychlostní F = bump/rebound·v)
#   - AntiRollBar je STUB bez compute → stabilizátor řeší samostatná funkce níže
#     jako nová implementace F_arb = k·(dispL − dispR) (není převzato, je nové).
# FLAG source: "measured" / "estimated" / "simplified".

"""Čtvrtinový model: pružina, tlumič, motion ratio, zdvih, stabilizátor."""

from __future__ import annotations

import math

SOURCES = {
    "spring_stiffness": "estimated",  # tuhosti často null → odhad/kalibrace
    "damper_rates": "estimated",      # křivky tlumičů typicky neznámé
    "preload": "estimated",
    "motion_ratio": "estimated",
    "travel_m": "measured",           # zdvih z modelu/konstrukce
    "arb_stiffness": "estimated",     # nová implementace, kalibrační
    "stiffness_guard": "simplified",  # guard < 1000 N/m proti záměně N/mm
}

MIN_STIFFNESS_NPM = 1000.0  # guard: podezření na zadání v N/mm


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def spring_force(stiffness_Npm: float, compression_m: float, preload_N: float = 0.0,
                 bump_stop_k_Npm: float = 0.0, bump_gap_m: float = float("inf")) -> float:
    """Síla pružiny. F = k*x + preload; za mezerou dorazu přičte k_bump*(x − gap).
    Vstup: [N/m], [m], [N]. Výstup: [N]."""
    k = _finite(stiffness_Npm, "stiffness_Npm")
    x = _finite(compression_m, "compression_m")
    pre = _finite(preload_N, "preload_N")
    if k < MIN_STIFFNESS_NPM:
        raise ValueError(f"stiffness {k} < {MIN_STIFFNESS_NPM} N/m: podezreni na N/mm")
    f = k * x + pre
    if bump_stop_k_Npm:
        kb = _finite(bump_stop_k_Npm, "bump_stop_k_Npm")
        gap = _finite(bump_gap_m, "bump_gap_m")
        if kb < 0.0:
            raise ValueError("bump_stop_k_Npm nesmi byt zaporne")
        if x > gap:
            f += kb * (x - gap)
    return f


def damper_force(bump_Nspm: float, rebound_Nspm: float, velocity_mps: float) -> float:
    """Síla tlumiče, čistě rychlostní. v > 0 stlačení → bump*v; v < 0 → rebound*v.
    Vstup: [N*s/m], [m/s]. Výstup: [N]."""
    b = _finite(bump_Nspm, "bump_Nspm")
    r = _finite(rebound_Nspm, "rebound_Nspm")
    v = _finite(velocity_mps, "velocity_mps")
    if b < 0.0 or r < 0.0:
        raise ValueError("utlum nesmi byt zaporny")
    if v > 0.0:
        return b * v
    if v < 0.0:
        return r * v
    return 0.0


def wheel_force(spring_N: float, damper_N: float, motion_ratio: float) -> float:
    """Přepočet na kolo: F_kolo = r²·(F_pružina + F_tlumič). Vstup: [N], [-]. Výstup: [N]."""
    fs = _finite(spring_N, "spring_N")
    fd = _finite(damper_N, "damper_N")
    mr = _finite(motion_ratio, "motion_ratio")
    if not 0.0 < mr <= 2.0:
        raise ValueError("motion_ratio musi byt v (0, 2]")
    return mr * mr * (fs + fd)


def travel_check(compression_m: float, max_travel_m: float) -> dict:
    """Kontrola zdvihu. Vstup: [m], [m]. Výstup: {travel_used_m, topped_out, bottomed_out}.
    topped_out při x ≤ 0 (plné vysunutí), bottomed_out při x ≥ max (doraz)."""
    x = _finite(compression_m, "compression_m")
    mx = _finite(max_travel_m, "max_travel_m")
    if mx <= 0.0:
        raise ValueError("max_travel_m musi byt > 0")
    return {"travel_used_m": min(max(x, 0.0), mx),
            "topped_out": x <= 0.0,
            "bottomed_out": x >= mx}


def quarter_force(stiffness_Npm: float, compression_m: float, velocity_mps: float,
                  bump_Nspm: float, rebound_Nspm: float, motion_ratio: float,
                  preload_N: float = 0.0, max_travel_m: float = 0.12) -> dict:
    """Čtvrtinový model v jednom kroku (algebraický, bez integrace).
    Vrací {"wheel_force_N", "spring_N", "damper_N", "travel_used_m",
    "topped_out", "bottomed_out"}."""
    fs = spring_force(stiffness_Npm, compression_m, preload_N)
    fd = damper_force(bump_Nspm, rebound_Nspm, velocity_mps)
    fw = wheel_force(fs, fd, motion_ratio)
    t = travel_check(compression_m, max_travel_m)
    return {"wheel_force_N": fw, "spring_N": fs, "damper_N": fd, **t}


def anti_roll_bar(stiffness_Npm: float, disp_left_m: float, disp_right_m: float) -> dict:
    """Příčná vazba stabilizátoru (NOVÁ implementace, ve zdroji jen stub).
    F_arb = k·(dispL − dispR); levé kolo +F, pravé −F (přenáší zatížení dovnitř).
    Vstup: [N/m], stlačení L/P [m]. Výstup: {"left_N", "right_N"}."""
    k = _finite(stiffness_Npm, "stiffness_Npm")
    dl = _finite(disp_left_m, "disp_left_m")
    dr = _finite(disp_right_m, "disp_right_m")
    if k < 0.0:
        raise ValueError("arb stiffness nesmi byt zaporna")
    f = k * (dl - dr)
    return {"left_N": f, "right_N": -f}

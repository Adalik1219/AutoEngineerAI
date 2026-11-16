# load_transfer.py — kvazistatický přenos zatížení + statický základ per-corner.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: hmotnost [kg], a/b vzdálenosti těžiště od náprav [m], výška h [m],
#           rozvor L [m], rozchod T [m], zrychlení [m/s^2], g [m/s^2],
#           přítlak [N] + přední podíl [-], poloha CoP [m] (volitelná).
#   Výstupy: zatížení kol {FL, FR, RL, RR} [N], kontrola součtu, lifted flag.
# SOUŘADNICE: x vpřed, y vlevo, z vzhůru. aLat > 0 = zrychlení vlevo (zatíží pravá kola).
# PŘEDPOKLADY
#   - Ustálené/pomalé manévry (kvazistatika); volající ručí za konzistenci mass/g.
#   - Striktně a + b == L; gEff = g + aVert; gEff < 0 → REJECT (volný pád není statika).
#   - Laterální split náprav statickým b/L je provizorní alokace (dle zdroje).
# LIMITY
#   - Žádná setrvačnost neodpružených hmot, tlumiče, zdvih; clamp raw ≤ 0 porušuje
#     Σ = m*g (kompenzuje až VehicleDynamics); transienty musí dodat podvozek.
# ZDROJE (principy + rovnice):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Chassis/WeightTransfer.luau
#     (checkLoadSum tolerance 0,5 %; Ff=m*gEff*b/L; Δlong=m*aLong*h/L;
#     Dlat=2*m*aLat*h/T, strany ±Dlat/2; raw≤0→clamp+lifted;
#     liftedEquivalentKg_1g=max(0,−Σneg/g)).
# FLAG source: "measured" / "estimated" / "simplified".

"""Kvazistatika zatížení kol: statika + podélný/příčný přenos + aero."""

from __future__ import annotations

import math

SOURCES = {
    "mass_kg": "measured",          # vážení
    "com_position": "estimated",    # a/b/h z geometrie, pokud není měřeno
    "wheelbase_track": "measured",  # rozvor/rozchod z modelu
    "lateral_split": "simplified",  # provizorní alokační předpoklad b/L
    "quasistatic": "simplified",    # bez transientů podvozku
}

WHEELS = ("FL", "FR", "RL", "RR")


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def static_loads(mass_kg: float, a_m: float, b_m: float, wheelbase_m: float,
                 g: float = 9.81) -> dict:
    """Statické zatížení náprav. a = těžiště–přední náprava, b = těžiště–zadní [m].
    Předek = m*g*b/L, zadek = m*g*a/L; na kolo polovina. Výstup [N]."""
    m = _finite(mass_kg, "mass_kg")
    a = _finite(a_m, "a_m")
    b = _finite(b_m, "b_m")
    L = _finite(wheelbase_m, "wheelbase_m")
    g = _finite(g, "g")
    if m <= 0.0 or L <= 0.0 or g <= 0.0:
        raise ValueError("mass_kg, wheelbase_m a g musi byt > 0")
    if not math.isclose(a + b, L, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("a + b se musi rovnat rozvoru L")
    front = m * g * b / L
    rear = m * g * a / L
    return {"FL": front / 2.0, "FR": front / 2.0, "RL": rear / 2.0, "RR": rear / 2.0}


def compute_loads(mass_kg: float, a_m: float, b_m: float, h_m: float,
                  wheelbase_m: float, track_m: float,
                  a_long_mps2: float = 0.0, a_lat_mps2: float = 0.0,
                  a_vert_mps2: float = 0.0, g: float = 9.81,
                  aero_N: float = 0.0, front_aero_bias: float = 0.5) -> dict:
    """Kvazistatické zatížení všech kol. a_long > 0 = zrychlení vpřed (zatíží zadek).
    Vrací {"FL","FR","RL","RR"} [N] + "lifted" (bool) + "lifted_equiv_kg_1g" [kg]
    + "load_sum_N" pro kontrolu Σ."""
    m = _finite(mass_kg, "mass_kg")
    a = _finite(a_m, "a_m")
    b = _finite(b_m, "b_m")
    h = _finite(h_m, "h_m")
    L = _finite(wheelbase_m, "wheelbase_m")
    T = _finite(track_m, "track_m")
    aLong = _finite(a_long_mps2, "a_long_mps2")
    aLat = _finite(a_lat_mps2, "a_lat_mps2")
    aVert = _finite(a_vert_mps2, "a_vert_mps2")
    g = _finite(g, "g")
    aero = _finite(aero_N, "aero_N")
    fab = _finite(front_aero_bias, "front_aero_bias")
    if m <= 0.0 or L <= 0.0 or T <= 0.0 or g <= 0.0:
        raise ValueError("mass_kg, wheelbase_m, track_m a g musi byt > 0")
    if h < 0.0:
        raise ValueError("h_m nesmi byt zaporne")
    if not math.isclose(a + b, L, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("a + b se musi rovnat rozvoru L")
    if not 0.0 <= fab <= 1.0:
        raise ValueError("front_aero_bias musi byt v [0, 1]")
    if aero < 0.0:
        raise ValueError("aero_N nesmi byt zaporne")
    g_eff = g + aVert
    if g_eff < 0.0:
        raise ValueError("gEff < 0: volny pad neni kvazistatika (REJECT)")
    front_static = m * g_eff * b / L
    rear_static = m * g_eff * a / L
    d_long = m * aLong * h / L          # celkem z předku na zadek při aLong > 0
    d_lat = 2.0 * m * aLat * h / T      # diference L−R; aLat > 0 (vlevo) zatíží pravá kola
    front_static += aero * fab
    rear_static += aero * (1.0 - fab)
    # Laterální alokace na nápravy statickým poměrem (provizorní předpoklad).
    raw = {
        "FL": front_static / 2.0 - d_long / 2.0 - (d_lat * b / L) / 2.0,
        "FR": front_static / 2.0 - d_long / 2.0 + (d_lat * b / L) / 2.0,
        "RL": rear_static / 2.0 + d_long / 2.0 - (d_lat * a / L) / 2.0,
        "RR": rear_static / 2.0 + d_long / 2.0 + (d_lat * a / L) / 2.0,
    }
    neg = sum(v for v in raw.values() if v < 0.0)
    loads = {k: (0.0 if v <= 0.0 else v) for k, v in raw.items()}
    lifted = any(v <= 0.0 for v in raw.values())
    return {**loads,
            "lifted": lifted,
            "lifted_equiv_kg_1g": max(0.0, -neg / g),
            "load_sum_N": sum(loads.values())}


def check_load_sum(loads: dict, mass_kg: float, g: float = 9.81,
                   rel_tol: float = 0.005) -> bool:
    """Kontrola ΣFz ≈ m*g (rel. tolerance 0,5 %). Platí jen bez clamp/lift/aero/vert."""
    s = sum(_finite(loads[w], w) for w in WHEELS)
    m = _finite(mass_kg, "mass_kg")
    g = _finite(g, "g")
    return abs(s - m * g) <= rel_tol * m * g

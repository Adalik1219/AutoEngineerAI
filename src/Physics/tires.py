# tires.py — pneumatiky: slip + Magic Formula + friction circle.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: úhlová rychlost kola [rad/s], poloměr [m], rychlosti [m/s],
#           natočení [rad], svislé zatížení Fz [N], součinitel adheze mu [-],
#           koeficienty MF B/C [-].
#   Výstupy: kappa [-], alpha [rad], síly Fx (podélná, +x vpřed) / Fy (boční, +y vlevo) [N].
# SOUŘADNICE: x vpřed, y vlevo, z vzhůru, yaw kolem +z.
# PŘEDPOKLADY
#   - Rovinný kontakt; B/C/D patří povrchu; D = mu*Fz; směr výslednice se zachovává.
# LIMITY
#   - Kruh, ne elipsa; žádná load-senzitivita B/C, camber/toe, teplota,
#     opotřebení, vratný moment Mz; pád za peakem je vlastnost zvolených B/C.
# ZDROJE (principy):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Tires/TireSlip.luau ř. 58–60
#     (denom = max(|vx|, eps); kappa = (omega*R − vx)/denom; alpha = steer − atan(vy/denom))
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Tires/TireGrip.luau ř. 65–72
#     (F(s) = D*sin(C*atan(B*s)) zvlášť pro osy; friction circle; Fz ≤ 0 → (0,0))
#   POZOR: zdroj má rámec +x doprava / −z vpřed; zde přepočítáno na x vpřed / y vlevo
#   (podélná osa = x, boční osa = y). Guard TIRE_EPS_MPS = 0.5 převzat.
# FLAG source: "measured" / "estimated" / "simplified".

"""Pneumatiky: kinematika skluzu + Magic Formula + třecí kružnice."""

from __future__ import annotations

import math

TIRE_EPS_MPS = 0.5  # guard proti dělení nulou při stání/couvání (kinematický, ne fyzika)

SOURCES = {
    "mu": "estimated",           # adheze povrchu; měřená jen se zkouškou povrchu
    "mf_B_C": "estimated",       # tvarové koeficienty; kalibrační parametry
    "tire_radius": "measured",   # z designace pneu / měření
    "friction_circle": "simplified",  # kruh místo elipsy
    "no_camber_temp": "simplified",   # bez odklonu/teploty/opotřebení/Mz
}


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def compute_slip(omega_rads: float, radius_m: float, vx_mps: float,
                 vy_mps: float, steer_rad: float) -> dict:
    """Kinematika skluzu. kappa = (omega*R − vx)/max(|vx|, 0.5);
    alpha = steer − atan2(vy, max(|vx|, 0.5)).
    Vstup: [rad/s], [m], [m/s], [m/s], [rad]. Výstup: {"kappa", "alpha_rad"}."""
    w = _finite(omega_rads, "omega_rads")
    r = _finite(radius_m, "radius_m")
    vx = _finite(vx_mps, "vx_mps")
    vy = _finite(vy_mps, "vy_mps")
    st = _finite(steer_rad, "steer_rad")
    if r <= 0.0:
        raise ValueError("radius_m musi byt > 0")
    denom = max(abs(vx), TIRE_EPS_MPS)
    kappa = (w * r - vx) / denom
    alpha = st - math.atan2(vy, denom)
    return {"kappa": kappa, "alpha_rad": alpha}


def magic_formula(slip: float, B: float, C: float, D: float) -> float:
    """F(s) = D*sin(C*atan(B*s)). Vstup: skluz [-], B/C [-], D [N]. Výstup: [N]."""
    s = _finite(slip, "slip")
    B = _finite(B, "B")
    C = _finite(C, "C")
    D = _finite(D, "D")
    if B <= 0.0 or C <= 0.0:
        raise ValueError("B i C musi byt > 0")
    if D < 0.0:
        raise ValueError("D nesmi byt zaporne")
    return D * math.sin(C * math.atan(B * s))


def compute_grip(kappa: float, alpha_rad: float, fz_N: float, mu: float,
                 B_long: float = 10.0, C_long: float = 1.9,
                 B_lat: float = 10.0, C_lat: float = 1.9) -> dict:
    """Síly pneu. D = mu*Fz; MF zvlášť pro osy; sdružení třecí kružnicí
    (rho > 1 → škálování 1/rho). Fz ≤ 0 → (0, 0).
    Výstup: {"fx_N", "fy_N", "rho"}; |F| ≤ mu*Fz vždy."""
    k = _finite(kappa, "kappa")
    a = _finite(alpha_rad, "alpha_rad")
    fz = _finite(fz_N, "fz_N")
    mu = _finite(mu, "mu")
    if mu < 0.0:
        raise ValueError("mu nesmi byt zaporne")
    if fz <= 0.0:
        return {"fx_N": 0.0, "fy_N": 0.0, "rho": 0.0}
    D = mu * fz
    fx0 = magic_formula(k, B_long, C_long, D)
    fy0 = magic_formula(a, B_lat, C_lat, D)
    rho = math.hypot(fx0 / D, fy0 / D)
    if rho > 1.0:
        fx0 /= rho
        fy0 /= rho
        rho = 1.0
    return {"fx_N": fx0, "fy_N": fy0, "rho": rho}


def tire_forces(omega_rads: float, radius_m: float, vx_mps: float, vy_mps: float,
                steer_rad: float, fz_N: float, mu: float,
                B_long: float = 10.0, C_long: float = 1.9,
                B_lat: float = 10.0, C_lat: float = 1.9) -> dict:
    """Slip + grip v jednom kroku. Výstup: {kappa, alpha_rad, fx_N, fy_N, rho}."""
    s = compute_slip(omega_rads, radius_m, vx_mps, vy_mps, steer_rad)
    g = compute_grip(s["kappa"], s["alpha_rad"], fz_N, mu, B_long, C_long, B_lat, C_lat)
    return {**s, **g}

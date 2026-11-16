# api.py — tenké adaptéry src/Physics pro src/Sim/physics_backend.py.
#
# VSTUPY / VÝSTUPY / JEDNOTKY (souhrn):
#   tire_slip: vstupy vx_w [m/s], vy_w [m/s], omega [rad/s], radius_m [m],
#     steer_rad [rad]; výstupy (kappa [-], alpha_rad [rad]).
#   tire_force: vstupy kappa [-], alpha_rad [rad], fz_N [N], mu_long/mu_lat [-],
#     B_long/C_long/B_lat/C_lat [-]; výstupy (fx_N [N], fy_N [N]).
#   engine_torque: vstupy rpm [rpm], throttle [0..1], peak_torque_nm [Nm],
#     peak_power_kw [kW], idle_rpm [rpm], redline_rpm [rpm];
#     výstup torque_Nm [Nm].
#   gear_output: vstupy torque_in_Nm [Nm], ratio [-], final_drive [-],
#     efficiency (0..1] [-]; výstupy (torque_out_Nm [Nm], total_ratio [-]).
#   quasi_static_loads: vstupy mass_kg [kg], g [m/s^2], a_m/b_m/h_m/L_m [m],
#     track_m [m], a_long/a_lat [m/s^2];
#     výstupy (fz_FL, fz_FR, fz_RL, fz_RR) [N].
# SOUŘADNICE: x vpřed, y vlevo, z vzhůru (dle balíčku Physics).
# PŘEDPOKLADY: delegace na tires/engine/gearbox/load_transfer beze změny fyziky;
#   eps-guard sjednocen na TIRE_EPS_MPS = 0.5 z tires.py (kinematický guard).
# LIMITY: viz jednotlivé moduly (kruh místo elipsy; motor z náhradní křivky
#   curve_from_config = estimated; kvazistatika bez aera/vertikálu).
"""Adaptéry očekávané src/Sim/physics_backend.py nad src/Physics moduly."""

from __future__ import annotations

import math

from .tires import TIRE_EPS_MPS, compute_grip, compute_slip, magic_formula
from .engine import curve_from_config, engine_output
from .gearbox import gear_output as _gearbox_output
from .load_transfer import compute_loads

__all__ = (
    "TIRE_EPS_MPS",
    "tire_slip",
    "tire_force",
    "engine_torque",
    "gear_output",
    "quasi_static_loads",
)


def tire_slip(vx_w, vy_w, omega, radius_m, steer_rad):
    """Skluz kola. Vstupy: vx_w [m/s], vy_w [m/s], omega [rad/s],
    radius_m [m], steer_rad [rad]. Výstupy: (kappa [-], alpha_rad [rad]).
    Guard max(|vx|, TIRE_EPS_MPS=0.5) dle tires.compute_slip."""
    s = compute_slip(omega, radius_m, vx_w, vy_w, steer_rad)
    return s["kappa"], s["alpha_rad"]


def tire_force(kappa, alpha_rad, fz_N, mu_long, mu_lat, B_long, C_long,
               B_lat, C_lat):
    """Síly pneu. Vstupy: kappa [-], alpha_rad [rad], fz_N [N], mu_long [-],
    mu_lat [-], B_long/C_long/B_lat/C_lat [-].
    Výstupy: (fx_N [N], fy_N [N]). Dx = mu_long*Fz, Dy = mu_lat*Fz;
    MF přes tires.magic_formula + třecí kružnice; Fz <= 0 -> (0, 0)."""
    for _v, _n in ((kappa, "kappa"), (alpha_rad, "alpha_rad"),
                   (fz_N, "fz_N")):
        if not isinstance(_v, (int, float)) or not math.isfinite(float(_v)):
            raise ValueError("tire_force: nekonecny vstup")
    if fz_N <= 0.0:
        return 0.0, 0.0
    Dx = mu_long * fz_N
    Dy = mu_lat * fz_N
    fx0 = magic_formula(kappa, B_long, C_long, Dx)
    fy0 = magic_formula(alpha_rad, B_lat, C_lat, Dy)
    rho = math.sqrt((fx0 / Dx) ** 2 + (fy0 / Dy) ** 2)
    if rho > 1.0:
        s = 1.0 / rho
        fx0 *= s
        fy0 *= s
    # Dotyk compute_grip (delegace na tires): konzistence pro mu_long == mu_lat.
    if mu_long == mu_lat:
        _chk = compute_grip(kappa, alpha_rad, fz_N, mu_long,
                            B_long, C_long, B_lat, C_lat)
        assert math.isclose(_chk["fx_N"], fx0, rel_tol=1e-12, abs_tol=1e-9)
        assert math.isclose(_chk["fy_N"], fy0, rel_tol=1e-12, abs_tol=1e-9)
    return fx0, fy0


def engine_torque(rpm, throttle, peak_torque_nm, peak_power_kw, idle_rpm,
                  redline_rpm):
    """Moment motoru. Vstupy: rpm [rpm], throttle [0..1], peak_torque_nm [Nm],
    peak_power_kw [kW], idle_rpm [rpm], redline_rpm [rpm].
    Výstup: torque_Nm [Nm]. Delegace: náhradní křivka
    engine.curve_from_config + engine.engine_output + výkonový strop
    P = tau*omega (stejný princip jako backend builtin-v1)."""
    cfg = curve_from_config(peak_torque_nm, peak_power_kw, redline_rpm,
                            idle_rpm)
    out = engine_output(cfg["curve"], rpm, throttle, redline_rpm, idle_rpm)
    tau = out["torque_nm"]
    omega = max(float(rpm), 0.0) * 2.0 * math.pi / 60.0
    if omega > 1.0:
        cap = peak_power_kw * 1000.0 / omega
        if tau > cap:
            tau = cap
    return tau


def gear_output(torque_in_Nm, ratio, final_drive, efficiency):
    """Převod. Vstupy: torque_in_Nm [Nm], ratio [-], final_drive [-],
    efficiency (0..1] [-]. Výstupy: (torque_out_Nm [Nm], total_ratio [-]).
    Delegace na gearbox.gear_output (gears=[ratio], gear=1)."""
    out = _gearbox_output(torque_in_Nm, 0.0, 1, [ratio], final_drive,
                          efficiency)
    return out["torque_out_nm"], out["total_ratio"]


def quasi_static_loads(mass_kg, g, a_m, b_m, h_m, L_m, track_m, a_long,
                       a_lat):
    """Kvazistatické zatížení kol. Vstupy: mass_kg [kg], g [m/s^2],
    a_m/b_m/h_m/L_m [m], track_m [m], a_long/a_lat [m/s^2].
    Výstupy: (fz_FL, fz_FR, fz_RL, fz_RR) [N]; a_long > 0 = vpřed (zatíží
    zadek), a_lat > 0 = vlevo (zatíží pravá kola). Delegace na
    load_transfer.compute_loads (bez aera, a_vert = 0)."""
    loads = compute_loads(mass_kg, a_m, b_m, h_m, L_m, track_m,
                          a_long_mps2=a_long, a_lat_mps2=a_lat,
                          a_vert_mps2=0.0, g=g, aero_N=0.0)
    return loads["FL"], loads["FR"], loads["RL"], loads["RR"]

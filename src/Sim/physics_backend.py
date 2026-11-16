"""Fyzikalni backend: volani src/Physics (relativne, bez kopirovani).

Ocekavane rozhrani src/Physics (pro koordinatora / agenta B): modul
`src/Physics/api.py` s cistymi funkcemi:
  tire_slip(vx_w, vy_w, omega, radius_m, steer_rad) -> (kappa, alpha_rad)
  tire_force(kappa, alpha_rad, fz_N, mu_long, mu_lat, B_long, C_long,
             B_lat, C_lat) -> (fx_N, fy_N)
  engine_torque(rpm, throttle, peak_torque_nm, peak_power_kw, idle_rpm,
                redline_rpm) -> torque_Nm
  gear_output(torque_in_Nm, ratio, final_drive, efficiency)
      -> (torque_out_Nm, total_ratio)
  quasi_static_loads(mass_kg, g, a_m, b_m, h_m, L_m, track_m, a_long, a_lat)
      -> (fz_FL, fz_FR, fz_RL, fz_RR)

Pokud src/Physics (zatim) neexistuje, pouzije se vestaveny fallback
`builtin-v1` — puvodni implementace agenta C podle principu a vzorcu
z docs/KNOWLEDGE-TRANSFER.md (§2.1–2.6: slip kinematika + eps-guard,
Magic-Formula + friction circle + Fz<=0 -> 0, kvazistatika zateze,
plynula krivka misto plocheho motoru). Zadny kod neni kopirovan.
Aktivni backend se zapisuje do manifestu (pole `backend`).
"""

import math

EXPECTED_PHYSICS_API = ("tire_slip", "tire_force", "engine_torque",
                        "gear_output", "quasi_static_loads")

_backend_name = "builtin-v1"
_ext = None

try:  # relativni import balicku src.Physics (bez kopirovani)
    from ..Physics import api as _ext  # noqa: F401
    if all(hasattr(_ext, name) for name in EXPECTED_PHYSICS_API):
        _backend_name = "src.Physics.api"
    else:
        _ext = None
except Exception:
    _ext = None

try:  # absolutni fallback pri prime ceste (root repo na sys.path)
    if _ext is None:
        from src.Physics import api as _ext2  # noqa: F401
        if all(hasattr(_ext2, name) for name in EXPECTED_PHYSICS_API):
            _ext = _ext2
            _backend_name = "src.Physics.api"
        del _ext2
except Exception:
    pass


def backend_name():
    return _backend_name


# ------------------------------------------------------------- slip (KT §2.1)
def tire_slip(vx_w, vy_w, omega, radius_m, steer_rad, eps=1.0):
    """Skluz: kappa = (w*R - vx)/max(|vx|, eps); alpha = steer - atan(vy/denom).

    Overeny princip z KNOWLEDGE-TRANSFER §2.1 (TireSlip.luau). eps-guard
    chrani rozjezd/stani (neni to fyzika couvani).
    """
    if _ext is not None:
        return _ext.tire_slip(vx_w, vy_w, omega, radius_m, steer_rad)
    denom = abs(vx_w)
    if denom < eps:
        denom = eps
    kappa = (omega * radius_m - vx_w) / denom
    alpha = steer_rad - math.atan2(vy_w, denom)
    return kappa, alpha


# ------------------------------------------------------------- grip (KT §2.1)
def tire_force(kappa, alpha_rad, fz_N, mu_long, mu_lat,
               B_long, C_long, B_lat, C_lat):
    """Magic-Formula + friction circle; Fz <= 0 -> (0, 0).

    Princip z KNOWLEDGE-TRANSFER §2.1 (TireGrip.luau). Kruh, ne elipsa
    (zname omezeni zdroje, viz KT §2.1) — elipsa je ukol pozdejsi faze.
    """
    if _ext is not None:
        return _ext.tire_force(kappa, alpha_rad, fz_N, mu_long, mu_lat,
                               B_long, C_long, B_lat, C_lat)
    if not (math.isfinite(kappa) and math.isfinite(alpha_rad)
            and math.isfinite(fz_N)):
        raise ValueError("tire_force: nekonecny vstup")
    if fz_N <= 0.0:
        return 0.0, 0.0
    Dx = mu_long * fz_N
    Dy = mu_lat * fz_N
    fx0 = Dx * math.sin(C_long * math.atan(B_long * kappa))
    fy0 = Dy * math.sin(C_lat * math.atan(B_lat * alpha_rad))
    rho = math.sqrt((fx0 / Dx) ** 2 + (fy0 / Dy) ** 2)
    if rho > 1.0:
        s = 1.0 / rho
        fx0 *= s
        fy0 *= s
    return fx0, fy0


# --------------------------------------------------- zatizeni kol (KT §2.3)
def quasi_static_loads(mass_kg, g, a_m, b_m, h_m, L_m, track_m,
                       a_long, a_lat):
    """Kvazistaticky prenos zatizeni (princip KT §2.3 WeightTransfer).

    Vraci (FL, FR, RL, RR). Vlevo = +y. Zapory se clampuji na 0 (lift).
    """
    if _ext is not None:
        return _ext.quasi_static_loads(mass_kg, g, a_m, b_m, h_m, L_m,
                                       track_m, a_long, a_lat)
    Ff = mass_kg * g * b_m / L_m
    Fr = mass_kg * g * a_m / L_m
    d_long = mass_kg * a_long * h_m / L_m
    Dlat = 2.0 * mass_kg * a_lat * h_m / track_m
    stat_f, stat_r = Ff / 2.0, Fr / 2.0
    dlat_f = (Dlat / 2.0) * (b_m / L_m)
    dlat_r = (Dlat / 2.0) * (a_m / L_m)
    raw = [stat_f - d_long / 2.0 - dlat_f,   # FL (+y)
           stat_f - d_long / 2.0 + dlat_f,   # FR (-y)
           stat_r + d_long / 2.0 - dlat_r,   # RL
           stat_r + d_long / 2.0 + dlat_r]   # RR
    return tuple(v if v > 0.0 else 0.0 for v in raw)


# ------------------------------------------------------------- motor (KT §2.5)
def engine_torque(rpm, throttle, peak_torque_nm, peak_power_kw,
                  idle_rpm, redline_rpm):
    """Mapa tau(omega, throttle): tvarovana krivka + vykonovy strop.

    Struktura dle KT §2.5 (Engine: tau = throttle*Tmax, P = tau*omega),
    ale OPRAVENA znama vada zdroje (plochy motor + skok na redline):
    krivka ma nabeh od volnobehu a vykonovy strop P = tau*omega.
    """
    if _ext is not None:
        return _ext.engine_torque(rpm, throttle, peak_torque_nm,
                                  peak_power_kw, idle_rpm, redline_rpm)
    if rpm >= redline_rpm:
        return 0.0
    span = redline_rpm - idle_rpm
    xn = (rpm - idle_rpm) / span if span > 0 else 1.0
    xn = 0.0 if xn < 0.0 else (1.0 if xn > 1.0 else xn)
    shape = 0.78 + 0.22 * (math.sin(math.pi * xn) ** 0.7)
    tau = throttle * peak_torque_nm * shape
    omega = rpm * 2.0 * math.pi / 60.0
    if omega > 1.0:
        cap = peak_power_kw * 1000.0 / omega
        if tau > cap:
            tau = cap
    return tau


def gear_output(torque_in_Nm, ratio, final_drive, efficiency):
    """Idealni prevod: tau_out = tau_in*ratio*final*eff (KT §2.5 Gearbox)."""
    if _ext is not None:
        return _ext.gear_output(torque_in_Nm, ratio, final_drive, efficiency)
    total = ratio * final_drive
    return torque_in_Nm * total * efficiency, total


def fail_if_nonfinite(name, value):
    if not math.isfinite(value):
        raise ValueError("Nekonecna hodnota v %s" % name)

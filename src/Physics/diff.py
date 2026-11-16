# diff.py — diferenciály: rozdělení FWD/RWD/AWD, otevřený/svorný.
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: moment na vstupu [Nm], typ pohonu (FWD/RWD/AWD), přední bias [-],
#           svornost lock [0..1], otáčky kol [rad/s], účinnost [-].
#   Výstupy: momenty na kola {FL, FR, RL, RR} [Nm], x vpřed / y vlevo.
# PŘEDPOKLADY
#   - Otevřený dif = 50/50 na nápravě; svornost přerozděluje k pomalejšímu kolu.
#   - AWD má mezinápravový split konfigurovatelný (front_bias), ne natvrdo 50/50.
# LIMITY
#   - Algebraický model svornosti, žádná teplota/lamely; invariant Σ = T_in*eff.
# ZDROJE (principy):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Powertrain/Shafts.luau
#     (bias = lock*dw/(dw+5.0); pomalejší T*(0.5+0.5*bias); lock=0 -> 50/50)
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/VehicleDynamics.luau ř. 264–267
#     (AWD 50/50 bez mezinápravového difu + lock=0 natvrdo = CHYBA, kterou zde
#     NEPŘEBÍRÁME: split je konfigurovatelný a lock se skutečně uplatní).
# FLAG source: "measured" / "estimated" / "simplified".

"""Diferenciály: rozdělení momentu na kola pro FWD/RWD/AWD."""

from __future__ import annotations

import math

SOURCES = {
    "drive_type": "measured",       # koncepce vozu (factory)
    "front_bias": "estimated",      # mezinápravový split, pokud není factory údaj
    "lock": "estimated",            # svornost; kalibrační parametr
    "lock_formula": "simplified",   # algebraický bias-vzorec ze Shafts.luau
}

WHEELS = ("FL", "FR", "RL", "RR")


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def shaft_split(torque_axle_nm: float, lock: float, omega_l_rads: float,
                omega_r_rads: float, efficiency: float = 1.0) -> tuple:
    """Rozdělení momentu nápravy na kola. Svornost tlačí moment k pomalejšímu kolu.
    Vstup: [Nm], lock [0..1], otáčky [rad/s]. Výstup: (T_left, T_right) [Nm].
    Vzorec: bias = lock*dw/(dw+5.0); pomalejší T*(0.5+0.5*bias). Invariant Σ=T*eff."""
    t = _finite(torque_axle_nm, "torque_axle_nm")
    lk = _finite(lock, "lock")
    wl = _finite(omega_l_rads, "omega_l_rads")
    wr = _finite(omega_r_rads, "omega_r_rads")
    eff = _finite(efficiency, "efficiency")
    if not 0.0 <= lk <= 1.0:
        raise ValueError("lock musi byt v [0, 1]")
    if not 0.0 < eff <= 1.0:
        raise ValueError("efficiency musi byt v (0, 1]")
    total = t * eff
    dw = abs(wl - wr)
    bias = lk * dw / (dw + 5.0)
    if wl <= wr:
        return (total * (0.5 + 0.5 * bias), total * (0.5 - 0.5 * bias))
    return (total * (0.5 - 0.5 * bias), total * (0.5 + 0.5 * bias))


def distribute(torque_in_nm: float, drive_type: str, front_bias: float = 0.5,
               lock_front: float = 0.0, lock_rear: float = 0.0,
               lock_center: float = 0.0, omega: dict | None = None,
               efficiency: float = 0.95) -> dict:
    """Rozdělení momentu převodovky na 4 kola. Vstup: [Nm], drive_type FWD/RWD/AWD,
    front_bias [0..1] podíl předku (jen AWD), svornosti [0..1], otáčky kol [rad/s].
    Výstup: {FL, FR, RL, RR} [Nm]. Nehnaná náprava = 0."""
    t = _finite(torque_in_nm, "torque_in_nm")
    eff = _finite(efficiency, "efficiency")
    if drive_type not in ("FWD", "RWD", "AWD"):
        raise ValueError("drive_type musi byt FWD/RWD/AWD")
    fb = _finite(front_bias, "front_bias")
    if not 0.0 <= fb <= 1.0:
        raise ValueError("front_bias musi byt v [0, 1]")
    om = dict(omega) if omega else {}
    for w in WHEELS:
        om.setdefault(w, 0.0)
        om[w] = _finite(om[w], f"omega[{w}]")
    for name, lk in (("lock_front", lock_front), ("lock_rear", lock_rear),
                     ("lock_center", lock_center)):
        lk = _finite(lk, name)
        if not 0.0 <= lk <= 1.0:
            raise ValueError(f"{name} musi byt v [0, 1]")

    if drive_type == "FWD":
        front, rear = t * eff, 0.0
    elif drive_type == "RWD":
        front, rear = 0.0, t * eff
    else:
        # Mezinápravový split: svornost přitahuje moment k pomalejší nápravě.
        mean_f = 0.5 * (om["FL"] + om["FR"])
        mean_r = 0.5 * (om["RL"] + om["RR"])
        dw = abs(mean_f - mean_r)
        bias_c = lock_center * dw / (dw + 5.0)
        fb_eff = fb
        if mean_f > mean_r:
            fb_eff = fb * (1.0 - bias_c)  # předek rychlejší -> ubrat
        elif mean_r > mean_f:
            fb_eff = fb + (1.0 - fb) * bias_c  # zadek rychlejší -> přidat předku
        front, rear = t * eff * fb_eff, t * eff * (1.0 - fb_eff)

    fl, fr = shaft_split(front, lock_front, om["FL"], om["FR"]) if front else (0.0, 0.0)
    rl, rr = shaft_split(rear, lock_rear, om["RL"], om["RR"]) if rear else (0.0, 0.0)
    return {"FL": fl, "FR": fr, "RL": rl, "RR": rr}

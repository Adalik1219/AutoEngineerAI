"""Nahradni (fallback) simulator: deterministicke podélné synteticke stopy.

Pouzit pouze kdyz src/Sim (Agent C) neni k dispozici – backend.py nejprve
zkousi externi simulator a tuto syntezu hlasi v manifestu jako
sim_backend=fallback-synth-v0 (uroven SIM, ne dukaz pro Roblox).
Vystup: radky se SLOZENIM dle src/Telemetry/metrics.py TELEMETRY_COLUMNS
(x vpred / y vlevo / z vzhuru, SI, zaznam 60 Hz, fyzika dt=1/240).

Model: bodova hmota, idealni prevod, automaticke razeni pri shift_rpm
s vypadkem momentu shift_time_s, trakcni strop RWD, odpor vzduchu+valeni.
Kalibrace (odhady, SIM only): MASS_KG=1150 (curb 1075 + ridic 75, S1),
WHEEL_R_M=0.308 (z 205/45 R17, prumer 616 mm), CDA_M2=0.70 (sedí V-max
tovarniho configu ~216 km/h), MU=0.95 (suchy asfalt).
Zamerne citlivy na final_drive: sila na kolech, pocet prerazeni do 100 km/h
i omezeni V-max prevodem – optimum je vnitrni (~3.5–4.0), ne na mezi.
Pouze stdlib.
"""

import csv
import hashlib
import math

DT = 1.0 / 240.0
REC_EVERY = 4  # zaznam kazdy 4. krok = 60 Hz
G = 9.81
RHO_AIR = 1.225
CDA_M2 = 0.70
CRR = 0.012
MASS_KG = 1150.0
WHEEL_R_M = 0.308
EFFICIENCY = 0.92
MU_DRY = 0.95
REAR_SHARE = 0.55  # RWD: podil normalove sily na hnaci naprave pri rozjezdu
OPT_BIAS = 0.60  # kalibracni optimum brzdneho biasu SIM modelu

try:
    from src.Telemetry.metrics import TELEMETRY_COLUMNS as _COLS
    TELEMETRY_COLUMNS = tuple(_COLS)
except Exception:
    # Zalozni sada (shodna s Agentem F) pro beh bez src/Telemetry na ceste.
    TELEMETRY_COLUMNS = (
        "time_s", "x_m", "y_m", "v_mps", "a_long_mps2", "a_lat_mps2",
        "yaw_rad", "yaw_rate_radps", "steer_rad", "throttle", "brake",
        "gear", "engine_rpm", "engine_torque_nm",
        "omega_FL", "omega_FR", "omega_RL", "omega_RR",
        "slip_FL", "slip_FR", "slip_RL", "slip_RR",
        "fz_FL", "fz_FR", "fz_RL", "fz_RR",
        "travel_FL", "travel_FR", "travel_RL", "travel_RR",
    )


def j01(key):
    """Deterministicky pseudo-nahodny slip v [0,1) z retezce (seed, stabilni)."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2.0 ** 64


def _params(config):
    p = config.get("parameters", {})
    eng = p.get("engine", {})
    tra = p.get("transmission", {})
    tir = p.get("tires", {})
    brk = p.get("brakes", {})
    return {
        "t_peak": float(eng.get("peak_torque_nm", 205.0)),
        "p_peak_kw": float(eng.get("peak_power_kw", 135.0)),
        "gears": [float(g) for g in tra.get("gears", [5.087, 2.991, 2.035, 1.594, 1.286, 1.0])],
        "final_drive": float(tra.get("final_drive", 2.866)),
        "shift_rpm": float(tra.get("shift_rpm", 7000.0)),
        "shift_time_s": float(tra.get("shift_time_s", 0.4)),
        "grip": float(tir.get("grip_long", 1.0)),
        "bias": float(brk.get("bias_front", 0.62)),
    }


def _engine_torque(rpm, t_peak, p_peak_kw):
    omega = max(rpm * 2.0 * math.pi / 60.0, 50.0)
    return min(t_peak, p_peak_kw * 1000.0 / omega)


def _row(t, x, v, a, throttle, brake, gear, rpm, torque, slip_r):
    fz = MASS_KG * G / 4.0
    om_f = v / WHEEL_R_M
    om_r = v * (1.0 + slip_r) / WHEEL_R_M
    return {
        "time_s": t, "x_m": x, "y_m": 0.0, "v_mps": max(v, 0.0),
        "a_long_mps2": a, "a_lat_mps2": 0.0,
        "yaw_rad": 0.0, "yaw_rate_radps": 0.0, "steer_rad": 0.0,
        "throttle": throttle, "brake": brake,
        "gear": gear, "engine_rpm": rpm, "engine_torque_nm": torque,
        "omega_FL": om_f, "omega_FR": om_f, "omega_RL": om_r, "omega_RR": om_r,
        "slip_FL": 0.0, "slip_FR": 0.0, "slip_RL": slip_r, "slip_RR": slip_r,
        "fz_FL": fz, "fz_FR": fz, "fz_RL": fz, "fz_RR": fz,
        "travel_FL": 0.0, "travel_FR": 0.0, "travel_RL": 0.0, "travel_RR": 0.0,
    }


def synth_accel_rows(config, seed, duration_s=45.0):
    """Stopa straight_accel: plny plyn s rampou, auto-razeni, dojezd na V-max."""
    q = _params(config)
    gears, fd = q["gears"], q["final_drive"]
    ramp = 0.20 + (j01("accel|ramp|%s" % seed) - 0.5) * 0.02
    f_cap = MU_DRY * q["grip"] * MASS_KG * G * REAR_SHARE
    t, v, x = 0.0, 0.0, 0.0
    gear = 1
    shift_timer = 0.0
    rows = []
    recent_v = []
    step = 0
    while t < duration_s:
        thr = min(1.0, t / ramp) if ramp > 0 else 1.0
        gr = gears[gear - 1]
        rpm = v * gr * fd / WHEEL_R_M * 60.0 / (2.0 * math.pi)
        torque = 0.0
        if shift_timer > 0.0:
            shift_timer -= DT
        elif rpm > q["shift_rpm"] and gear < len(gears):
            gear += 1
            shift_timer = q["shift_time_s"]
            gr = gears[gear - 1]
            rpm = v * gr * fd / WHEEL_R_M * 60.0 / (2.0 * math.pi)
        else:
            torque = _engine_torque(rpm, q["t_peak"], q["p_peak_kw"])
        force = torque * gr * fd * EFFICIENCY / WHEEL_R_M
        force = min(force, f_cap) * thr
        resist = 0.5 * RHO_AIR * CDA_M2 * v * v + CRR * MASS_KG * G
        a = (force - resist) / MASS_KG
        v += a * DT
        if v < 0:
            v = 0.0
        x += v * DT
        t += DT
        step += 1
        slip_r = min(0.12, 0.06 * force / f_cap) if f_cap > 0 and force > 0 else 0.0
        if step % REC_EVERY == 0:
            rows.append(_row(t, x, v, a, thr, 0.0, gear, rpm, torque, slip_r))
            recent_v.append(v)
            if len(recent_v) > 300:
                recent_v.pop(0)
            # Predcasny konec: ustálena V-max (std poslednich 5 s < 0.3).
            if t > 25.0 and len(recent_v) == 300:
                avg = sum(recent_v) / len(recent_v)
                var = sum((w - avg) ** 2 for w in recent_v) / len(recent_v)
                if var < 0.09:
                    break
    return rows


def synth_brake_rows(config, seed, v0_mps=27.7778, duration_s=8.0):
    """Stopa straight_brake_100_0: ustalena rychlost, pak plna brzda do zastaveni."""
    q = _params(config)
    mu = MU_DRY * (1.0 + (j01("brake|mu|%s" % seed) - 0.5) * 0.006)
    ramp = 0.15 + (j01("brake|ramp|%s" % seed) - 0.5) * 0.02
    v0 = v0_mps * (1.0 + (j01("brake|v0|%s" % seed) - 0.5) * 0.004)
    factor = 1.0 - 2.0 * (q["bias"] - OPT_BIAS) ** 2
    factor = max(0.5, factor)
    t, v, x = 0.0, v0, 0.0
    rows = []
    step = 0
    while t < duration_s:
        brk = min(1.0, t / ramp) if ramp > 0 else 1.0
        a = -mu * G * factor * brk
        v += a * DT
        if v < 0:
            v = 0.0
        x += v * DT
        t += DT
        step += 1
        if step % REC_EVERY == 0:
            rows.append(_row(t, x, v, a, 0.0, brk, 0, 0.0, 0.0, 0.0))
            if v <= 0.05 and t > 1.0:
                # Dolezi par vzorku pro detekci uplneho zastaveni.
                if step % REC_EVERY == 0 and t > 1.0 and v <= 0.05:
                    extra = 0
                    while extra < 12:
                        t += DT * REC_EVERY
                        rows.append(_row(t, x, 0.0, 0.0, 0.0, 1.0, 0, 0.0, 0.0, 0.0))
                        extra += 1
                    break
    return rows


def write_csv(path, rows):
    """Zapise stopy do CSV s hlavickou kompatibilni s Agentem F."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(TELEMETRY_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row[c] for c in TELEMETRY_COLUMNS})

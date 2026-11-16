"""Stav vozidla + semi-implicitni Euler krok + smycka scenare.

Stav (planar + vertikalni karoserie + 4 kola + pohon):
  x, y, yaw | u (podéne), v (pricne), r (yaw rate)
  z, vz, pitch, pitch_rate, roll, roll_rate (karoserie vuci statice)
  omega[4] (kola), gear, rpm, shift_timer
  a_long, a_lat (specificke zrychleni pro telemetrii)
Poradi kol: FL, FR, RL, RR. Souradnice: x vpred, y vlevo, z vzhuru. SI.

Schema kroku (semi-implicitni Euler): sily -> zrychleni ->
aktualizace rychlosti -> aktualizace poloh. Kolo: Iw*dw =
Tdrive - Tbrake - R*Fx (princip KT §2.4 Wheel) + hold pri stani.
Karoserie vertikalne: pruzina+tlumic na roh (princip KT §2.4),
kolo sleduje vozovku, Fz >= 0 (lift -> 0).
Rizeni: rate-limit + rychlostni orez + Ackermann (princip KT §2.2).
"""

import math
import random

from . import physics_backend as phys

WHEEL_ORDER = ("FL", "FR", "RL", "RR")

# gainy ridicich regulatoru se resi ve scenarios.py; zde jen meze
_BRAKE_SMOOTH_W = 0.3  # vyhlazeni brzdneho momentu kolem omega = 0


def _clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def build_road_bumps(seed):
    """Seedovane pole nerovnosti pro bump_section (deterministicke).

    Vraci (zl(x), zr(x)) — vyska vozovky leve/prave stopy.
    Mimo usek [50, 300] nula s 5m nabehem. Sinus + seedovane hrboly.
    """
    rng_l = random.Random(seed)
    rng_r = random.Random(seed ^ 0x9E3779B9)
    bumps_l = [(rng_l.uniform(60.0, 290.0), rng_l.uniform(0.5, 1.5),
                rng_l.uniform(0.02, 0.06)) for _ in range(12)]
    bumps_r = [(rng_r.uniform(60.0, 290.0), rng_r.uniform(0.5, 1.5),
                rng_r.uniform(0.02, 0.06)) for _ in range(12)]
    probe = [rng_l.random(), rng_l.random(), rng_r.random()]

    def envelope(x):
        if x < 45.0 or x > 305.0:
            return 0.0
        if x < 50.0:
            return 0.5 - 0.5 * math.cos(math.pi * (x - 45.0) / 5.0)
        if x > 300.0:
            return 0.5 + 0.5 * math.cos(math.pi * (x - 300.0) / 5.0)
        return 1.0

    def field(bumps, x):
        env = envelope(x)
        if env == 0.0:
            return 0.0
        z = 0.015 * math.sin(2.0 * math.pi * (x - 50.0) / 8.0)
        for (c, w, h) in bumps:
            d = abs(x - c)
            if d < w:
                z += h * 0.5 * (1.0 + math.cos(math.pi * d / w))
        return z * env

    def zl(x):
        return field(bumps_l, x)

    def zr(x):
        return field(bumps_r, x)

    return zl, zr, probe


def _corner_geometry(params):
    m = params["mass"]
    d = params["dimensions"]
    L = d["wheelbase_m"]
    a, b = m["cog_a_m"], m["cog_b_m"]
    px = [a, a, -b, -b]
    py = [d["track_f_m"] / 2.0, -d["track_f_m"] / 2.0,
          d["track_r_m"] / 2.0, -d["track_r_m"] / 2.0]
    return px, py, L


def _initial_gear(params, v0):
    trans = params["transmission"]
    eng = params["engine"]
    r = params["tires"]["radius_m"]
    if v0 < 0.5:
        return 1
    w_wheel = v0 / r
    for gi in range(len(trans["gears"]) - 1, 0, -1):
        total = trans["gears"][gi] * trans["final_drive"]
        rpm = w_wheel * total * 60.0 / (2.0 * math.pi)
        if rpm >= 2000.0 and rpm <= eng["shift_rpm"]:
            return gi + 1
    return 1


def init_state(params, init):
    """Pocatecni stav (klid/rozjezd dle init)."""
    m = params["mass"]
    trans = params["transmission"]
    r = params["tires"]["radius_m"]
    v0 = init.get("v0_mps", 0.0)
    gear0 = init.get("gear0", 1)
    gear = _initial_gear(params, v0) if gear0 == "auto" else int(gear0)
    total = trans["gears"][gear - 1] * trans["final_drive"]
    w0 = v0 / r
    # Staticke Fz pro nulty krok (kvazistatika, a = 0).
    d = params["dimensions"]
    L = d["wheelbase_m"]
    track = 0.5 * (d["track_f_m"] + d["track_r_m"])
    fz = phys.quasi_static_loads(m["total_kg"], 9.81, m["cog_a_m"],
                                 m["cog_b_m"], m["cog_h_m"], L, track,
                                 0.0, 0.0)
    susp = params["suspension"]
    kf = [susp["spring_f_Npm"], susp["spring_f_Npm"],
          susp["spring_r_Npm"], susp["spring_r_Npm"]]
    d0 = [fz[i] / kf[i] for i in range(4)]
    return {
        "t": 0.0, "x": 0.0, "y": 0.0, "yaw": 0.0,
        "u": v0, "v": 0.0, "r": 0.0,
        "z": 0.0, "vz": 0.0, "pitch": 0.0, "pitch_rate": 0.0,
        "roll": 0.0, "roll_rate": 0.0,
        "omega": [w0, w0, w0, w0],
        "gear": gear, "rpm": params["engine"]["idle_rpm"],
        "shift_timer": 0.0, "steer": 0.0,
        "throttle": 0.0, "brake": 0.0,
        "a_long": 0.0, "a_lat": 0.0,
        "fz": list(fz), "travel": [0.0, 0.0, 0.0, 0.0],
        "slip": [0.0, 0.0, 0.0, 0.0],
        "k_static_d0": d0,
        "prev_road": [0.0, 0.0, 0.0, 0.0],
        "engine_torque": 0.0,
    }


def _steering_step(state, steer_norm, params, dt):
    """Rate-limit + rychlostni orez (princip KT §2.2 Steering)."""
    st = params["steering"]
    vmax_angle = st["max_angle_deg"] * math.pi / 180.0
    v = math.hypot(state["u"], state["v"])
    target = _clamp(steer_norm, -1.0, 1.0) * vmax_angle
    target /= 1.0 + (v / st["speed_ref_mps"]) ** 2
    cur = state["steer"]
    step = st["max_rate_radps"] * dt
    nxt = _clamp(target, cur - step, cur + step)
    state["steer"] = nxt
    return nxt


def _engine_rpm(state, params):
    # Zamerne z rychlosti vozidla (aproximace sepnute spojky): pri prokluzu
    # by otacky z kol kmitaly a razeni by cyklovalo. Prokluz se porad
    # uplatni pres silovou saturaci pneumatik. Dokumentovany predpoklad.
    trans = params["transmission"]
    eng = params["engine"]
    r = params["tires"]["radius_m"]
    v = math.hypot(state["u"], state["v"])
    total = trans["gears"][state["gear"] - 1] * trans["final_drive"]
    rpm = (v / r) * total * 60.0 / (2.0 * math.pi)
    return max(rpm, eng["idle_rpm"])


def _shift_logic(state, params, dt):
    eng = params["engine"]
    trans = params["transmission"]
    if state["shift_timer"] > 0.0:
        state["shift_timer"] -= dt
    rpm = state["rpm"]
    gear = state["gear"]
    ng = len(trans["gears"])
    if state["shift_timer"] <= 0.0:
        if rpm >= eng["shift_rpm"] and gear < ng and state["throttle"] > 0.3:
            state["gear"] += 1
            state["shift_timer"] = trans["shift_time_s"]
        elif rpm < 2000.0 and gear > 1:
            state["gear"] -= 1
            state["shift_timer"] = trans["shift_time_s"]


def step(state, ctrl, params, dt, road_l, road_r):
    """Jeden semi-implicitni Euler krok. Aktualizuje state in-place."""
    p = params
    m = p["mass"]
    trans = p["transmission"]
    eng = p["engine"]
    tir = p["tires"]
    sus = p["suspension"]
    aero = p["aero"]
    px, py, L = _corner_geometry(p)

    throttle, brake, steer_norm = ctrl["inputs"]
    steer = _steering_step(state, steer_norm, p, dt)
    state["throttle"] = throttle
    state["brake"] = brake

    # --- vozovka pod koly (kolo sleduje vozovku)
    wx = [state["x"] + px[i] * math.cos(state["yaw"])
          - py[i] * math.sin(state["yaw"]) for i in range(4)]
    zw = [road_l(wx[i]) if py[i] > 0 else road_r(wx[i]) for i in range(4)]
    vzw = [(zw[i] - state["prev_road"][i]) / dt for i in range(4)]
    state["prev_road"] = zw

    # --- vertikalni karoserie: h_c rohu, rychlosti rohu
    hc = [state["z"] + state["pitch"] * px[i] + state["roll"] * py[i]
          for i in range(4)]
    vhc = [state["vz"] + state["pitch_rate"] * px[i]
           + state["roll_rate"] * py[i] for i in range(4)]
    kf = [sus["spring_f_Npm"], sus["spring_f_Npm"],
          sus["spring_r_Npm"], sus["spring_r_Npm"]]
    cb = [sus["damper_f_bump_Nspm"], sus["damper_f_bump_Nspm"],
          sus["damper_r_bump_Nspm"], sus["damper_r_bump_Nspm"]]
    cr = [sus["damper_f_reb_Nspm"], sus["damper_f_reb_Nspm"],
          sus["damper_r_reb_Nspm"], sus["damper_r_reb_Nspm"]]
    fz = []
    travel = []
    for i in range(4):
        gap = hc[i] - zw[i]
        comp = state["k_static_d0"][i] - gap  # + = komprese od statiky
        travel.append(comp)
        vrel = vhc[i] - vzw[i]
        c = cb[i] if vrel < 0.0 else cr[i]
        f = kf[i] * (state["k_static_d0"][i] - gap) - c * vrel
        fz.append(f if f > 0.0 else 0.0)
    state["fz"] = fz
    state["travel"] = travel

    # --- pohon: motor -> prevodovka -> kola
    state["rpm"] = _engine_rpm(state, p)
    _shift_logic(state, p, dt)
    state["rpm"] = _engine_rpm(state, p)
    if state["shift_timer"] > 0.0:
        tau_e = 0.0  # preruseni zaberu pri razeni
    else:
        tau_e = phys.engine_torque(state["rpm"], throttle,
                                   eng["peak_torque_nm"],
                                   eng["peak_power_kw"], eng["idle_rpm"],
                                   eng["redline_rpm"])
        # Rozjezdova spojka: omezeni zaberu pri malem v (deterministicke).
        # Aproximace rozjezdu bez rizeni prokluzu spojky (viz _engine_rpm).
        v = math.hypot(state["u"], state["v"])
        tau_e *= 0.55 + 0.45 * _clamp(v / 4.0, 0.0, 1.0)
    state["engine_torque"] = tau_e
    ratio = trans["gears"][state["gear"] - 1]
    tau_shaft, _total = phys.gear_output(tau_e, ratio, trans["final_drive"],
                                         trans["efficiency"])
    if trans["drive"] == "RWD":
        t_drive = [0.0, 0.0, tau_shaft / 2.0, tau_shaft / 2.0]
    elif trans["drive"] == "FWD":
        t_drive = [tau_shaft / 2.0, tau_shaft / 2.0, 0.0, 0.0]
    else:
        t_drive = [tau_shaft / 4.0] * 4

    # --- brzdy: rozdeleni predni/zadni (princip KT §2.4 Brakes)
    bias = p["brakes"]["bias_front"]
    tmax = p["brakes"]["torque_Nm"]
    t_brake_axle = [brake * tmax * bias / 2.0, brake * tmax * bias / 2.0,
                    brake * tmax * (1.0 - bias) / 2.0,
                    brake * tmax * (1.0 - bias) / 2.0]

    # --- pneumatiky: slip -> grip -> body sily
    mu_l = tir["grip_long"] * tir["mu_road"]
    mu_t = tir["grip_lat"] * tir["mu_road"]
    sum_fx = 0.0
    sum_fy = 0.0
    sum_mz = 0.0
    for i in range(4):
        dlt = steer if i < 2 else 0.0  # predni rizena naprava
        uw = state["u"] - state["r"] * py[i]
        vw = state["v"] + state["r"] * px[i]
        cd, sd = math.cos(dlt), math.sin(dlt)
        vx_w = uw * cd + vw * sd
        vy_w = -uw * sd + vw * cd
        kap, alp = phys.tire_slip(vx_w, vy_w, state["omega"][i],
                                  tir["radius_m"], dlt)
        state["slip"][i] = kap
        fx_w, fy_w = phys.tire_force(kap, alp, fz[i], mu_l, mu_t,
                                     tir["mf_B_long"], tir["mf_C_long"],
                                     tir["mf_B_lat"], tir["mf_C_lat"])
        fx_b = fx_w * cd - fy_w * sd
        fy_b = fx_w * sd + fy_w * cd
        # Valivy odpor.
        if abs(vx_w) > 0.1:
            fx_b -= aero["Crr"] * fz[i] * (1.0 if vx_w > 0 else -1.0)
        sum_fx += fx_b
        sum_fy += fy_b
        sum_mz += px[i] * fy_b - py[i] * fx_b
        # Kolo: Iw*dw = Tdrive - Tbrake - R*Fx (KT §2.4 Wheel) + hold.
        t_br = t_brake_axle[i] * _clamp(state["omega"][i] / _BRAKE_SMOOTH_W,
                                        -1.0, 1.0)
        net = t_drive[i] - t_br - tir["radius_m"] * fx_w
        held = (abs(state["omega"][i]) <= 0.5 and
                abs(t_drive[i] - tir["radius_m"] * fx_w)
                <= t_brake_axle[i] and brake > 0.05)
        if held:
            state["omega"][i] = 0.0
        else:
            state["omega"][i] += net / tir["inertia_kgm2"] * dt
        phys.fail_if_nonfinite("omega[%d]" % i, state["omega"][i])

    # Aero odpor (pusobi v tezisti, klopivy moment zanedban).
    sum_fx += -0.5 * aero["rho_kgpm3"] * aero["CdA_m2"] * state["u"] \
        * abs(state["u"])

    # --- planarni zrychleni (body frame, rotujici: + r×v cleny)
    ax = sum_fx / m["total_kg"] + state["r"] * state["v"]
    ay = sum_fy / m["total_kg"] - state["r"] * state["u"]
    yaw_acc = sum_mz / m["yaw_inertia_kgm2"]
    state["a_long"] = sum_fx / m["total_kg"]
    state["a_lat"] = sum_fy / m["total_kg"]

    # --- vertikalni zrychleni karoserie
    ms = m["sprung_kg"]
    az = sum(fz) / ms - 9.81
    pitch_acc = sum(fz[i] * px[i] for i in range(4)) / m["pitch_inertia_kgm2"]
    roll_acc = (sum(fz[i] * py[i] for i in range(4))
                - sus["arb_roll_Nm_per_rad"] * state["roll"]) \
        / m["roll_inertia_kgm2"]

    for name in ("ax", "ay", "yaw_acc", "az", "pitch_acc", "roll_acc"):
        phys.fail_if_nonfinite(name, locals()[name])

    # --- semi-implicitni Euler: nejprve rychlosti, pak polohy
    state["u"] += ax * dt
    state["v"] += ay * dt
    state["r"] += yaw_acc * dt
    state["vz"] += az * dt
    state["pitch_rate"] += pitch_acc * dt
    state["roll_rate"] += roll_acc * dt

    cy, sy = math.cos(state["yaw"]), math.sin(state["yaw"])
    state["x"] += (state["u"] * cy - state["v"] * sy) * dt
    state["y"] += (state["u"] * sy + state["v"] * cy) * dt
    state["yaw"] += state["r"] * dt
    state["z"] += state["vz"] * dt
    state["pitch"] += state["pitch_rate"] * dt
    state["roll"] += state["roll_rate"] * dt
    state["t"] += dt


def check_abort(state):
    """Abort kriteria (TESTING-OPTIMIZATION §4.5, zjednodusene)."""
    if abs(state["roll"]) > math.radians(60.0):
        return "rollover"
    if abs(state["pitch"]) > math.radians(60.0):
        return "pitch_over"
    if abs(state["r"]) > math.radians(120.0):
        return "spin"
    for name in ("u", "v", "r", "x", "y", "vz"):
        if not math.isfinite(state[name]):
            return "nonfinite_" + name
    return None


# Fixni telemetricke sloupce (kontrakt vyhodnoceni).
TELEMETRY_COLUMNS = [
    "time_s", "x_m", "y_m", "v_mps", "a_long_mps2", "a_lat_mps2",
    "yaw_rad", "yaw_rate_radps", "steer_rad", "throttle", "brake", "gear",
    "engine_rpm", "engine_torque_nm",
    "omega_FL", "omega_FR", "omega_RL", "omega_RR",
    "slip_FL", "slip_FR", "slip_RL", "slip_RR",
    "fz_FL", "fz_FR", "fz_RL", "fz_RR",
    "travel_FL", "travel_FR", "travel_RL", "travel_RR",
]


def telemetry_row(state):
    v = math.hypot(state["u"], state["v"])
    return [state["t"], state["x"], state["y"], v,
            state["a_long"], state["a_lat"], state["yaw"], state["r"],
            state["steer"], state["throttle"], state["brake"], state["gear"],
            state["rpm"], state["engine_torque"],
            state["omega"][0], state["omega"][1],
            state["omega"][2], state["omega"][3],
            state["slip"][0], state["slip"][1],
            state["slip"][2], state["slip"][3],
            state["fz"][0], state["fz"][1], state["fz"][2], state["fz"][3],
            state["travel"][0], state["travel"][1],
            state["travel"][2], state["travel"][3]]


def simulate(params, scenario_def, dt, seed):
    """Provede scenar. Vrati (rows, abort_reason, rng_probe).

    rows = seznam telemetrickych radku (vcetne t = 0).
    """
    from .scenarios import SCENARIO_VERSIONS  # lokalne proti cyklu
    _ = SCENARIO_VERSIONS
    road_l, road_r, probe = build_road_bumps(seed)
    init = scenario_def["init"](params)
    state = init_state(params, init)
    ctrl = {"dt": dt}
    rows = [telemetry_row(state)]
    abort = None
    while True:
        t = state["t"]
        if scenario_def["done"](t, state, ctrl, params):
            break
        ctrl["inputs"] = scenario_def["driver"](t, state, ctrl, params)
        step(state, ctrl, params, dt, road_l, road_r)
        rows.append(telemetry_row(state))
        ab = check_abort(state)
        if ab is not None:
            abort = ab
            break
        if len(rows) > 200000:
            abort = "timeout_rows"
            break
    return rows, abort, probe

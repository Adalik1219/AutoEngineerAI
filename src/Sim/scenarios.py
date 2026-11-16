"""Scenare (driver profily plyn/brzda/volant v case) + verze scenaru.

Kazdy scenar: id, scenario_version, duration_s, init (pocatecni podminky),
driver(t, state, ctrl) -> (throttle, brake, steer_norm).
Driver je ciste deterministicky: stejny (t, stav) = stejne vstupy.
PI regulatory (tempomat, stopar) drzi svuj stav v ctrl dictu, ktery je
soucasti stavu simulace — opakovatelnost tim neni narusena.
"""

import math

# Verze scenaru — soucast manifestu; zmena verze invaliduje srovnani.
SCENARIO_VERSIONS = {
    "straight_accel": "1.0.0",
    "straight_brake_100_0": "1.0.0",
    "constant_radius_turn": "1.0.0",
    "lane_change": "1.0.0",
    "bump_section": "1.0.0",
}

SCENARIOS = sorted(SCENARIO_VERSIONS.keys())


def _clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def _wrap_angle(a):
    while a > math.pi:
        a -= 2.0 * math.pi
    while a <= -math.pi:
        a += 2.0 * math.pi
    return a


# ------------------------------------------------------------------ S1 akcel
def _accel_init(params):
    return {"v0_mps": 0.0, "gear0": 1}


def _accel_driver(t, state, ctrl, params):
    throttle = _clamp(t / 0.2, 0.0, 1.0)  # rampa 0 -> 1 za 0.2 s
    return throttle, 0.0, 0.0


def _accel_done(t, state, ctrl, params):
    v = math.hypot(state["u"], state["v"])
    if v >= 27.78 and t > (ctrl.get("t100", 1e9) + 3.0):
        return True
    if v >= 27.78 and "t100" not in ctrl:
        ctrl["t100"] = t
    return t >= 40.0


# ------------------------------------------------------- S3 brzdy 100 -> 0
def _brake_init(params):
    return {"v0_mps": 27.77777777777778, "gear0": "auto"}


def _brake_driver(t, state, ctrl, params):
    brake = _clamp(t / 0.15, 0.0, 1.0)  # rampa 0 -> 1 za 0.15 s
    return 0.0, brake, 0.0


def _brake_done(t, state, ctrl, params):
    v = math.hypot(state["u"], state["v"])
    if v < 0.1:
        ctrl["settle"] = ctrl.get("settle", 0.0) + 1.0
        if ctrl["settle"] >= int(1.0 / ctrl["dt"]):
            return True
    else:
        ctrl["settle"] = 0.0
    return t >= 20.0


# ------------------------------------------------------- S4 konstantni oblouk
TURN_R_M = 30.0
TURN_V_MPS = 14.0


def _turn_init(params):
    return {"v0_mps": TURN_V_MPS, "gear0": "auto",
            "cx": 0.0, "cy": TURN_R_M}


def _turn_driver(t, state, ctrl, params):
    p = params
    # Tempomat 15 m/s (PI, stav v ctrl).
    err = TURN_V_MPS - state["u"]
    ctrl["cruise_i"] = _clamp(ctrl.get("cruise_i", 0.0) + err * ctrl["dt"],
                              -2.0, 2.0)
    u_cmd = 0.35 * err + 0.25 * ctrl["cruise_i"]
    throttle = _clamp(u_cmd, 0.0, 1.0)
    brake = _clamp(-u_cmd, 0.0, 0.6)
    # Stopar kruhu: tangent + PD na chybu kurzu vuci pozadovane yaw rate
    # + korekce radialni chyby. Feedforward Ackermann.
    dx = state["x"] - 0.0
    dy = state["y"] - TURN_R_M
    dist = math.hypot(dx, dy)
    phi = math.atan2(dy, dx)
    psi_des = phi + 0.5 * math.pi
    herr = _wrap_angle(psi_des - state["yaw"])
    e_r = dist - TURN_R_M
    prev = ctrl.get("prev_herr")
    dherr = 0.0 if prev is None else (herr - prev) / ctrl["dt"]
    ctrl["prev_herr"] = herr
    L = p["dimensions"]["wheelbase_m"]
    ff = math.atan(L / TURN_R_M)
    raw = ff + 1.2 * herr + 0.3 * dherr + 0.012 * e_r
    # Driver vydava normovany povel; _steering_step deli rychlostnim
    # orezem — prepoctem rad -> norm se orez presne kompenzuje.
    st = p["steering"]
    vmax_a = st["max_angle_deg"] * math.pi / 180.0
    cap = 1.0 + (state["u"] / st["speed_ref_mps"]) ** 2
    steer = _clamp(raw * cap / vmax_a, -0.9, 0.9)
    return throttle, brake, steer


def _turn_done(t, state, ctrl, params):
    return t >= 20.0


# ------------------------------------------------------- S5 zmena pruhu
LANE_T0 = 5.0
LANE_T = 3.0  # delsi perioda = klidnejsi prechod, bez saturace gum
LANE_A_RAD = 0.025  # spicka ~3-4 m/s2 pri 60 km/h, v gripu, repeatabilni


def _lane_init(params):
    return {"v0_mps": 16.666666666666668, "gear0": "auto"}


def _lane_driver(t, state, ctrl, params):
    # Tempomat 60 km/h.
    err = 16.666666666666668 - state["u"]
    ctrl["cruise_i"] = _clamp(ctrl.get("cruise_i", 0.0) + err * ctrl["dt"],
                              -2.0, 2.0)
    u_cmd = 0.35 * err + 0.25 * ctrl["cruise_i"]
    throttle = _clamp(u_cmd, 0.0, 1.0)
    brake = _clamp(-u_cmd, 0.0, 0.6)
    # Replay volantu: 1 perioda sinu (deterministicky v case).
    # Amplituda zadana v radianech; prepočet na normovany povel
    # kompenzuje rychlostni orez v _steering_step.
    st = params["steering"]
    vmax_a = st["max_angle_deg"] * math.pi / 180.0
    cap = 1.0 + (state["u"] / st["speed_ref_mps"]) ** 2
    if LANE_T0 <= t <= LANE_T0 + LANE_T:
        rad = LANE_A_RAD * math.sin(2.0 * math.pi * (t - LANE_T0) / LANE_T)
        steer = _clamp(rad * cap / vmax_a, -1.0, 1.0)
    else:
        steer = 0.0
    return throttle, brake, steer


def _lane_done(t, state, ctrl, params):
    return t >= 12.0


# ------------------------------------------------------- S7 nerovnosti
BUMP_V_MPS = 16.666666666666668


def _bump_init(params):
    return {"v0_mps": BUMP_V_MPS, "gear0": "auto"}


def _bump_driver(t, state, ctrl, params):
    err = BUMP_V_MPS - state["u"]
    ctrl["cruise_i"] = _clamp(ctrl.get("cruise_i", 0.0) + err * ctrl["dt"],
                              -2.0, 2.0)
    u_cmd = 0.35 * err + 0.25 * ctrl["cruise_i"]
    throttle = _clamp(u_cmd, 0.0, 1.0)
    brake = _clamp(-u_cmd, 0.0, 0.6)
    return throttle, brake, 0.0


def _bump_done(t, state, ctrl, params):
    return t >= 25.0 or state["x"] >= 400.0


_SCENARIO_DEFS = {
    "straight_accel": {"init": _accel_init, "driver": _accel_driver,
                       "done": _accel_done},
    "straight_brake_100_0": {"init": _brake_init, "driver": _brake_driver,
                             "done": _brake_done},
    "constant_radius_turn": {"init": _turn_init, "driver": _turn_driver,
                             "done": _turn_done},
    "lane_change": {"init": _lane_init, "driver": _lane_driver,
                    "done": _lane_done},
    "bump_section": {"init": _bump_init, "driver": _bump_driver,
                     "done": _bump_done},
}


def get_scenario(scenario_id):
    """Vrati definici scenare; KeyError pri neznamem id."""
    if scenario_id not in _SCENARIO_DEFS:
        raise KeyError("Neznamy scenar: %r (zname: %s)"
                       % (scenario_id, ", ".join(SCENARIOS)))
    return _SCENARIO_DEFS[scenario_id]

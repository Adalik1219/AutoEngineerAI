"""VehicleConfig (§3.3) — nacteni, defaulty, ukazkovy MX-5-like config.

Format VehicleConfig (ARCHITECTURE §3.3): parameters.engine /
transmission / tires / suspension / steering / brakes. Chybejici pole
doplni defaulty; nic se neodhaduje potichu — defaulty jsou explicitni
nize a manifest loguje, ktera byla pouzita (viz run.py).
"""

import copy
import json

G = 9.81

# Ukazkovy config: Mazda MX-5 ND2 2.0 6MT (EU), dle vehicle-data/references.
# Hodnoty z example-vehicle.json (overeny fakt), zbytek explicitni default.
SAMPLE_MX5_CONFIG = {
    "config_id": "cfg_sample_mx5_nd2",
    "parent_config_id": None,
    "vehicle_profile_id": "vp_sample_mx5_nd2",
    "chassis_adapter": "local-sim-v1",
    "parameters": {
        "mass": {"total_kg": 1150.0, "cog_a_m": 1.155, "cog_b_m": 1.155,
                 "cog_h_m": 0.46, "yaw_inertia_kgm2": 1550.0,
                 "pitch_inertia_kgm2": 1500.0, "roll_inertia_kgm2": 500.0,
                 "sprung_kg": 990.0},
        "dimensions": {"wheelbase_m": 2.31, "track_f_m": 1.495,
                       "track_r_m": 1.505},
        "engine": {"peak_torque_nm": 205.0, "peak_power_kw": 135.0,
                   "idle_rpm": 900.0, "redline_rpm": 7500.0,
                   "shift_rpm": 6800.0},
        "transmission": {"gears": [3.36, 2.05, 1.48, 1.17, 1.00, 0.83],
                         "final_drive": 2.866, "efficiency": 0.90,
                         "drive": "RWD", "shift_time_s": 0.35},
        "tires": {"grip_long": 1.0, "grip_lat": 1.0, "mu_road": 1.0,
                  "radius_m": 0.31, "inertia_kgm2": 1.2,
                  "mf_B_long": 12.0, "mf_C_long": 1.40,
                  "mf_B_lat": 10.0, "mf_C_lat": 1.35},
        "suspension": {"spring_f_Npm": 34000.0, "spring_r_Npm": 26000.0,
                       "damper_f_bump_Nspm": 2200.0,
                       "damper_f_reb_Nspm": 3200.0,
                       "damper_r_bump_Nspm": 1800.0,
                       "damper_r_reb_Nspm": 2600.0,
                       "travel_bump_m": 0.07, "travel_droop_m": -0.06,
                       "arb_roll_Nm_per_rad": 2500.0},
        "steering": {"max_angle_deg": 32.0, "max_rate_radps": 1.5,
                     "speed_ref_mps": 22.0},
        "brakes": {"bias_front": 0.6, "torque_Nm": 4000.0},
        "aero": {"rho_kgpm3": 1.225, "CdA_m2": 0.72, "Crr": 0.012},
        "geometry_overrides": None,
    },
    "rationale": "Ukazkovy config pro selftest sim-engine (agent C).",
    "model_patch_ref": None,
}


def _merge(base, override):
    """Rekurzivni merge dictu (override vyhrava). Deterministicky."""
    out = copy.deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def load_config(path):
    """Nacte VehicleConfig JSON ze souboru. Vrati (config, used_defaults)."""
    with open(path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    return resolve_params(cfg)


def resolve_params(cfg):
    """Doplni defaulty ze SAMPLE_MX5_CONFIG. Vrati (config, used_defaults).

    used_defaults = serazeny seznam teckovanych cest parametru, ktere
    config neobsahoval a byly doplneny (jde do manifestu).
    """
    cfg = copy.deepcopy(cfg)
    defaults = SAMPLE_MX5_CONFIG["parameters"]
    params = cfg.get("parameters", {}) or {}
    merged, used = _resolve_section(params, defaults, "")
    cfg["parameters"] = merged
    if "config_id" not in cfg:
        cfg["config_id"] = "cfg_unnamed"
    return cfg, sorted(used)


def _resolve_section(params, defaults, prefix):
    merged = {}
    used = []
    for key, dval in defaults.items():
        path = prefix + key
        if key not in params or params[key] is None:
            merged[key] = copy.deepcopy(dval)
            used.append(path)
        elif isinstance(dval, dict) and isinstance(params[key], dict):
            merged[key], sub = _resolve_section(params[key], dval, path + ".")
            used.extend(sub)
        else:
            merged[key] = copy.deepcopy(params[key])
    for key, val in params.items():
        if key not in defaults:
            merged[key] = copy.deepcopy(val)
    return merged, used


def validate_params(params):
    """Fail-fast validace zakladnich mezi. Vraci seznam chyb (prazdny = OK)."""
    errors = []

    def check(path, cond, msg):
        if not cond:
            errors.append("%s: %s" % (path, msg))

    eng = params["engine"]
    check("engine.peak_torque_nm", eng["peak_torque_nm"] > 0, "musi byt > 0")
    check("engine.peak_power_kw", eng["peak_power_kw"] > 0, "musi byt > 0")
    gears = params["transmission"]["gears"]
    check("transmission.gears", len(gears) >= 1, "aspon 1 stupen")
    check("transmission.gears", all(g > 0 for g in gears), "prevody > 0")
    check("transmission.gears",
          all(gears[i] >= gears[i + 1] for i in range(len(gears) - 1)),
          "prevody musi klesat")
    check("tires.grip_long", 0.0 < params["tires"]["grip_long"] <= 2.0,
          "mimo (0, 2]")
    check("tires.grip_lat", 0.0 < params["tires"]["grip_lat"] <= 2.0,
          "mimo (0, 2]")
    check("suspension.spring_f_Npm", params["suspension"]["spring_f_Npm"] >= 1000,
          "podezrele mpository (< 1000 N/m, guard dle KT Springs)")
    check("brakes.bias_front", 0.0 <= params["brakes"]["bias_front"] <= 1.0,
          "mimo [0, 1]")
    check("mass.total_kg", params["mass"]["total_kg"] > 0, "musi byt > 0")
    return errors

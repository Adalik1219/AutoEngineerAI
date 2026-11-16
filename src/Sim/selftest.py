"""Selftest sim-engine: 3 scenare na ukazkovem MX-5 configu + determinismus.

Beh: python -m src.Sim.selftest
Exit 0 = vse prošlo; jinak exit 1 s duvodem na stderr.
Kontroluje: sloupce CSV, konecnost hodnot, zakladni fyzikalni sanity
(akcelerace jede vpred, brzda zastavi, zatacka zataci), bitovy
determinismus (2 behy, sha256).
"""

import csv
import hashlib
import json
import math
import os
import sys
import tempfile

from .config import SAMPLE_MX5_CONFIG
from .run import DEFAULT_DT, run_scenario

SELFTEST_SCENARIOS = ["straight_accel", "straight_brake_100_0",
                       "constant_radius_turn"]

EXPECTED_COLUMNS = [
    "time_s", "x_m", "y_m", "v_mps", "a_long_mps2", "a_lat_mps2",
    "yaw_rad", "yaw_rate_radps", "steer_rad", "throttle", "brake", "gear",
    "engine_rpm", "engine_torque_nm",
    "omega_FL", "omega_FR", "omega_RL", "omega_RR",
    "slip_FL", "slip_FR", "slip_RL", "slip_RR",
    "fz_FL", "fz_FR", "fz_RL", "fz_RR",
    "travel_FL", "travel_FR", "travel_RL", "travel_RR",
]


def _fail(msg):
    print("SELFTEST FAIL: " + msg, file=sys.stderr)
    return 1


def _read_csv(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = [[float(x) if i != 11 else x for i, x in enumerate(r)]
                for r in reader]
    return header, rows


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _check_common(scenario_id, csv_path, manifest):
    if manifest["mode"] != "local-sim":
        return "mode != local-sim"
    if manifest["abort"]["flag"]:
        return "abort: %s" % manifest["abort"]["reason"]
    header, rows = _read_csv(csv_path)
    if header != EXPECTED_COLUMNS:
        return "spatne sloupce: %s" % header
    if len(rows) < 100:
        return "malo radku: %d" % len(rows)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            if j == 11:  # gear je int retezec
                continue
            if not math.isfinite(val):
                return "nekonecno r%d c%d" % (i, j)
    times = [r[0] for r in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        return "cas neni rostouci"
    dt = manifest["dt"]
    if abs((times[1] - times[0]) - dt) > 1e-12:
        return "prvni krok neodpovida dt"
    for key in ("code_version", "seed", "scenario_version", "mode"):
        if key not in manifest:
            return "manifest bez %s" % key
    return None


def _check_physics(scenario_id, rows):
    vmax = max(r[3] for r in rows)
    if scenario_id == "straight_accel":
        if vmax < 27.78:
            return ("nedosazeno 100 km/h (vmax=%.2f)" % vmax, None)
        t100 = next(r[0] for r in rows if r[3] >= 27.78)
        if not (3.0 <= t100 <= 25.0):
            return ("podezrely t_0_100 = %.2f s" % t100, None)
        if rows[-1][1] <= 50.0:
            return ("auto nejede vpred (x=%.1f)" % rows[-1][1], None)
    elif scenario_id == "straight_brake_100_0":
        if abs(rows[0][3] - 27.78) > 0.5:
            return ("spatna vstupni rychlost %.2f" % rows[0][3], None)
        if rows[-1][3] >= 0.5:
            return ("auto nezastavilo (v=%.2f)" % rows[-1][3], None)
        dist = rows[-1][1] - rows[0][1]
        if not (20.0 <= dist <= 120.0):
            return ("podezrela brzdna draha %.1f m" % dist, None)
    elif scenario_id == "constant_radius_turn":
        tail = rows[int(len(rows) * 0.5):]
        mean_alat = sum(abs(r[5]) for r in tail) / len(tail)
        if mean_alat < 2.0:
            return ("mala lateralka v oblouku (%.2f)" % mean_alat, None)
        if abs(rows[-1][6]) < 1.0:
            return ("auto nezataci (yaw=%.2f)" % rows[-1][6], None)
    return None, vmax


def main():
    tmp = tempfile.mkdtemp(prefix="sim_selftest_")
    cfg_path = os.path.join(tmp, "sample_mx5_config.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(SAMPLE_MX5_CONFIG, fh, indent=2, sort_keys=True)
    results = {}
    for sid in SELFTEST_SCENARIOS:
        out = os.path.join(tmp, sid)
        try:
            csv_path, mpath, manifest = run_scenario(
                cfg_path, sid, DEFAULT_DT, 1, out)
        except Exception as exc:  # noqa: BLE001
            return _fail("%s: vyjimka %r" % (sid, exc))
        err = _check_common(sid, csv_path, manifest)
        if err is not None:
            return _fail("%s: %s" % (sid, err))
        _, rows = _read_csv(csv_path)
        perr, _ = _check_physics(sid, rows)
        if perr is not None:
            return _fail("%s: %s" % (sid, perr))
        results[sid] = (csv_path, manifest, rows)
        print("SELFTEST %s: OK rows=%d dur=%.2fs sha=%s"
              % (sid, manifest["rows"], manifest["duration_s"],
                 manifest["telemetry_sha256"][:16]))
    # Determinismus: 2 behy straight_accel, stejny seed -> stejny sha.
    out2 = os.path.join(tmp, "straight_accel_rep")
    _, _, manifest2 = run_scenario(cfg_path, "straight_accel",
                                   DEFAULT_DT, 1, out2)
    _, _, manifest3 = run_scenario(cfg_path, "straight_accel",
                                   DEFAULT_DT, 1, out2 + "_b")
    h1 = results["straight_accel"][1]["telemetry_sha256"]
    if manifest2["telemetry_sha256"] != h1:
        return _fail("determinismus: opak behu ma jiny sha")
    if manifest3["telemetry_sha256"] != h1:
        return _fail("determinismus: 3. beh ma jiny sha")
    print("SELFTEST determinism: OK sha=%s (3 identicke behy)" % h1[:16])
    # Klicove metriky do reportu.
    _, rows_a = results["straight_accel"][0], results["straight_accel"][2]
    t100 = next(r[0] for r in rows_a if r[3] >= 27.78)
    rows_b = results["straight_brake_100_0"][2]
    dist = rows_b[-1][1] - rows_b[0][1]
    rows_c = results["constant_radius_turn"][2]
    alat = sum(abs(r[5]) for r in rows_c[int(len(rows_c) * 0.5):])
    alat /= len(rows_c[int(len(rows_c) * 0.5):])
    print("METRICS t_0_100_s=%.3f brake_100_0_m=%.2f a_lat_turn=%.2f" %
          (t100, dist, alat))
    print("SELFTEST PASS (3 scenare + determinismus)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

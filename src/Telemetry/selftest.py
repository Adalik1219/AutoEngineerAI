"""Selftest Telemetry: synteticke CSV (idealni + nestabilni + chamtivy beh).

Overuje: skore nestabilniho behu je horsi, chranena metrika ho shodi (A2/A3),
rychlejsi-ale-nebezpecny beh projde A1 a padne na A2. Exit 0 = vse proslo.
Pouziti: python selftest.py  (pise jen do docasneho adresare + stdout)
"""

import csv
import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluate import evaluate
from metrics import TELEMETRY_COLUMNS

DT = 1.0 / 60.0
K_US = 0.008  # smernice steer = K_US * a_lat (nedotacivy vuz)


def _row(t, x, y, v, a_long, a_lat, yaw, yaw_rate, steer, throttle, brake,
         gear, rpm, tq, slip, travel):
    om = v / 0.33  # omega z valiveho polomeru 0.33 m
    return {
        "time_s": t, "x_m": x, "y_m": y, "v_mps": max(v, 0.0),
        "a_long_mps2": a_long, "a_lat_mps2": a_lat,
        "yaw_rad": yaw, "yaw_rate_radps": yaw_rate, "steer_rad": steer,
        "throttle": throttle, "brake": brake, "gear": gear,
        "engine_rpm": rpm, "engine_torque_nm": tq,
        "omega_FL": om, "omega_FR": om, "omega_RL": om, "omega_RR": om,
        "slip_FL": slip, "slip_FR": slip, "slip_RL": slip, "slip_RR": slip,
        "fz_FL": 3500.0, "fz_FR": 3500.0, "fz_RL": 3500.0, "fz_RR": 3500.0,
        "travel_FL": travel, "travel_FR": travel,
        "travel_RL": travel, "travel_RR": travel,
    }


def gen_trace(kind):
    """Synteticka stopa: akcelerace -> ustaleny oblouk -> brzdeni -> V-max.

    kind: 'ideal' (referencni), 'unstable' (zname defekty: spin yaw, prokluz,
    dosednuti podvozku, delsi brzdeni), 'greedy' (lepsi akcelerace, ale brzdeni
    +1.9 % nad baseline -> musi padnout na A2 i pri lepsim skore).
    """
    tau = {"ideal": 3.0, "unstable": 4.5, "greedy": 2.6}[kind]
    decel = {"ideal": 9.0, "unstable": 7.5, "greedy": 8.82}[kind]
    rows = []
    # Faze A: akcelerace z 0 na ~100 km/h (v = 30*(1-exp(-t/tau)), cap 27.78).
    t, x, y, yaw, v = 0.0, 0.0, 0.0, 0.0, 0.0
    while v < 27.78:
        v = 30.0 * (1.0 - math.exp(-t / tau))
        a = (30.0 / tau) * math.exp(-t / tau)
        slip = 0.02 if kind == "ideal" else (0.45 if kind == "unstable" else 0.03)
        rows.append(_row(t, x, y, v, a, 0.0, yaw, 0.0, 0.0, 1.0, 0.0,
                         2, 3500.0, 250.0, slip, 0.03))
        x += v * DT
        t += DT
    # Faze B: ustaleny oblouk pri 100 km/h, stupne volantu (pro K_us regresi).
    for step in range(6):
        steer = step * 0.01
        a_lat = steer / K_US
        for _ in range(120):  # 2 s na stupen
            yaw_rate = a_lat / 27.78
            if kind == "unstable":
                # Defekt: oscilace + spin prekracujici 120 °/s.
                k = len(rows)
                yaw_rate += 0.5 * math.sin(k * 0.3)
                if 700 < k < 730:
                    yaw_rate = 2.5
                a_lat_out = a_lat + (2.0 if 700 < k < 730 else 0.0)
            else:
                a_lat_out = a_lat
            yaw += yaw_rate * DT
            x += 27.78 * DT
            travel = (0.1195 if (kind == "unstable" and step >= 4)
                      else 0.03)  # defekt: dosednuti (limit 0.12 - 2 mm)
            slip = (0.30 if kind == "unstable" else 0.02)
            rows.append(_row(t, x, y, 27.78, 0.0, a_lat_out, yaw, yaw_rate,
                             steer, 0.15, 0.0, 5, 3000.0, 120.0, slip, travel))
            t += DT
    # Faze C: brzdeni 100-0 plnou brzdou.
    v = 27.78
    while v > 0.0:
        v = max(0.0, v - decel * DT)
        slip = (0.40 if kind == "unstable" else 0.08)
        rows.append(_row(t, x, y, v, -decel, 0.0, yaw, 0.0, 0.0, 0.0, 1.0,
                         3, 2000.0, 0.0, slip, 0.04))
        x += v * DT
        t += DT
    # Faze D: nova akcelerace + ustalenych 55 m/s (198 km/h) pro V-max.
    v = 0.0
    t_launch = t
    while t - t_launch < 25.0:
        v = min(55.0, v + 4.0 * DT)
        thr = 1.0 if v < 55.0 else 0.35
        rows.append(_row(t, x, y, v, 0.0, 0.0, yaw, 0.0, 0.0, thr, 0.0,
                         6, 5500.0, 200.0, 0.02, 0.03))
        x += v * DT
        t += DT
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(TELEMETRY_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def reference_profile():
    return {
        "vehicle": {"make": "synthetic", "model": "selftest", "year": 2026},
        "config_id": "cfg_selftest",
        "scenario_id": "full_matrix_synth",
        "mode": "local-sim",
        "seed": 1,
        "code_version": "selftest",
        "suspension_travel_limit_m": 0.12,
        "target_metrics": [
            {"metric": "t_0_60_s", "target": 2.5, "tolerance": 0.3},
            {"metric": "t_0_100_s", "target": 7.8, "tolerance": 0.5},
            {"metric": "v_max_kmh", "target": 198.0, "tolerance": 5.0},
            {"metric": "brake_distance_100_0_m", "target": 43.0, "tolerance": 1.5},
            {"metric": "a_lat_max_mps2", "target": 6.25, "tolerance": 0.5},
            {"metric": "yaw_rate_variance", "target": 0.0, "tolerance": 0.001},
            {"metric": "slip_max_abs", "target": 0.10, "tolerance": 0.05},
            {"metric": "susp_travel_max_m", "target": 0.05, "tolerance": 0.02},
            {"metric": "susp_bottoming_count", "target": 0, "tolerance": 1},
        ],
    }


def main():
    tmp = tempfile.mkdtemp(prefix="telemetry_selftest_")
    paths = {}
    for kind in ("ideal", "unstable", "greedy"):
        path = os.path.join(tmp, kind + ".csv")
        write_csv(path, gen_trace(kind))
        paths[kind] = path

    ref = reference_profile()
    ideal = evaluate(paths["ideal"], ref)

    # Baseline = idealni beh (aktualni best); kandidati se hodnoti vuci nemu.
    ref_base = dict(reference_profile())
    ref_base["baseline_metrics"] = ideal["metrics"]
    ideal_b = evaluate(paths["ideal"], ref_base)
    unstable = evaluate(paths["unstable"], ref_base)
    greedy = evaluate(paths["greedy"], ref_base)

    print("== RAW metriky: ideal ==")
    print(json.dumps(ideal["metrics"], indent=1, default=str))
    print("== RAW metriky: unstable ==")
    print(json.dumps(unstable["metrics"], indent=1, default=str))
    print("== Skore: ideal=%.4f unstable=%.4f greedy=%.4f" % (
        ideal_b["total_score"], unstable["total_score"], greedy["total_score"]))
    print("== Verdikty: ideal=%s unstable=%s greedy=%s" % (
        ideal_b["verdicts"], unstable["verdicts"], greedy["verdicts"]))

    checks = [
        ("ideal neni unstable", not ideal_b["metrics"]["unstable"]),
        ("ideal bez baseline prijat (A2/A3 vuci targetum)",
         ideal["verdicts"]["accepted"]),
        ("ideal vs vlastni baseline padne na A1 (neni zlepseni)",
         ideal_b["verdicts"]["failed_condition"] == "A1_TOTAL_SCORE"),
        ("unstable je unstable", unstable["metrics"]["unstable"]),
        ("skore unstable horsi nez ideal",
         unstable["total_score"] > ideal_b["total_score"]),
        ("unstable zamitnut", not unstable["verdicts"]["accepted"]),
        ("unstable padl na A3/A2",
         (unstable["verdicts"]["failed_condition"] or "").startswith(("A3", "A2"))),
        ("greedy ma lepsi skore nez ideal",
         greedy["total_score"] < ideal_b["total_score"]),
        ("greedy presto zamitnut na A2 (brzda +1 %)",
         greedy["verdicts"]["failed_condition"] == "A2_HARD_LIMIT:brake_distance_100_0_m"),
        ("K_us idealniho ~0.008",
         abs((ideal["metrics"]["understeer_gradient"] or 0) - K_US) < 0.002),
        ("bottoming unstable > 0", unstable["metrics"]["susp_bottoming_count"] > 0),
        ("slip unstable > slip ideal",
         unstable["metrics"]["slip_max_abs"] > ideal["metrics"]["slip_max_abs"]),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    if failed:
        print("SELFTEST FAILED: %d kontrol" % len(failed))
        return 1
    print("SELFTEST OK: vsech %d kontrol proslo" % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())

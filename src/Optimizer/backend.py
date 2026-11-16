"""Napojeni pipeline: simulate (src/Sim) -> evaluate (src/Telemetry) -> propose.

Priorita: externi src/Sim.run_scenario (Agent C), pokud je importovatelny
a vrati platne CSV (overeno hlavickou Agenta F); jinak fallback-synth-v0
z fallback_sim.py. Vyhodnoceni vzdy pres src/Telemetry/evaluate.py
(Agent F, single-run A1–A3 + TotalScore); opakovani a A4/A5 ridi optimizer.
Normalizace nazvu metrik: reference pouzivaji aliasy (accel_0_100_s,
vmax_kmh, brake_100_0_m), telemetrie kanonicke nazvy (t_0_100_s, v_max_kmh,
brake_distance_100_0_m). Pouze stdlib + importy sourozencu (read-only).
"""

import importlib
import os

from .fallback_sim import synth_accel_rows, synth_brake_rows, write_csv
from .statistics import median

try:
    from src.Telemetry.evaluate import (
        GROUP_WEIGHTS,
        HARD_LIMITS_DEFAULT,
        HIGHER_BETTER,
        METRIC_GROUPS,
        evaluate,
    )
    HAVE_TELEMETRY = True
except Exception as exc:
    HAVE_TELEMETRY = False
    TELEMETRY_IMPORT_ERROR = str(exc)
    GROUP_WEIGHTS = {
        "performance": 0.25, "braking": 0.20, "handling": 0.25,
        "suspension": 0.10, "traction": 0.10, "robustness": 0.10,
    }
    HARD_LIMITS_DEFAULT = {
        "brake_distance_100_0_m": {"rel": 0.01},
        "yaw_rate_max_abs": {"rel": 0.05},
        "slip_max_abs": {"rel": 0.05},
        "susp_bottoming_count": {"abs": 0},
    }
    HIGHER_BETTER = {"v_max_mps", "v_max_kmh", "a_lat_max_mps2", "mean_decel_mps2"}
    METRIC_GROUPS = {
        "t_0_60_s": "performance", "t_0_100_s": "performance",
        "v_max_kmh": "performance", "brake_distance_100_0_m": "braking",
        "stopping_time_s": "braking",
    }

    def evaluate(_csv, _profile):
        # Nedosazitelne: make_evaluator bez src/Telemetry odmitne start.
        # Navrat {} jen pro typovou kontrolu.
        return {}

# Scenare rychle matice (TESTING-OPTIMIZATION §3: S1 + S3-dry) + bodovane
# metriky kazdeho scenare. DUVOD: V-max se nesmi bodovat z brzdneho behu
# (v behu S3 auto nikdy nejede 219 km/h) a t_0_100 se neboduje z brzdeni.
# Bez tohoto deleni by S3 dominovala S a margin A1 by byl nekonecny.
SCENARIOS = [
    {"scenario_id": "S1_accel", "kind": "straight_accel", "duration_s": 45.0},
    {"scenario_id": "S3_brake", "kind": "straight_brake_100_0", "duration_s": 8.0},
]
SCENARIO_METRICS = {
    "straight_accel": {"t_0_60_s", "t_0_100_s", "v_max_mps", "v_max_kmh"},
    "straight_brake_100_0": {"brake_distance_100_0_m", "stopping_time_s",
                             "mean_decel_mps2"},
}

# Aliasy referencnich nazvu -> kanonicke nazvy telemetrie.
METRIC_ALIASES = {
    "accel_0_100_s": "t_0_100_s",
    "accel_0_60_s": "t_0_60_s",
    "t_0_100_s": "t_0_100_s",
    "t_0_60_s": "t_0_60_s",
    "vmax_kmh": "v_max_kmh",
    "v_max_kmh": "v_max_kmh",
    "v_max_mps": "v_max_mps",
    "brake_100_0_m": "brake_distance_100_0_m",
    "brake_distance_100_0_m": "brake_distance_100_0_m",
    "stopping_time_s": "stopping_time_s",
    "mean_decel_mps2": "mean_decel_mps2",
    "a_lat_max_mps2": "a_lat_max_mps2",
    "yaw_rate_max_abs": "yaw_rate_max_abs",
    "slip_max_abs": "slip_max_abs",
    "slip_time_over_02_s": "slip_time_over_02_s",
    "susp_bottoming_count": "susp_bottoming_count",
    "susp_travel_max_m": "susp_travel_max_m",
    "yaw_rate_variance": "yaw_rate_variance",
}


def normalize_targets(raw_targets):
    """Prevod [{metric, target, tolerance, weight?}] na kanonicke nazvy."""
    out = []
    for spec in raw_targets:
        name = METRIC_ALIASES.get(spec["metric"])
        if name is None:
            continue  # nezname metriky optimizer neboduje (dokumentovano)
        out.append({
            "metric": name,
            "target": float(spec["target"]),
            "tolerance": float(spec["tolerance"]),
            "weight": float(spec.get("weight", 1.0)),
        })
    return out


def reference_from_rich_vehicle(rich):
    """Cile z bohateho zaznamu vehicle-data/references (MX-5 priklad).

    Tolerance dle prikladu Agenta E (contracts/examples/reference_profile).
    """
    perf = (rich.get("performance") or {})
    targets = []

    def num(node):
        if isinstance(node, dict):
            node = node.get("value")
        return None if node is None else float(node)

    accel = num(perf.get("accel_0_100"))
    if accel is not None:
        targets.append({"metric": "accel_0_100_s", "target": accel,
                        "tolerance": 0.5, "weight": 1.0})
    vmax = num(perf.get("vmax"))
    if vmax is not None:
        targets.append({"metric": "vmax_kmh", "target": vmax,
                        "tolerance": 5.0, "weight": 0.8})
    brake = num(perf.get("braking_100_0"))
    if brake is not None:
        targets.append({"metric": "brake_100_0_m", "target": brake,
                        "tolerance": 2.0, "weight": 0.9})
    return normalize_targets(targets)


def load_reference_targets(path_or_doc):
    """Nacte cile z JSON: bud rp-format (target_metrics), nebo rich-format."""
    import json
    doc = path_or_doc
    if isinstance(doc, str):
        with open(doc, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    if isinstance(doc.get("target_metrics"), list):
        return normalize_targets(doc["target_metrics"])
    return reference_from_rich_vehicle(doc)


def find_external_sim():
    """Hledani src/Sim (Agent C). Vraci (fn|None, info).

    fn(config, scenario, seed, out_csv) -> out_csv; povinne overeni vystupu
    hlavickou Agenta F, jinak se povazuje za nefunkcni.
    """
    candidates = [
        ("src.Sim.api", "run_scenario"),
        ("src.Sim.simulation", "run_scenario"),
        ("src.Sim.engine", "run_scenario"),
        ("src.Sim", "run_scenario"),
    ]
    for mod_name, attr in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, attr, None)
            if callable(fn):
                return fn, {"module": mod_name, "func": attr}
        except Exception:
            continue
    return None, {"module": None, "reason": "src.Sim.run_scenario nenalezeno"}


def _scenario_seed(base_seed, scenario_id, rep):
    return int(base_seed) * 1000 + abs(hash(scenario_id)) % 100 + int(rep)


def make_evaluator(out_dir, targets, repeats=5, base_seed=7, code_version="optimizer-v0"):
    """Tovarna evaluate_config(config, seed_offset=0) -> agregace pro A1–A5.

    Pro kazdy scenar × opakovani: CSV stopa (externi Sim nebo fallback),
    vyhodnoceni pres src/Telemetry/evaluate.py. Vraci agregaci:
    {"S", "rep_totals", "scenario_medians", "metric_medians", "unstable",
     "suspect", "aborts"}.
    """
    if not HAVE_TELEMETRY:
        raise RuntimeError("src/Telemetry chybi: %s" % TELEMETRY_IMPORT_ERROR)
    telemetry_dir = os.path.join(out_dir, "telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)
    ext_fn, ext_info = find_external_sim()
    backend = "external-src.Sim" if ext_fn else "fallback-synth-v0"

    base_profile = {"target_metrics": targets, "mode": "local-sim",
                    "code_version": code_version}

    def run_one(config, scenario, rep, seed_offset, baseline_metrics):
        seed = _scenario_seed(base_seed + seed_offset, scenario["scenario_id"], rep)
        csv_path = os.path.join(
            telemetry_dir,
            "%s_%s_r%d.csv" % (config["config_id"], scenario["scenario_id"], rep))
        used = backend
        if ext_fn is not None:
            try:
                ext_fn(config, scenario, seed, csv_path)
                _validate_csv(csv_path)
            except Exception:
                used = "fallback-synth-v0"
        if used == "fallback-synth-v0":
            if scenario["kind"] == "straight_accel":
                rows = synth_accel_rows(config, seed, scenario["duration_s"])
            else:
                rows = synth_brake_rows(config, seed)
            write_csv(csv_path, rows)
        profile = dict(base_profile)
        profile.update({
            "config_id": config["config_id"],
            "scenario_id": scenario["scenario_id"],
            "seed": seed,
            "baseline_metrics": baseline_metrics,
            # Bodovane metriky scenare (S1: vykon, S3: brzdeni).
            "target_metrics": [t for t in targets
                               if t["metric"] in SCENARIO_METRICS[scenario["kind"]]],
        })
        result = evaluate(csv_path, profile)
        return result, used

    def evaluate_config(config, seed_offset=0, baseline_metrics=None):
        rep_totals = []
        scen_totals = {}
        scen_rep_totals = {}
        scen_metric_medians = {}
        metric_vals = {}
        unstable = 0
        suspect = 0
        backends = set()
        for scenario in SCENARIOS:
            totals = []
            scen_vals = {}
            for rep in range(repeats):
                result, used = run_one(config, scenario, rep, seed_offset,
                                       baseline_metrics)
                backends.add(used)
                totals.append(float(result["total_score"]))
                rep_totals.append(float(result["total_score"]))
                if result["verdicts"]["unstable"]:
                    unstable += 1
                if result["verdicts"].get("suspect"):
                    suspect += 1
                for metric, value in (result.get("metrics") or {}).items():
                    if isinstance(value, bool) or value is None:
                        continue
                    if isinstance(value, (int, float)):
                        scen_vals.setdefault(metric, []).append(float(value))
            scen_totals[scenario["scenario_id"]] = median(totals)
            scen_rep_totals[scenario["scenario_id"]] = list(totals)
            scen_metric_medians[scenario["scenario_id"]] = {
                m: median(v) for m, v in scen_vals.items()}
        metric_medians = {}
        for scen_meds in scen_metric_medians.values():
            for m, v in scen_meds.items():
                metric_vals.setdefault(m, []).append(v)
        # Poolovane mediany jen pro metriky z jedineho scenare (jinak by
        # mesily meritelne nesmysly, napr. V-max z brzdneho behu).
        for m, v in metric_vals.items():
            if len(v) == 1:
                metric_medians[m] = v[0]
        scored = sorted(scen_totals.values())
        return {
            "S": sum(scored) / len(scored),
            "rep_totals": rep_totals,
            "scenario_rep_totals": scen_rep_totals,
            "scenario_medians": scen_totals,
            "scenario_metric_medians": scen_metric_medians,
            "metric_medians": metric_medians,
            "unstable": unstable,
            "suspect": suspect,
            "aborts": 0,
            "backend": "+".join(sorted(backends)),
        }

    info = {"backend": backend, "external": ext_info,
            "telemetry": "src.Telemetry.evaluate"}
    return evaluate_config, info


def _validate_csv(path):
    """Kontrola hlavicky CSV proti Agentu F (odmitne cizi formaty)."""
    try:
        from src.Telemetry.metrics import TELEMETRY_COLUMNS, load_telemetry
    except Exception as exc:
        raise ValueError("validace CSV bez src/Telemetry: %s" % exc)
    rows = load_telemetry(path)
    if not rows:
        raise ValueError("prazdna telemetrie")
    return True

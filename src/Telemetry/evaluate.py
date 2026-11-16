"""Vyhodnoceni telemetrie -> TestResult (§3.5 ARCHITECTURE.md, §4.3–4.4 a §5.3 TESTING-OPTIMIZATION.md).

evaluate(telemetry_csv, reference_profile) -> TestResult (dict, JSON-serializovatelny).
Skore: nizsi TotalScore = lepsi (soucet vazenych normalizovanych odchylek + penalizace).
Vystupni `score` (kontrakt contracts/test_result.schema.json, 0..1, vyssi=lepsi)
je monotoni zobrazeni TotalScore: score = 1/(1+exp(total)).
total=0 -> 0.5, total->-inf -> 1 (lepsi nez cil), total->+inf -> 0 (horsi).
Mapovani je ryze monotonni (poradi kandidatu shodne s TotalScore); vnitrni
rozhodovani (A1), optimizer i reporty dale pracuji s TotalScore (lower-better).
Chranene metriky: kandidat nesmi zhorsit nad hard_limit ani pri lepsim skore (A2).
"""

import hashlib
import json
import math
import os

try:
    from .metrics import compute_metrics, load_telemetry
except ImportError:  # prime spousteni jako skript z vlastniho adresare
    from metrics import compute_metrics, load_telemetry

# §4.4: vahy skupin, soucet = 1. Inzenyrska priorita, verzovano (nemenit bez koordinátora).
GROUP_WEIGHTS = {
    "performance": 0.25,
    "braking": 0.20,
    "handling": 0.25,
    "suspension": 0.10,
    "traction": 0.10,
    "robustness": 0.10,
}

# Zarazeni metrik do skupin kapitoly 7.
METRIC_GROUPS = {
    "t_0_60_s": "performance",
    "t_0_100_s": "performance",
    "v_max_kmh": "performance",
    "brake_distance_100_0_m": "braking",
    "stopping_time_s": "braking",
    "a_lat_max_mps2": "handling",
    "yaw_rate_max_abs": "handling",
    "susp_travel_max_m": "suspension",
    "susp_bottoming_count": "suspension",
    "slip_max_abs": "traction",
    "slip_time_over_02_s": "traction",
    "yaw_rate_variance": "robustness",
}

# Vyssi hodnota = lepsi (odchylka se otaci: dev = (ref - m) / scale).
HIGHER_BETTER = {"v_max_mps", "v_max_kmh", "a_lat_max_mps2", "mean_decel_mps2"}

# tol_rel: 3 % casy/drahy/rychlosti, 5 % brzdeni, 10 % komfortni/RMS (§4.3).
TOL_REL = {
    "brake_distance_100_0_m": 0.05,
    "a_lat_max_mps2": 0.05,
    "slip_max_abs": 0.10,
    "slip_time_over_02_s": 0.10,
    "yaw_rate_variance": 0.10,
    "yaw_rate_max_abs": 0.10,
    "susp_travel_max_m": 0.10,
    "susp_bottoming_count": 0.0,
}
DEFAULT_TOL_REL = 0.03

# Chranene metriky + prahy (§5.3 A2: brzda +1 %, yaw +5 %, dosednuti/spin nulova tolerance).
HARD_LIMITS_DEFAULT = {
    "brake_distance_100_0_m": {"rel": 0.01},
    "yaw_rate_max_abs": {"rel": 0.05},
    "slip_max_abs": {"rel": 0.05},
    "susp_bottoming_count": {"abs": 0},
}

CRITICAL_PENALTY = 10.0  # §4.4: radove vic nez typicke GroupScore


def _deviation(metric, value, target, tolerance):
    """Relativni odchylka; kladna = horsi nez reference (oboji smery sjednoceny)."""
    rel = TOL_REL.get(metric, DEFAULT_TOL_REL)
    scale = max(tolerance, abs(target) * rel)
    if scale <= 0:
        scale = tolerance if tolerance > 0 else 1.0
    if metric in HIGHER_BETTER:
        return (target - value) / scale
    return (value - target) / scale


def _total_for(metrics_dict, targets, weights, unstable):
    """TotalScore pro libovolna metriky (i baseline) na stejnych tercich."""
    group_devs = {}
    for metric, spec in targets.items():
        if metric not in METRIC_GROUPS or metric not in metrics_dict:
            continue
        value = metrics_dict.get(metric)
        if value is None or isinstance(value, bool):
            continue
        dev = _deviation(metric, value, spec["target"], spec["tolerance"])
        group_devs.setdefault(METRIC_GROUPS[metric], []).append(dev)
    group_scores = {
        g: sum(d) / len(d) for g, d in group_devs.items() if d
    }
    present = [g for g in group_scores if g in weights]
    wsum = sum(weights[g] for g in present)
    total = (
        sum(weights[g] * group_scores[g] for g in present) / wsum
        if wsum > 0 else 0.0
    )
    if unstable:
        total += CRITICAL_PENALTY
    return total, group_scores


def _total_to_score(total):
    """Monotonni zobrazeni TotalScore (lower-better) do 0..1 (higher-better).

    score = 1/(1+exp(total)); ryze klesajici v total, tj. poradi kandidatu
    je shodne s TotalScore. Krajni hodnoty oriznuty pro exp-overflow.
    """
    total = float(total)
    if total >= 30.0:
        return 0.0
    if total <= -30.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(total))


def evaluate(telemetry_csv, reference_profile):
    """Spocita metriky z RAW CSV a vrati TestResult dle §3.5.

    reference_profile: dict nebo cesta k JSON. Klice:
      target_metrics: [{metric, target, tolerance, weight?}] (povinne pro skore),
      weights: volitelny prepis vah skupin,
      baseline_metrics: metriky aktualni best varianty (pro A1/A2; jinak se
        chranene metriky hlidaji vuci targetum a A1 se neaplikuje),
      hard_limits: volitelny prepis prahu chranenych metrik,
      config_id / scenario_id / scenario_version / seed / mode / code_version.
    """
    if isinstance(reference_profile, str):
        with open(reference_profile, "r", encoding="utf-8") as fh:
            reference_profile = json.load(fh)

    rows = load_telemetry(telemetry_csv)
    travel_limit = float(reference_profile.get("suspension_travel_limit_m", 0.12))
    metrics = compute_metrics(rows, travel_limit_m=travel_limit)

    weights = dict(GROUP_WEIGHTS)
    weights.update(reference_profile.get("weights", {}))

    targets = {}
    for spec in reference_profile.get("target_metrics", []):
        targets[spec["metric"]] = {
            "target": float(spec["target"]),
            "tolerance": float(spec["tolerance"]),
        }

    unstable = bool(metrics.get("unstable"))
    total, group_scores = _total_for(metrics, targets, weights, unstable)

    deviations = {}
    for metric, spec in targets.items():
        value = metrics.get(metric)
        if value is None or isinstance(value, bool):
            continue
        deviations[metric] = value - spec["target"]

    # --- Chranene metriky (A2): vuci baseline, jinak vuci targetu. ---
    baseline = reference_profile.get("baseline_metrics") or {}
    hard_limits = dict(HARD_LIMITS_DEFAULT)
    hard_limits.update(reference_profile.get("hard_limits", {}))
    protected = {}
    for metric, lim in hard_limits.items():
        value = metrics.get(metric)
        base = baseline.get(metric)
        if base is None and metric in targets:
            base = targets[metric]["target"]
        if value is None or base is None:
            protected[metric] = {"value": value, "limit": None, "ok": None,
                                 "note": "n/a"}
            continue
        if "abs" in lim:
            allowed = base + lim["abs"]
        else:
            allowed = base * (1.0 + lim["rel"]) if base >= 0 else base
        protected[metric] = {
            "value": value,
            "baseline": base,
            "limit": allowed,
            "ok": bool(value <= allowed),
        }

    # --- Akceptace (jednorazovy beh: A1–A3; A4/A5 vyzaduji opakovani/runtime). ---
    failed = None
    if unstable:
        failed = "A3_STABILITY"
    else:
        bad = next((m for m, p in protected.items() if p["ok"] is False), None)
        if bad is not None:
            failed = "A2_HARD_LIMIT:" + bad
    baseline_total = None
    if failed is None and baseline:
        b_metrics = {k: v for k, v in baseline.items()}
        baseline_total, _ = _total_for(b_metrics, targets, weights, False)
        margin = max(0.0, 0.005 * abs(baseline_total))
        if not (total < baseline_total - margin):
            failed = "A1_TOTAL_SCORE"
    accepted = failed is None

    with open(telemetry_csv, "rb") as fh:
        digest = hashlib.sha1(fh.read()).hexdigest()[:8]

    return {
        "schema_version": "1.0.0",
        "result_id": "tr_" + digest,
        "config_id": reference_profile.get("config_id", "cfg_unknown"),
        "scenario_id": reference_profile.get("scenario_id", "unknown"),
        "environment": {
            "mode": reference_profile.get("mode", "local-sim"),
            "seed": reference_profile.get("seed", 0),
            "code_version": reference_profile.get("code_version", "dev"),
        },
        "metrics": metrics,
        "deviations_vs_target": deviations,
        "group_scores": group_scores,
        "score": _total_to_score(total),
        "total_score": total,
        "baseline_total_score": baseline_total,
        "protected": protected,
        "verdicts": {
            "unstable": unstable,
            "unstable_reasons": metrics.get("unstable_reasons", []),
            "suspect": metrics.get("suspect", []),
            "accepted": accepted,
            "failed_condition": failed,
            "note": "A4 (Mann-Whitney, n>=5) a A5 (runtime brana) vyzaduji "
                    "opakovane/runtime behy – v single-run evaluate se nekontroluji.",
        },
        "reproduced_runs": 1,
        "raw_telemetry_ref": os.path.abspath(telemetry_csv),
    }

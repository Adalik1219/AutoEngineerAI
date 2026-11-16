#!/usr/bin/env python3
"""AutoEngineerAI end-to-end pipeline (Agent G): load -> simulate -> evaluate -> propose.

Cela optimalizacni kampan bez zasahu uzivatele:
  config (VehicleConfig JSON) -> stopy (src/Sim, pripadne fallback-synth-v0)
  -> TestResult (src/Telemetry/evaluate.py) -> propose/A1–A5 (src/Optimizer)
  -> best + historie (history.jsonl) + manifest.
Uroven dukazu je vzdy SIM (UNCONFIRMED_RUNTIME) – neni dukazem pro Roblox.
Prikazy: run | selftest | plan. Pouze stdlib, zadne git operace.
"""

import argparse
import copy
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Optimizer.backend import (  # noqa: E402
    GROUP_WEIGHTS,
    HARD_LIMITS_DEFAULT,
    SCENARIOS,
    load_reference_targets,
    make_evaluator,
)
from src.Optimizer.change_plan import plan_from_diagnosis  # noqa: E402
from src.Optimizer.optimizer import run_optimization  # noqa: E402
from src.Optimizer.search_space import get_param, search_space  # noqa: E402
from src.Optimizer.selftest import run_selftest  # noqa: E402
from src.Optimizer.store import VariantStore  # noqa: E402

CODE_VERSION = "autoengineer-pipeline-v0 (stdlib, bez git operaci)"


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_config(doc):
    """Doplni povinna pole VehicleConfig minimalnim schematem (neprepisuje)."""
    cfg = copy.deepcopy(doc)
    cfg.setdefault("schema_version", "1.0.0")
    cfg.setdefault("config_id", "cfg_input_base")
    cfg.setdefault("parent_config_id", None)
    cfg.setdefault("vehicle_profile_id", "vp_2026_mx5_demo")
    cfg.setdefault("chassis_adapter", "achassis-v1")
    params = cfg.setdefault("parameters", {})
    params.setdefault("engine", {}).setdefault("peak_torque_nm", 205.0)
    params["engine"].setdefault("peak_power_kw", 135.0)
    tra = params.setdefault("transmission", {})
    tra.setdefault("gears", [5.087, 2.991, 2.035, 1.594, 1.286, 1.0])
    tra.setdefault("final_drive", 2.866)
    tra.setdefault("shift_rpm", 7000.0)
    tra.setdefault("shift_time_s", 0.4)
    params.setdefault("tires", {}).setdefault("grip_long", 1.0)
    params["tires"].setdefault("grip_lat", 1.0)
    params.setdefault("suspension", {})
    params.setdefault("steering", {})
    params.setdefault("brakes", {}).setdefault("bias_front", 0.62)
    params.setdefault("geometry_overrides", None)
    cfg.setdefault("rationale", "vstupni konfigurace kampane autoengineer.py")
    return cfg


def default_out_dir(root):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return os.path.join(root, "vehicle-data", "runs", "run_%s" % stamp)


def cmd_run(args):
    config = normalize_config(load_json(args.config))
    targets = load_reference_targets(args.reference)
    if not targets:
        print("CHYBA: reference neobsahuje zadne bodovane metriky", file=sys.stderr)
        return 2
    out_dir = args.out or default_out_dir(ROOT)
    os.makedirs(out_dir, exist_ok=True)
    space = search_space(config)
    store = VariantStore(out_dir)
    evaluate_config, backend_info = make_evaluator(
        out_dir, targets, repeats=args.repeats, base_seed=args.seed,
        code_version=CODE_VERSION)
    outcome = run_optimization(config, space, evaluate_config, store,
                               targets, dict(HARD_LIMITS_DEFAULT),
                               max_evaluations=args.max_evaluations,
                               seed_offset=0)
    best = outcome["best_config"]
    counts = store.counts()
    run_id = os.path.basename(os.path.normpath(out_dir))
    if not run_id.startswith("run_"):
        run_id = "run_" + "".join(c if (c.isalnum() or c == "_") else "_"
                                  for c in run_id)
    manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "code_version": CODE_VERSION,
        "seed": args.seed,
        "scenario_versions": {s["scenario_id"]: {"kind": s["kind"],
                                                "duration_s": s["duration_s"]}
                              for s in SCENARIOS},
        # artifacts polozky smi mit vlastni rozsireni (additionalProperties: true).
        "artifacts": [
            {"kind": "history", "path": "history.jsonl"},
            {"kind": "best_config", "path": "best.json",
             "id": store.best_config_id},
            {"kind": "best_config", "path": "best_config.json",
             "id": store.best_config_id},
            {"kind": "report", "path": "report.json"},
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    # Plny kampanovy report (vlastni format pipeline, mimo manifest schema).
    report = {
        "level": "SIM (UNCONFIRMED_RUNTIME – neni dukaz pro Roblox)",
        "score_direction": "lower_better (TotalScore, souhlasne s Telemetry)",
        "stop_reason": outcome["stop_reason"],
        "evaluations": outcome["evaluations"],
        "repeats": args.repeats,
        "backend": backend_info,
        "weights": dict(GROUP_WEIGHTS),
        "hard_limits": dict(HARD_LIMITS_DEFAULT),
        "best_config_id": store.best_config_id,
        "S_best": outcome["best_stats"]["S"],
        "counts": counts,
        "config_path": os.path.abspath(args.config),
        "reference_path": os.path.abspath(args.reference),
    }
    with open(os.path.join(out_dir, "report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "best_config.json"), "w",
              encoding="utf-8") as fh:
        json.dump(best, fh, ensure_ascii=False, indent=2)
    try:
        fd_best = get_param(best, "transmission.final_drive")
    except KeyError:
        fd_best = None
    print("KAMPAN hotova: stop=%s evals=%d testovano=%d prijato=%d zamitnuto=%d"
          % (outcome["stop_reason"], outcome["evaluations"], counts["tested"],
             counts["accepted"], counts["rejected"]))
    print("best_config_id=%s S_best=%.4f final_drive_best=%s"
          % (store.best_config_id, outcome["best_stats"]["S"], fd_best))
    print("vystupy: %s (history.jsonl, best.json, manifest.json, report.json)" % out_dir)
    return 0


def cmd_selftest(args):
    out_dir = args.out or os.path.join(ROOT, "vehicle-data", "runs",
                                       "selftest_%s" % datetime.datetime.now(
                                           datetime.timezone.utc).strftime(
                                               "%Y%m%dT%H%M%SZ"))
    code, message, results = run_selftest(
        out_dir, ROOT, reference_path=args.reference, repeats=args.repeats,
        max_evaluations=args.max_evaluations, base_seed=args.seed)
    print(results.get("report", message))
    print("vystupy: %s" % out_dir)
    return code


def cmd_plan(args):
    diagnosis = load_json(args.diagnosis)
    config = normalize_config(load_json(args.config))
    plan = plan_from_diagnosis(diagnosis, config,
                               max_iterations=args.max_iterations)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="AutoEngineerAI pipeline: load -> simulate -> evaluate -> propose")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="plna kampan bez zasahu uzivatele")
    p_run.add_argument("--config", required=True, help="VehicleConfig JSON")
    p_run.add_argument("--reference", required=True, help="reference JSON (rp nebo rich)")
    p_run.add_argument("--out", default=None, help="vystupni adresar")
    p_run.add_argument("--repeats", type=int, default=5)
    p_run.add_argument("--max-evaluations", type=int, default=60)
    p_run.add_argument("--seed", type=int, default=7)
    p_run.set_defaults(func=cmd_run)

    p_st = sub.add_parser("selftest", help="akceptacni selftest (exit 0/1)")
    p_st.add_argument("--reference", default=None)
    p_st.add_argument("--out", default=None)
    p_st.add_argument("--repeats", type=int, default=5)
    p_st.add_argument("--max-evaluations", type=int, default=80)
    p_st.add_argument("--seed", type=int, default=1234)
    p_st.set_defaults(func=cmd_selftest)

    p_plan = sub.add_parser("plan", help="ChangePlan v0 z Diagnosis (deterministicky)")
    p_plan.add_argument("--diagnosis", required=True)
    p_plan.add_argument("--config", required=True)
    p_plan.add_argument("--max-iterations", type=int, default=50)
    p_plan.set_defaults(func=cmd_plan)

    args = parser.parse_args(argv)
    if args.command in ("run", "selftest") and args.repeats is not None and args.repeats < 3:
        print("CHYBA: repeats musi byt >= 3 (TESTING-OPTIMIZATION §5.5)", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

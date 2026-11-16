"""Selftest akceptace Agenta G: zhorseny brzdny bias -> najit a validovat lepsi.

Scenar: vychozi VehicleConfig (tovarni hodnoty) se ZHORSENYM brzdnym biasem
0.70 (prilis na predku: brzdna draha 100-0 ~52 m misto tovarnich ~46 m).
Kampan musi prokazatelne najit a statisticky (A1–A5) potvrdit lepsi
konfiguraci. Exit 0 = vse splneno, 1 = nesplneno. Tiskne RAW historii
(JSONL) a best_config_id. Pouze stdlib.

Pozn. ke kalibraci (realny backend src/Sim, 240 Hz): staly prevod ani
spickovy moment na S v teto matici prakticky nereaguji (t_0_100 i V-max
se v rozsahu sond meni v pasmu sumu; krivka S(fd) neni monotoni),
takze degradace final_drive neni na realnem Simu detekovatelna.
Brzdny bias ma hladkou konvexni odezvu (0.62 -> S~6.79, 0.70 -> S~8.25),
proto je degradovanym knobem selftestu prave on.
"""

import datetime
import json
import os
import sys

try:
    from .backend import (
        GROUP_WEIGHTS,
        HARD_LIMITS_DEFAULT,
        SCENARIOS,
        load_reference_targets,
        make_evaluator,
    )
    from .optimizer import run_optimization
    from .search_space import get_param, search_space
    from .store import VariantStore
except ImportError:  # prime spousteni jako skript: python src/Optimizer/selftest.py
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _ROOT = os.path.dirname(os.path.dirname(_HERE))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from src.Optimizer.backend import (
        GROUP_WEIGHTS,
        HARD_LIMITS_DEFAULT,
        SCENARIOS,
        load_reference_targets,
        make_evaluator,
    )
    from src.Optimizer.optimizer import run_optimization
    from src.Optimizer.search_space import get_param, search_space
    from src.Optimizer.store import VariantStore

FACTORY_FINAL_DRIVE = 2.866
FACTORY_BIAS_FRONT = 0.62
DEGRADED_BIAS_FRONT = 0.70
REPEATS = 5
MAX_EVALUATIONS = 80


def degraded_config():
    """Ukazkovy config s umyslne zhorsenym brzdnym biasem (schema-compatible).

    Vse tovarni krome brakes.bias_front = 0.70 (viz kalibracni poznamka
    v hlavicce: jediny knob s hladkou meritelnou odezvou na realnem Simu).
    """
    return {
        "schema_version": "1.0.0",
        "config_id": "cfg_selftest_base",
        "parent_config_id": None,
        "vehicle_profile_id": "vp_2026_mx5_demo",
        "chassis_adapter": "achassis-v1",
        "parameters": {
            "engine": {"peak_torque_nm": 205.0, "peak_power_kw": 135.0},
            "transmission": {
                "gears": [5.087, 2.991, 2.035, 1.594, 1.286, 1.0],
                "final_drive": FACTORY_FINAL_DRIVE,
                "shift_rpm": 7000.0,
                "shift_time_s": 0.4,
            },
            "tires": {"grip_long": 1.0, "grip_lat": 1.0},
            "suspension": {"spring_f_Npm": 28000.0, "damper_f_Nspm": 2500.0,
                           "spring_r_Npm": 24000.0, "damper_r_Nspm": 2200.0},
            "steering": {"max_angle_deg": 35.0},
            "brakes": {"bias_front": DEGRADED_BIAS_FRONT, "torque_Nm": 4000.0},
            "geometry_overrides": None,
        },
        "rationale": "selftest: umyslne zhorseny bias_front 0.70 (zaklad kampane)",
    }


def default_reference_path(root):
    return os.path.join(root, "vehicle-data", "references", "example-vehicle.json")


def _load_targets(root, reference_path=None):
    path = reference_path or default_reference_path(root)
    return load_reference_targets(path), path


def run_selftest(out_dir, root, reference_path=None, repeats=REPEATS,
                 max_evaluations=MAX_EVALUATIONS, base_seed=1234,
                 print_raw=True):
    """Spusti selftest kampan. Vraci (exit_code, zprava, vysledky)."""
    os.makedirs(out_dir, exist_ok=True)
    hist = os.path.join(out_dir, "history.jsonl")
    if os.path.exists(hist) and os.path.getsize(hist) > 0:
        return 1, "cilovy adresar neni prazdny (historie musi byt append-only " \
                  "a selftest vyzaduje cisty beh): %s" % hist, {}
    targets, ref_path = _load_targets(root, reference_path)
    if not targets:
        return 1, "reference neobsahuje zadne bodovane metriky", {}
    initial = degraded_config()
    space = search_space(initial)
    store = VariantStore(out_dir)
    evaluate_config, backend_info = make_evaluator(
        out_dir, targets, repeats=repeats, base_seed=base_seed,
        code_version="optimizer-v0-selftest")
    outcome = run_optimization(initial, space, evaluate_config, store,
                               targets, dict(HARD_LIMITS_DEFAULT),
                               max_evaluations=max_evaluations)
    best = outcome["best_config"]
    best_stats = outcome["best_stats"]
    base_rec = store.attempts[0] if store.attempts else {}
    base_stats = {"S": base_rec.get("S")}
    checks = []
    bias_init = DEGRADED_BIAS_FRONT
    bias_best = get_param(best, "brakes.bias_front")

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    ok_all = True
    ok_all &= check("history_nonempty", len(store.attempts) >= 3,
                    "pokusu=%d" % len(store.attempts))
    accepts = sum(1 for r in store.attempts
                    if (r.get("decision") or {}).get("accept") is True
                    and r.get("attempt", 0) != 0)
    ok_all &= check("accepted_exists", accepts >= 1, "prijato=%d" % accepts)
    fail_codes = {(r.get("decision") or {}).get("failed_condition")
                  for r in store.attempts}
    fail_codes = {c for c in fail_codes if c}
    ok_all &= check("rejected_with_A_code", len(fail_codes) >= 1,
                    "kody=%s" % sorted(fail_codes))
    margin = max(0.005 * abs(base_rec.get("S") or 0.0), 1e-9)
    improved = (best_stats["S"] < base_rec.get("S", 0.0) - margin)
    ok_all &= check("score_improved",
                    improved and best["config_id"] != initial["config_id"],
                    "S_base=%.4f S_best=%.4f" % (base_rec.get("S"), best_stats["S"]))
    closer = abs(bias_best - FACTORY_BIAS_FRONT) < abs(bias_init - FACTORY_BIAS_FRONT)
    ok_all &= check("bias_toward_factory", closer,
                    "bias_base=%.2f bias_best=%.2f tovarna=%.3f"
                    % (bias_init, bias_best, FACTORY_BIAS_FRONT))
    base_medians = (store.attempts[0].get("scenario_metric_medians") or {})
    b_init = None
    for scen_meds in base_medians.values():
        if scen_meds.get("brake_distance_100_0_m") is not None:
            b_init = scen_meds["brake_distance_100_0_m"]
            break
    b_best = best_stats["metric_medians"].get("brake_distance_100_0_m")
    brake_ok = (b_init is None or b_best is None
                or b_best <= b_init * 1.01 + 1e-9)
    ok_all &= check("protected_brake_not_worse", brake_ok,
                    "brzda base=%s best=%s" % (b_init, b_best))
    ok_all &= check("best_config_id_present",
                    bool(store.best_config_id)
                    and store.best_config_id == best["config_id"],
                    "best_config_id=%s" % store.best_config_id)
    ok_all &= check("no_unstable_accepted",
                    all(r.get("decision", {}).get("accept") is not True
                        or "UNSTABLE" not in json.dumps(r.get("scenario_medians") or {})
                        for r in store.attempts),
                    "zadny prijaty pokus s UNSTABLE")

    manifest = {
        "selftest": True,
        "level": "SIM (UNCONFIRMED_RUNTIME – neni dukaz pro Roblox)",
        "reference_path": ref_path,
        "factory_final_drive": FACTORY_FINAL_DRIVE,
        "factory_bias_front": FACTORY_BIAS_FRONT,
        "degraded_bias_front": bias_init,
        "best_bias_front": bias_best,
        "S_base": base_rec.get("S"),
        "S_best": best_stats["S"],
        "best_config_id": store.best_config_id,
        "stop_reason": outcome["stop_reason"],
        "evaluations": outcome["evaluations"],
        "repeats": repeats,
        "backend": backend_info,
        "scenarios": [s["scenario_id"] for s in SCENARIOS],
        "weights": dict(GROUP_WEIGHTS),
        "checks": checks,
    }
    with open(os.path.join(out_dir, "selftest_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    lines = []
    lines.append("SELFTEST optimizer-v0 bias_base=%.2f -> bias_best=%.2f "
                 "S_base=%.4f S_best=%.4f best=%s stop=%s evals=%d"
                 % (bias_init, bias_best, base_rec.get("S") or float("nan"),
                    best_stats["S"], store.best_config_id,
                    outcome["stop_reason"], outcome["evaluations"]))
    for c in checks:
        lines.append("  [%s] %s: %s" % ("OK" if c["ok"] else "FAIL",
                                        c["check"], c["detail"]))
    if print_raw:
        lines.append("--- RAW historie (history.jsonl) ---")
        for rec in store.records:
            lines.append(json.dumps(rec, ensure_ascii=False))
        lines.append("best_config_id=%s" % store.best_config_id)
    report = "\n".join(lines)
    base_stats.update({"S": base_rec.get("S")})
    results = {"manifest": manifest, "report": report,
               "best_config": best, "best_stats": best_stats}
    return (0 if ok_all else 1,
            "SELFTEST %s" % ("PASS" if ok_all else "FAIL"), results)


if __name__ == "__main__":
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _ROOT = os.path.dirname(os.path.dirname(_HERE))
    _stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ")
    _out = os.path.join(_ROOT, "vehicle-data", "runs",
                        "opt_selftest_" + _stamp)
    _code, _message, _results = run_selftest(_out, _ROOT)
    print(_results.get("report", _message))
    sys.exit(_code)

"""FÁZE 4.2.1 Agent C: efekt optimalizace (bias_front hybe metrikou).

(1) Optimalizovany parametr brakes.bias_front prokazatelne meni metriku
    brake_distance_100_0_m: 2 konfigurace (before 0.70 / after 0.62),
    parovane opakovane behy pres kanonicke src/Telemetry/evaluate
    (5/5 shodnych znamenek = znamenkovy test p ~ 0.03 < 0.05, ne nahoda).
(2) Nepodporovany parametr engine.peak_torque_nm je mimo prostor
    (nema Tune protejsek ani katalogovy zaznam, MAPPING.md §6/1).
(3) Determinismus (stejny seed = bitove stejne stopy), historie
    append-only a rollback pointer zachovany (stub-kampan pres
    run_optimization + VariantStore, dvakrat = shodne).
Akceptace: exit 0 + raw vystup (RAW F4-C bloky). Pouze stdlib.
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Chassis.mapping_engine import build_search_space  # noqa: E402
from src.Optimizer.backend import HARD_LIMITS_DEFAULT  # noqa: E402
from src.Optimizer.fallback_sim import synth_brake_rows, write_csv  # noqa: E402
from src.Optimizer.optimizer import (  # noqa: E402
    run_optimization,
    safety_filter,
)
from src.Optimizer.search_space import (  # noqa: E402
    backend_caps,
    get_param,
    search_space,
)
from src.Optimizer.store import VariantStore  # noqa: E402
from src.Telemetry.evaluate import evaluate  # noqa: E402

CATALOG = os.path.join(ROOT, "src", "Chassis", "catalog", "parameters.json")

BAD_BIAS = 0.70    # before: zhorseny (selftest vychozi stav)
GOOD_BIAS = 0.62   # after: tovarni (ocekavane lepsi)
OPT_BIAS = 0.60    # kalibracni optimum fallback modelu
SEEDS = [11, 22, 33, 44, 55]  # 5 opakovanych behu (parovane)
MIN_PAIRED_DIFF_M = 0.5  # nejnizsi pripustny parovany rozdil (efekt ~0.8)


def _cfg(bias, config_id="cfg_f4c_effect"):
    """Minimalni schema-compatible VehicleConfig pro fallback Sim."""
    return {
        "schema_version": "1.0.0",
        "config_id": config_id,
        "parent_config_id": None,
        "vehicle_profile_id": "vp_2026_mx5_demo",
        "chassis_adapter": "achassis-v1",
        "parameters": {
            "engine": {"peak_torque_nm": 205.0, "peak_power_kw": 135.0},
            "transmission": {
                "gears": [5.087, 2.991, 2.035, 1.594, 1.286, 1.0],
                "final_drive": 2.866,
                "shift_rpm": 7000.0,
                "shift_time_s": 0.4,
            },
            "tires": {"grip_long": 1.0},
            "brakes": {"bias_front": bias},
        },
        "rationale": "F4.2.1 Agent C: efekt bias_front",
    }


def _brake_distance_m(config, seed, workdir):
    """Kanonicka metrika brake_distance_100_0_m pres fallback + evaluate."""
    csv_path = os.path.join(
        workdir, "%s_s%d.csv" % (config["config_id"], seed))
    write_csv(csv_path, synth_brake_rows(config, seed))
    profile = {
        "target_metrics": [{"metric": "brake_distance_100_0_m",
                            "target": 40.0, "tolerance": 5.0}],
        "config_id": config["config_id"],
        "scenario_id": "S3_brake",
        "seed": seed,
        "mode": "local-sim",
        "code_version": "f4c-effect-test",
    }
    return evaluate(csv_path, profile)["metrics"]["brake_distance_100_0_m"]


def _stub_evaluator_factory():
    """Deterministicky stub: S(bias) konvexni s minimem na OPT_BIAS."""
    def evaluate_config(config, seed_offset=0, baseline_metrics=None):
        bias = get_param(config, "brakes.bias_front")
        s_val = 5.0 + 100.0 * (bias - OPT_BIAS) ** 2
        dist = 40.0 + 100.0 * (bias - OPT_BIAS) ** 2
        return {
            "S": s_val,
            "rep_totals": [s_val] * 5,
            "scenario_rep_totals": {"S3_brake": [s_val] * 5},
            "scenario_medians": {"S3_brake": s_val},
            "scenario_metric_medians": {
                "S3_brake": {"brake_distance_100_0_m": dist}},
            "metric_medians": {"brake_distance_100_0_m": dist},
            "unstable": 0,
            "suspect": 0,
            "aborts": 0,
        }
    return evaluate_config


def _run_stub_campaign(out_dir):
    initial = _cfg(BAD_BIAS, "cfg_f4c_base")
    space = search_space(initial)
    store = VariantStore(out_dir)
    outcome = run_optimization(
        initial, space, _stub_evaluator_factory(), store, [],
        dict(HARD_LIMITS_DEFAULT), max_evaluations=30,
        stop_on_target=False)
    return store, outcome


class TestF4OptimizerEffect(unittest.TestCase):
    def test_prostor_bias_uvnitr_peak_torque_venku(self):
        """Dynamicky prostor: bias se ladi, peak_torque_neni v prostoru."""
        caps = backend_caps(CATALOG)
        self.assertTrue(caps)
        self.assertIn("BrakeBias", caps)
        self.assertNotIn("Horsepower", caps)  # Sim meri moment/vykon
        tune_space = build_search_space(CATALOG, caps)
        self.assertIn("BrakeBias", tune_space)
        space = search_space(_cfg(BAD_BIAS))
        self.assertTrue(space)
        names = [e["name"] for e in space]
        self.assertIn("brakes.bias_front", names)
        self.assertNotIn("engine.peak_torque_nm", names)
        for entry in space:
            self.assertLess(entry["min"], entry["max"])
            self.assertGreater(entry["step"], 0)
        print("RAW prostor: caps=%s tune=%s optimizer=%s"
              % (caps, tune_space, names))

    def test_bias_meni_metriku_opakovane_behy(self):
        """before/after (0.70 vs 0.62): parovane lepsi ve vsech 5 bezich."""
        workdir = tempfile.mkdtemp(prefix="f4c_effect_")
        before = _cfg(BAD_BIAS, "cfg_f4c_before")
        after = _cfg(GOOD_BIAS, "cfg_f4c_after")
        rows = []
        for seed in SEEDS:
            d_before = _brake_distance_m(before, seed, workdir)
            d_after = _brake_distance_m(after, seed, workdir)
            rows.append((seed, d_before, d_after))
            self.assertLess(
                d_after, d_before,
                "seed %d: after=%.4f neni lepsi nez before=%.4f"
                % (seed, d_after, d_before))
            self.assertGreater(
                d_before - d_after, MIN_PAIRED_DIFF_M,
                "seed %d: rozdil %.4f pod prahem efektu" % (seed, d_before - d_after))
        med_before = sorted(r[1] for r in rows)[len(rows) // 2]
        med_after = sorted(r[2] for r in rows)[len(rows) // 2]
        self.assertGreater(med_before - med_after, MIN_PAIRED_DIFF_M)
        print("--- RAW F4-C efekt (bias 0.70 -> 0.62) ---")
        for seed, d_before, d_after in rows:
            print("seed=%d before=%.4f m after=%.4f m diff=%.4f m"
                  % (seed, d_before, d_after, d_before - d_after))
        print("median before=%.4f after=%.4f (5/5 shoda, p~0.03)"
              % (med_before, med_after))

    def test_determinismus_stejny_seed(self):
        """Stejny seed = bitove stejne stopy (x i v)."""
        first = synth_brake_rows(_cfg(GOOD_BIAS), SEEDS[0])
        second = synth_brake_rows(_cfg(GOOD_BIAS), SEEDS[0])
        self.assertEqual(len(first), len(second))
        self.assertTrue(first)
        for row_a, row_b in zip(first, second):
            self.assertEqual(row_a["x_m"], row_b["x_m"])
            self.assertEqual(row_a["v_mps"], row_b["v_mps"])
        print("RAW determinismus: %d radku identickych (seed=%d)"
              % (len(first), SEEDS[0]))

    def test_historie_rollback_determinismus(self):
        """Stub-kampan: historie append-only, rollback pointer, 2x shodne."""
        out1 = tempfile.mkdtemp(prefix="f4c_hist1_")
        out2 = tempfile.mkdtemp(prefix="f4c_hist2_")
        store1, outcome1 = _run_stub_campaign(out1)
        store2, outcome2 = _run_stub_campaign(out2)

        best1 = outcome1["best_config"]
        bias_best = get_param(best1, "brakes.bias_front")
        self.assertLess(abs(bias_best - OPT_BIAS), abs(BAD_BIAS - OPT_BIAS))
        self.assertEqual(store1.best_config_id, best1["config_id"])
        accepted = sum(1 for r in store1.attempts
                       if (r.get("decision") or {}).get("accept") is True
                       and r.get("attempt", 0) != 0)
        self.assertGreaterEqual(accepted, 1)
        rollbacks = [r for r in store1.records
                     if r.get("event") == "rollback"
                     or r.get("rollback_to")]
        self.assertTrue(rollbacks, "zadny rollback zaznam")

        # Append-only: soubor = pamet; reload ze souboru = shoda.
        with open(os.path.join(out1, "history.jsonl"),
                  encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), len(store1.records))
        reopened = VariantStore(out1)
        self.assertEqual(len(reopened.records), len(store1.records))
        self.assertEqual(reopened.best_config_id, store1.best_config_id)

        # Determinismus: dve kampane = shodny prubeh i vysledek.
        seq1 = [r.get("S") for r in store1.attempts]
        seq2 = [r.get("S") for r in store2.attempts]
        self.assertEqual(seq1, seq2)
        self.assertEqual(bias_best,
                         get_param(outcome2["best_config"], "brakes.bias_front"))
        self.assertEqual(outcome1["best_stats"]["S"],
                         outcome2["best_stats"]["S"])

        # Safety filtr nad zivymi kroky/jednotkami porad strazi meze.
        entry = {e["name"]: e for e in search_space(_cfg(BAD_BIAS))}
        bad_diff = {"brakes.bias_front": {"from": BAD_BIAS,
                                          "to": entry["brakes.bias_front"]["max"] + 1.0}}
        ok, reason = safety_filter(bad_diff, _cfg(BAD_BIAS),
                                   search_space(_cfg(BAD_BIAS)))
        self.assertFalse(ok)
        self.assertTrue(reason)

        raw = {"best_bias": bias_best,
               "S_base": store1.attempts[0].get("S"),
               "S_best": outcome1["best_stats"]["S"],
               "attempts": len(store1.attempts),
               "accepted": accepted,
               "rollbacks": len(rollbacks),
               "stop": outcome1["stop_reason"],
               "best_config_id": store1.best_config_id}
        print("--- RAW F4-C historie/rollback ---")
        print(json.dumps(raw, ensure_ascii=False))
        print("F4-C EFFECT OK")


if __name__ == "__main__":
    unittest.main(verbosity=2)

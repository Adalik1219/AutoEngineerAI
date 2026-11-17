"""FÁZE 4 integrace (Agent D): VehicleConfig -> map_config -> adapter
apply_config -> Sim run -> evaluate -> TestResult.

Retez prvne overuje sjednocena rozhrani katalog<->mapping:
  verification_status: katalog PASS (overeno auditem/kodem [F]) je kanonicky;
    "verified" je starsi nazev ze zadani F4.2 (zpetna kompatibilita).
  backend_caps: kanonicky zdroj = Sim backend (SIM_SUPPORTED_CONFIG_PATHS
    v src/Optimizer/search_space.py: config_path podpora -> tune_key mnozina
    pres katalog) -> build_search_space -> dynamicky prostor Optimizeru.
  config_path -> tune_key: prevod dava katalog (Agent D wiring).

Akceptace: exit 0 + raw vystup (RAW F4 blok). peak_torque_nm cesta je
explicitne odmitnuta s duvodem (nema Tune protejsek, MAPPING.md §6/1).
Pouze stdlib.
"""

import copy
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter  # noqa: E402
from src.Chassis.mapping_engine import build_search_space, map_config  # noqa: E402
from src.Optimizer.search_space import (  # noqa: E402
    SIM_SUPPORTED_CONFIG_PATHS,
    backend_caps,
    search_space,
)
from src.Sim.run import DEFAULT_DT, run_scenario  # noqa: E402
from src.Telemetry.evaluate import evaluate  # noqa: E402

CATALOG = os.path.join(ROOT, "src", "Chassis", "catalog", "parameters.json")
SCENARIO = "straight_accel"
SEED = 7


def demo_config():
    """VehicleConfig: tovarni hodnoty + zhorseny bias (meritelna odezva Simu)."""
    return {
        "schema_version": "1.0.0",
        "config_id": "cfg_f4_integration",
        "parent_config_id": None,
        "vehicle_profile_id": "vp_2026_mx5_demo",
        "chassis_adapter": "achassis-v1",
        "parameters": {
            "engine": {"peak_torque_nm": 205.0, "peak_power_kw": 135.0,
                       "horsepower": 210, "idle_rpm": 950.0,
                       "redline_rpm": 7500.0, "shift_rpm": 6800.0},
            "transmission": {"gears": [3.36, 2.05, 1.48, 1.17, 1.00, 0.83],
                             "final_drive": 3.2, "efficiency": 0.90,
                             "drive": "RWD", "shift_time_s": 0.35},
            "tires": {"grip_long": 1.0, "grip_lat": 1.0, "mu_road": 1.0},
            "brakes": {"bias_front": 0.70, "torque_Nm": 4000.0},
            "suspension": {"spring_f_Npm": 28000.0},
            "steering": {"max_angle_deg": 32.0},
            "geometry_overrides": None,
        },
        "rationale": "F4 integracni test: mapovani -> Tune -> Sim -> TestResult",
    }


class TestF4Integration(unittest.TestCase):
    def test_chain_vehicleconfig_to_testresult(self):
        config = demo_config()

        # (1) Prostor na realnem katalogu je NEPRÁZDNÝ.
        caps = backend_caps(CATALOG)
        tune_space = build_search_space(CATALOG, caps)
        self.assertTrue(tune_space, "prostor na realnem katalogu je prazdny")
        space = search_space(config)
        self.assertTrue(space, "Optimizer prostor je prazdny")
        self.assertTrue(all(e["name"] != "engine.peak_torque_nm"
                            for e in space),
                        "peak_torque_nm nesmi byt optimalizovatelny")

        # (2) map_config: Tune-mmapovatelne projde, peak_torque_nm odmítnut.
        mapped = map_config(config, CATALOG, "achassis-v1")
        tune_keys = {c["tune_key"] for c in mapped["tune_changes"]}
        self.assertIn("Bias", tune_keys)
        self.assertIn("FinalDrive", tune_keys)
        rej = {r["param"]: r["reason"] for r in mapped["rejected"]}
        self.assertIn("engine.peak_torque_nm", rej)
        self.assertIn("engine.peak_power_kw", rej)
        self.assertIn("nemapuje", rej["engine.peak_torque_nm"])

        # (3) Adapter: Tune patch se aplikuje (wiring Agent D).
        tune_patch = {c["tune_key"]: c["value"]
                      for c in mapped["tune_changes"]}
        cfg_tune = copy.deepcopy(config)
        cfg_tune["parameters"] = dict(cfg_tune["parameters"])
        cfg_tune["parameters"]["tune"] = tune_patch
        adapter = AChassisV1Adapter()
        report = adapter.apply_config(
            os.path.join(ROOT, "assets", "chassis-original"), cfg_tune)
        applied = {a["tune_key"] for a in report.applied}
        self.assertIn("Bias", applied)
        patched = report.to_dict()["patched_config"]
        self.assertEqual(patched["parameters"]["tune"]["Bias"], 0.70)

        # (4) Sim run -> evaluate -> TestResult (striktne validni pole).
        tmp = tempfile.mkdtemp(prefix="f4_integration_")
        cfg_path = os.path.join(tmp, "config.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh)
        out_dir = os.path.join(tmp, "sim")
        csv_path, _, manifest = run_scenario(
            cfg_path, SCENARIO, DEFAULT_DT, SEED, out_dir)
        self.assertTrue(os.path.getsize(csv_path) > 0)
        profile = {
            "target_metrics": [
                {"metric": "t_0_100_s", "target": 8.0, "tolerance": 2.0},
                {"metric": "v_max_kmh", "target": 210.0, "tolerance": 10.0},
            ],
            "config_id": config["config_id"],
            "scenario_id": SCENARIO,
            "seed": SEED,
            "mode": manifest["mode"],
            "code_version": "f4-integration-test",
        }
        result = evaluate(csv_path, profile)
        for key in ("result_id", "config_id", "scenario_id", "metrics",
                    "score", "environment", "raw_telemetry_ref"):
            self.assertIn(key, result)
        self.assertEqual(result["config_id"], config["config_id"])
        self.assertEqual(result["scenario_id"], SCENARIO)
        self.assertIn("t_0_100_s", result["metrics"])
        self.assertTrue(0.0 <= result["score"] <= 1.0)

        # (5) RAW vystup (akceptace vyzaduje raw).
        raw = {
            "backend_caps": caps,
            "tune_space": tune_space,
            "optimizer_space": space,
            "tune_changes": mapped["tune_changes"],
            "rejected": mapped["rejected"],
            "adapter_applied": report.applied,
            "sim_manifest": {"scenario_id": manifest["scenario_id"],
                             "rows": manifest["rows"],
                             "mode": manifest["mode"]},
            "test_result": {
                "result_id": result["result_id"],
                "config_id": result["config_id"],
                "scenario_id": result["scenario_id"],
                "score": result["score"],
                "metrics": {k: result["metrics"].get(k) for k in
                            ("t_0_100_s", "v_max_kmh",
                             "brake_distance_100_0_m")},
            },
        }
        print("--- RAW F4 integrace ---")
        print(json.dumps(raw, ensure_ascii=False, indent=2))
        print("F4 INTEGRATION OK")

    def test_peak_torque_path_explicitly_rejected(self):
        """engine.peak_torque_nm nema Tune protejsek -> vzdy rejected s duvodem."""
        config = demo_config()
        config["parameters"] = {
            "engine": {"peak_torque_nm": 205.0},
            "geometry_overrides": None,
        }
        mapped = map_config(config, CATALOG, "achassis-v1")
        self.assertEqual(mapped["tune_changes"], [])
        self.assertEqual(len(mapped["rejected"]), 1)
        reason = mapped["rejected"][0]["reason"]
        self.assertEqual(mapped["rejected"][0]["param"],
                         "engine.peak_torque_nm")
        self.assertTrue(reason, "odmitnuti musi nest duvod")
        print("RAW peak_torque_nm rejected: %s" % reason)

    def test_sim_supported_paths_are_canonical_caps_source(self):
        """backend_caps = Sim-podpora -> tune_key (dokumentace kanonickeho zdroje)."""
        caps = backend_caps(CATALOG)
        with open(CATALOG, encoding="utf-8") as fh:
            records = {r["config_path"]: r for r in json.load(fh)}
        for path in SIM_SUPPORTED_CONFIG_PATHS:
            rec = records.get(path)
            if rec and rec.get("category") == "MUTABLE_TUNE" and rec.get(
                    "tune_key"):
                self.assertIn(rec["tune_key"], caps,
                              "Sim-ctena cesta %r chybi v caps" % path)
        # Sim necte engine.horsepower -> neni v caps (meri jen moment/vykon).
        self.assertNotIn("Horsepower", caps)
        print("RAW backend_caps (%d): %s" % (len(caps), caps))


if __name__ == "__main__":
    unittest.main(verbosity=2)

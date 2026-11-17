"""F4.4 regression test harness-vystupu T03 (Agent H1).

Validuje exporty outboxu (bridge/outbox -> vehicle-data/telemetry/f44/*.json):
  - schema pole per-run vystupu (TelemetrieCollector.GetRunOutput),
  - prave 3 repetice na (config_id, scenario_id),
  - T03 metriky v summary.t03 (brake_distance_studs, stopping_time_s, ABS),
  - nezavisly prepocet brake_distance z XZ vzorku,
  - agregat SUMMARY-<config>-T03 (mean/std/min/max/delta, repeatability +/-5 %).

Prazdny/chybejici adresar = SKIP s duvodem (legitimni PENDING: Studio-beh
dosud nemeren v Roblox runtime; zadna data zatim neexistuji).
Stdlib only, zadne sitove sluzby.
"""
import json
import math
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F44_DIR = os.path.join(ROOT, "vehicle-data", "telemetry", "f44")

REQUIRED_RUN_FIELDS = [
    "run_id",
    "scenario_id",
    "vehicle_id",
    "config_id",
    "timestamp",
    "environment",
    "measurements",
    "completion_status",
    "errors",
]

STOP_SPEED = 0.1
REPEAT_TOL_PCT = 5.0
EXPECTED_REPS = 3


def load_f44():
    """Nacte vsechny *.json z F44_DIR. Vraci (runs, summaries).

    runs: per-run vystupy; summaries: agregaty SUMMARY-*-T03.
    """
    if not os.path.isdir(F44_DIR):
        return None
    docs = []
    for name in sorted(os.listdir(F44_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(F44_DIR, name)
        with open(path, encoding="utf-8") as fh:
            docs.append((name, json.load(fh)))
    if not docs:
        return None
    runs = [d for _, d in docs if not isinstance(d, dict) or d.get("type") != "t03_summary"]
    summaries = [d for _, d in docs if isinstance(d, dict) and d.get("type") == "t03_summary"]
    return runs, summaries


def require_data(testcase):
    loaded = load_f44()
    if loaded is None:
        testcase.skipTest(
            "PENDING: vehicle-data/telemetry/f44 je prazdny nebo chybi "
            "(Studio-beh T03 dosud nemeren, legitimni PENDING)"
        )
    assert loaded is not None  # skipTest vyse vzdy vyhodi pri None
    return loaded


def xz_speed(v):
    if not isinstance(v, dict):
        return None
    try:
        return math.sqrt(v["x"] ** 2 + v["z"] ** 2)
    except (KeyError, TypeError):
        return None


def recompute_brake_distance(samples):
    """Nezavisly prepocet: kumulativni XZ draha do prvniho vzorku s v_xz < 0.1.

    Vraci (distance, stop_t, stopped). Stop cas = t vzorku zastaveni.
    """
    if not samples:
        raise ValueError("prazdne samples")
    dist = 0.0
    prev = samples[0].get("pos")
    for s in samples[1:]:
        pos = s.get("pos")
        if isinstance(prev, dict) and isinstance(pos, dict):
            try:
                dist += math.sqrt((pos["x"] - prev["x"]) ** 2 + (pos["z"] - prev["z"]) ** 2)
            except (KeyError, TypeError):
                pass
        prev = pos if isinstance(pos, dict) else prev
        v = xz_speed(s.get("vel"))
        if v is not None and v < STOP_SPEED:
            return dist, s.get("t"), True
    last_t = samples[-1].get("t") if isinstance(samples[-1], dict) else None
    return dist, last_t, False


def mean(values):
    return sum(values) / len(values)


def pstdev(values):
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


class TestF44Schema(unittest.TestCase):
    """Schema pole per-run vystupu + agregatu."""

    def test_required_fields(self):
        runs, summaries = require_data(self)
        for run in runs:
            for field in REQUIRED_RUN_FIELDS:
                self.assertIn(field, run, "chybi pole %s v %s" % (field, run.get("run_id")))
            env = run["environment"]
            self.assertEqual(env.get("mode"), "roblox-runtime", "spatny mode v %s" % run.get("run_id"))
            self.assertIn("seed", env)
            self.assertIn("code_version", env)
            meas = run["measurements"]
            self.assertIn("samples", meas)
            self.assertIsInstance(meas["samples"], list)
            self.assertGreater(len(meas["samples"]), 0, "prazdne samples v %s" % run.get("run_id"))

    def test_sample_fields(self):
        runs, _ = require_data(self)
        for run in runs:
            for i, s in enumerate(run["measurements"]["samples"]):
                self.assertIn("t", s, "vzorek %d bez t (%s)" % (i, run.get("run_id")))
                for axis in ("pos", "vel"):
                    self.assertIn(axis, s)
                    for comp in ("x", "y", "z"):
                        self.assertIsInstance(
                            s[axis][comp], (int, float), "%s.%s neni cislo (%s)" % (axis, comp, run.get("run_id"))
                        )
                for comp in ("throttle", "brake", "steer"):
                    self.assertIn(comp, s["inputs"], "chybi inputs.%s (%s)" % (comp, run.get("run_id")))

    def test_summary_schema(self):
        _, summaries = require_data(self)
        for doc in summaries:
            for field in REQUIRED_RUN_FIELDS:
                self.assertIn(field, doc, "chybi pole %s v agregatu" % field)
            body = doc["measurements"]["summary"]
            for field in (
                "n",
                "run_ids",
                "brake_distance_mean_studs",
                "brake_distance_std_studs",
                "brake_distance_min_studs",
                "brake_distance_max_studs",
                "brake_distance_delta_pct",
                "repeatability_ok",
            ):
                self.assertIn(field, body, "chybi agregat %s" % field)


class TestF44Repetitions(unittest.TestCase):
    """Prave 3 repetice na (config_id, scenario_id)."""

    def test_three_reps_per_config_scenario(self):
        runs, _ = require_data(self)
        groups = {}
        for run in runs:
            key = (run.get("config_id"), run.get("scenario_id"))
            groups.setdefault(key, []).append(run.get("run_id"))
        self.assertGreater(len(groups), 0)
        for key, ids in sorted(groups.items(), key=str):
            self.assertEqual(
                len(ids), EXPECTED_REPS, "skupina %s ma %d behu (ocekavano %d): %s" % (key, len(ids), EXPECTED_REPS, ids)
            )


class TestF44T03Metrics(unittest.TestCase):
    """T03 metriky: pritomnost, prepocet z XZ, ABS tvar, agregat."""

    def t03_runs(self):
        runs, _ = require_data(self)
        t03 = [r for r in runs if r.get("scenario_id") == "T03"]
        if not t03:
            self.skipTest("PENDING: zadny beh T03 v exportu")
        return t03

    def test_t03_metrics_present(self):
        for run in self.t03_runs():
            summary = run["measurements"].get("summary") or {}
            t03 = summary.get("t03")
            self.assertIsInstance(t03, dict, "chybi summary.t03 v %s" % run.get("run_id"))
            self.assertGreater(t03.get("brake_distance_studs", 0), 0, "nekladna draha v %s" % run.get("run_id"))
            self.assertGreater(t03.get("stopping_time_s", 0), 0, "nekladny cas v %s" % run.get("run_id"))

    def test_brake_distance_recompute(self):
        for run in self.t03_runs():
            t03 = run["measurements"]["summary"]["t03"]
            dist, stop_t, stopped = recompute_brake_distance(run["measurements"]["samples"])
            self.assertAlmostEqual(
                t03["brake_distance_studs"], dist, places=3, msg="prepoctana draha nesedi v %s" % run.get("run_id")
            )
            if stopped:
                self.assertAlmostEqual(
                    t03["stopping_time_s"], stop_t, places=6, msg="prepoctany cas nesedi v %s" % run.get("run_id")
                )
            self.assertEqual(
                t03.get("stopped"), stopped, "stopped flag nesedi s prepocetm v %s" % run.get("run_id")
            )

    def test_abs_shape(self):
        for run in self.t03_runs():
            t03 = run["measurements"]["summary"]["t03"]
            self.assertIn("abs", t03, "chybi summary.t03.abs v %s" % run.get("run_id"))
            abs_info = t03["abs"]
            if abs_info.get("active") is None:
                self.assertTrue(abs_info.get("reason"), "abs null bez duvodu v %s" % run.get("run_id"))
            else:
                self.assertIsInstance(abs_info["active"], bool)
                self.assertIsInstance(abs_info.get("active_samples"), int)

    def test_summary_aggregate(self):
        runs, summaries = require_data(self)
        t03 = [r for r in runs if r.get("scenario_id") == "T03"]
        if not t03:
            self.skipTest("PENDING: zadny beh T03 v exportu")
        by_config = {}
        for run in t03:
            by_config.setdefault(run.get("config_id"), []).append(run)
        by_summary = {d.get("config_id"): d for d in summaries}
        for config_id, group in sorted(by_config.items(), key=str):
            self.assertIn(config_id, by_summary, "chybi SUMMARY agregat pro %s" % config_id)
            doc = by_summary[config_id]
            body = doc["measurements"]["summary"]
            distances = []
            for r in group:
                t03m = r["measurements"]["summary"]["t03"]
                self.assertIsInstance(t03m, dict, "chybi summary.t03 v %s" % r.get("run_id"))
                distances.append(t03m["brake_distance_studs"])
            self.assertEqual(body.get("n"), len(group))
            self.assertEqual(sorted(body.get("run_ids")), sorted(r["run_id"] for r in group))
            self.assertAlmostEqual(body["brake_distance_mean_studs"], mean(distances), places=3)
            self.assertAlmostEqual(body["brake_distance_std_studs"], pstdev(distances), places=3)
            self.assertAlmostEqual(body["brake_distance_min_studs"], min(distances), places=6)
            self.assertAlmostEqual(body["brake_distance_max_studs"], max(distances), places=6)
            m = mean(distances)
            delta = (max(distances) - min(distances)) / m * 100 if m > 0 else None
            if delta is None:
                self.assertIsNone(body["brake_distance_delta_pct"])
            else:
                self.assertAlmostEqual(body["brake_distance_delta_pct"], delta, places=3)
            all_stopped = all(r["measurements"]["summary"]["t03"].get("stopped") for r in group)
            self.assertEqual(
                body.get("repeatability_ok"), bool(all_stopped and delta is not None and delta <= REPEAT_TOL_PCT)
            )
            self.assertTrue(body.get("repeatability_ok"), "rozptyl drahy nad 5 %% nebo nezastaveni (%s)" % config_id)


if __name__ == "__main__":
    unittest.main()

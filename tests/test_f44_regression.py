"""F4.4+ regresni test harness-vystupu T03 (Agent H1, rozsireno F5-C: Agent C).

Validuje exporty outboxu (bridge/outbox -> vehicle-data/telemetry/f*/<kohorta>.json):
  - schema pole per-run vystupu (TelemetrieCollector.GetRunOutput),
  - prave 3 repetice na (config_id, scenario_id),
  - T03 metriky v summary.t03 (brake_distance_studs, stopping_time_s, ABS),
  - nezavisly prepocet brake_distance z XZ vzorku (kanonicka definice, viz nize),
  - agregat SUMMARY-<config>-T03 (mean/std/min/max/delta, repeatability +/-5 %),
  - roll_deg kanal (roll z CFrame; od F5-C).

Kohorty: adresare vehicle-data/telemetry/f*/ se objevuji dynamicky
(f44 i budouci f55). Kohortova politika:
  - "f44" je LEGACY kohorta se dvema zdokumentovanymi defekty:
    (a) defekt 5 (F44-T03-FINAL cast 4 bod 5): SUMMARY agreguje FULL-vzorky,
        zatimco run-docs nesou metriky prepocitane z KEPT (decimovanych) vzorku.
        Krizova shoda SUMMARY vs run-docs se proto kontroluje jen v ohranicene
        toleranci (relativni odchylka < 5 %; mereno 0.6-1.1 %), ne exaktne.
    (b) defekt F5-4 (F44-T03-FINAL cast 2): vzorky nemaji roll_deg kanal
        (SampleOnce ho pred F5-C nezapisoval). Absence je pinovana jako znamy
        stav, ne chyba.
  - nove kohorty (f55+) musi plnit striktni kontrakt F5-C: roll_deg ciselny
    v kazdem vzorku a SUMMARY agregat exaktne z kept-vzorku run-docs
    (mean/std na 3 des. mista, min/max na 6), protoze plati pravidlo
    "agregace vzdy z kept" (viz TelemetryCollector.DecimateForOutbox).

Zamerne se NEvyzaduje repeatability_ok=True: verdikt opakovatelnosti je
fyzika kampane, ne kodovy regresni signal (F44 kampan merene FAIL, obe delty
>> 5 %). Test hlida, ze priznak odpovida pravidlu
(ok == vsechny stopped a delta <= 5 %), ne jeho hodnotu.

Prazdny/chybejici telemetry koren = SKIP s duvodem (legitimni PENDING:
Studio-beh dosud nemeren v Roblox runtime; zadna data zatim neexistuji).
Stdlib only, zadne sitove sluzby.
"""
import json
import math
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEMETRY_ROOT = os.path.join(ROOT, "vehicle-data", "telemetry")

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

# Legacy kohorty se zdokumentovanymi defekty (viz modulovy docstring).
LEGACY_COHORTS = {"f44"}
# Ohranicena tolerance krizove shody SUMMARY vs run-docs pro legacy kohorty
# (defekt 5: full- vs kept-agregace; relativni odchylka, mereno <= 1.5 %).
LEGACY_SUMMARY_REL_TOL = 0.05


def discover_cohorts():
    """Vrati {nazev_kohorty: adresar} pro vehicle-data/telemetry/f*/ serazene.

    Kohorta = adresar jehoz jmeno je 'f' + cislo (f44, budouci f55, ...).
    """
    found = {}
    if not os.path.isdir(TELEMETRY_ROOT):
        return found
    for name in sorted(os.listdir(TELEMETRY_ROOT)):
        if len(name) >= 2 and name[0] == "f" and name[1:].isdigit():
            path = os.path.join(TELEMETRY_ROOT, name)
            if os.path.isdir(path):
                found[name] = path
    return found


def load_cohort(path):
    """Nacte vsechny *.json z adresare kohorty. Vraci (runs, summaries).

    runs: per-run vystupy; summaries: agregaty SUMMARY-*-T03.
    Vraci (None, None) pri prazdnem adresari.
    """
    docs = []
    for name in sorted(os.listdir(path)):
        if not name.endswith(".json"):
            continue
        full = os.path.join(path, name)
        with open(full, encoding="utf-8") as fh:
            docs.append((name, json.load(fh)))
    if not docs:
        return None, None
    runs = [d for _, d in docs if not isinstance(d, dict) or d.get("type") != "t03_summary"]
    summaries = [d for _, d in docs if isinstance(d, dict) and d.get("type") == "t03_summary"]
    return runs, summaries


def require_cohorts(testcase):
    cohorts = discover_cohorts()
    if not cohorts:
        testcase.skipTest(
            "PENDING: vehicle-data/telemetry neobsahuje zadnou kohortu f* "
            "(Studio-beh T03 dosud nemeren, legitimni PENDING)"
        )
    loaded = {}
    for name, path in cohorts.items():
        runs, summaries = load_cohort(path)
        if runs is None:
            testcase.skipTest("PENDING: kohorta %s je prazdna (dosud nemereno)" % name)
        assert runs is not None and summaries is not None
        loaded[name] = (runs, summaries)
    return loaded


def iter_cohorts(testcase):
    """Yielduje (nazev, runs, summaries) pro kazdou kohortu."""
    loaded = require_cohorts(testcase)
    for name in sorted(loaded):
        runs, summaries = loaded[name]
        yield name, runs, summaries


def xz_speed(v):
    if not isinstance(v, dict):
        return None
    try:
        return math.sqrt(v["x"] ** 2 + v["z"] ** 2)
    except (KeyError, TypeError):
        return None


def recompute_brake_distance(samples):
    """Nezavisly prepocet: kumulativni XZ draha do prvniho vzorku s v_xz < 0.1.

    KANONICKA DEFINICE brake_distance (start->stop), zrcadli
    ScenarioRunner.ComputeT03Metrics (jedina implementace pouzita vsude):
    kumulativni XZ vzdalenost od prvniho vzorku do prvniho vzorku
    s XZ-rychlosti < 0.1 (prah zastaveni T03); nezastavi-li vuz do konce
    zaznamu, draha i cas se berou do konce zaznamu (stopped=False).
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


def repeatability_rule(distances, all_stopped):
    """Pravidlo opakovatelnosti: vsechny stopped a delta <= 5 %."""
    if not distances or not all_stopped:
        return False
    m = mean(distances)
    if m <= 0:
        return False
    return (max(distances) - min(distances)) / m * 100 <= REPEAT_TOL_PCT


class TestCohortDiscovery(unittest.TestCase):
    """Dynamicky objev kohort vehicle-data/telemetry/f*/."""

    def test_cohorts_discovered(self):
        cohorts = discover_cohorts()
        self.assertIn("f44", cohorts, "chybi baseline kohorta f44")
        for name, path in sorted(cohorts.items()):
            names = [n for n in os.listdir(path) if n.endswith(".json")]
            self.assertGreater(len(names), 0, "kohorta %s nema zadne JSON" % name)


class TestF44Schema(unittest.TestCase):
    """Schema pole per-run vystupu + agregatu (vsechny kohorty)."""

    def test_required_fields(self):
        for _, runs, _ in iter_cohorts(self):
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
        for _, runs, _ in iter_cohorts(self):
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
        for _, _, summaries in iter_cohorts(self):
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


class TestRollChannel(unittest.TestCase):
    """roll_deg kanal: legacy absence pinovana, nove kohorty striktne."""

    def test_roll_deg_absent_in_legacy(self):
        # Znamy stav kohorty f44 (defekt F5-4): SampleOnce pred F5-C roll_deg
        # nezapisoval. Pinuje rozsah defektu; objevi-li se roll_deg v legacy
        # exportech, je treba aktualizovat kohortovou politiku.
        for cohort, runs, _ in iter_cohorts(self):
            if cohort not in LEGACY_COHORTS:
                continue
            for run in runs:
                for i, s in enumerate(run["measurements"]["samples"]):
                    self.assertNotIn(
                        "roll_deg", s, "neocekavany roll_deg ve vzorku %d (%s, legacy %s)" % (i, run.get("run_id"), cohort)
                    )

    def test_roll_deg_present_in_strict(self):
        # Striktni kontrakt F5-C pro nove kohorty (f55+): roll_deg ciselny
        # v kazdem vzorku (roll z CFrame, konvence ReadStartRollDeg).
        for cohort, runs, _ in iter_cohorts(self):
            if cohort in LEGACY_COHORTS:
                continue
            for run in runs:
                for i, s in enumerate(run["measurements"]["samples"]):
                    self.assertIsInstance(
                        s.get("roll_deg"), (int, float), "chybi/neciselny roll_deg vzorek %d (%s, %s)"
                        % (i, run.get("run_id"), cohort)
                    )


class TestF44Repetitions(unittest.TestCase):
    """Prave 3 repetice na (config_id, scenario_id) v kazde kohorte."""

    def test_three_reps_per_config_scenario(self):
        for cohort, runs, _ in iter_cohorts(self):
            groups = {}
            for run in runs:
                key = (run.get("config_id"), run.get("scenario_id"))
                groups.setdefault(key, []).append(run.get("run_id"))
            self.assertGreater(len(groups), 0, "kohorta %s bez behu" % cohort)
            for key, ids in sorted(groups.items(), key=str):
                self.assertEqual(
                    len(ids), EXPECTED_REPS, "kohorta %s skupina %s ma %d behu (ocekavano %d): %s"
                    % (cohort, key, len(ids), EXPECTED_REPS, ids)
                )


class TestF44T03Metrics(unittest.TestCase):
    """T03 metriky: pritomnost, prepocet z XZ, ABS tvar, agregat."""

    def t03_runs(self, runs, cohort):
        t03 = [r for r in runs if r.get("scenario_id") == "T03"]
        if not t03:
            self.skipTest("PENDING: zadny beh T03 v kohorte %s" % cohort)
        return t03

    def test_t03_metrics_present(self):
        for cohort, runs, _ in iter_cohorts(self):
            for run in self.t03_runs(runs, cohort):
                summary = run["measurements"].get("summary") or {}
                t03 = summary.get("t03")
                self.assertIsInstance(t03, dict, "chybi summary.t03 v %s (%s)" % (run.get("run_id"), cohort))
                self.assertGreater(t03.get("brake_distance_studs", 0), 0, "nekladna draha v %s" % run.get("run_id"))
                self.assertGreater(t03.get("stopping_time_s", 0), 0, "nekladny cas v %s" % run.get("run_id"))

    def test_brake_distance_recompute(self):
        for cohort, runs, _ in iter_cohorts(self):
            for run in self.t03_runs(runs, cohort):
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
        for cohort, runs, _ in iter_cohorts(self):
            for run in self.t03_runs(runs, cohort):
                t03 = run["measurements"]["summary"]["t03"]
                self.assertIn("abs", t03, "chybi summary.t03.abs v %s" % run.get("run_id"))
                abs_info = t03["abs"]
                if abs_info.get("active") is None:
                    self.assertTrue(abs_info.get("reason"), "abs null bez duvodu v %s" % run.get("run_id"))
                else:
                    self.assertIsInstance(abs_info["active"], bool)
                    self.assertIsInstance(abs_info.get("active_samples"), int)

    def test_summary_aggregate(self):
        for cohort, runs, summaries in iter_cohorts(self):
            t03 = [r for r in runs if r.get("scenario_id") == "T03"]
            if not t03:
                continue
            by_config = {}
            for run in t03:
                by_config.setdefault(run.get("config_id"), []).append(run)
            by_summary = {d.get("config_id"): d for d in summaries}
            for config_id, group in sorted(by_config.items(), key=str):
                self.assertIn(config_id, by_summary, "chybi SUMMARY agregat pro %s (%s)" % (config_id, cohort))
                doc = by_summary[config_id]
                body = doc["measurements"]["summary"]
                distances = []
                for r in group:
                    t03m = (r["measurements"]["summary"] or {}).get("t03")
                    self.assertIsInstance(t03m, dict, "chybi summary.t03 v %s" % r.get("run_id"))
                    distances.append(t03m["brake_distance_studs"])
                # Struktura plati vzdy.
                self.assertEqual(body.get("n"), len(group))
                self.assertEqual(sorted(body.get("run_ids")), sorted(r["run_id"] for r in group))
                # Vnitrni konzistence tela: delta/ok odvozene z vlastnich cisel.
                m_body = body["brake_distance_mean_studs"]
                delta_body = (body["brake_distance_max_studs"] - body["brake_distance_min_studs"]) / m_body * 100
                self.assertAlmostEqual(body["brake_distance_delta_pct"], delta_body, places=3)
                all_stopped = all(
                    ((r["measurements"]["summary"] or {}).get("t03") or {}).get("stopped") for r in group
                )
                self.assertEqual(
                    body.get("repeatability_ok"),
                    bool(all_stopped and delta_body <= REPEAT_TOL_PCT),
                    "repeatability_ok neodpovida pravidlu (%s, %s)" % (cohort, config_id),
                )
                # Krizova konzistence SUMMARY vs run-docs: striktne pro nove
                # kohorty, ohranicene pro legacy (defekt 5).
                if cohort in LEGACY_COHORTS:
                    for field, kept in (
                        ("brake_distance_mean_studs", mean(distances)),
                        ("brake_distance_std_studs", pstdev(distances)),
                        ("brake_distance_min_studs", min(distances)),
                        ("brake_distance_max_studs", max(distances)),
                    ):
                        if kept:
                            rel = abs(body[field] - kept) / abs(kept)
                            self.assertLessEqual(
                                rel, LEGACY_SUMMARY_REL_TOL,
                                "legacy divergence %s=%f nad mezi (%s, %s)" % (field, rel, cohort, config_id),
                            )
                else:
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
                    self.assertEqual(
                        body.get("repeatability_ok"),
                        repeatability_rule(distances, all_stopped),
                        "repeatability_ok neodpovida pravidlu z run-docs (%s, %s)" % (cohort, config_id),
                    )
                # Verdikt opakovatelnosti se ZAMERNE nevyzaduje True: je to
                # fyzika kampane (F44: merene FAIL, delty >> 5 %), ne kodovy
                # signal. Regrese hlida konzistenci a pravidlo, ne vysledek.


if __name__ == "__main__":
    unittest.main()

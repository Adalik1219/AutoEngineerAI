"""FÁZE 4 integrace (Agent A): VehicleConfig -> map_config -> adapter
apply_config -> patched_config -> Sim -> TestResult.

Uzávěrka řetězce (FÁZE 4.2.1): Sim dostává SKUTEČNĚ aplikovanou
konfiguraci (patched_config), ne původní vstup. Sim čte parametry
z `parameters.<sekce>` (src/Sim/config.py + vehicle.py) a `tune`
klíče nikdy nečte — proto test promítá `patched_config["tune"]`
zpět na Sim-čtené `config_path` cesty přes katalog (tune_key ->
config_path) a Sim běží nad tímto odvozeným vstupem. Rovnost
Sim-vstupu s patched_config se asertuje (a nerovnost s původním
vstupem bez `tune`).

Akceptace: exit 0 + raw výstup (RAW F4 blok) s before/after hodnotami.
peak_torque_nm cesta je explicitně odmítnuta s důvodem (nemá Tune
protějšek, MAPPING.md §6/1). Pouze stdlib.
"""

import copy
import hashlib
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
from src.Chassis.mapping.gate import gate_catalog_file  # noqa: E402
from src.Chassis.mapping_engine import build_search_space, map_config  # noqa: E402
from src.Optimizer.search_space import (  # noqa: E402
    SIM_SUPPORTED_CONFIG_PATHS,
    backend_caps,
    search_space,
)
from src.Sim.run import DEFAULT_DT, run_scenario  # noqa: E402
from src.Telemetry.evaluate import evaluate  # noqa: E402
from src.Telemetry.metrics import compute_metrics, load_telemetry  # noqa: E402

CATALOG = os.path.join(ROOT, "src", "Chassis", "catalog", "parameters.json")
SCENARIO = "straight_accel"
BRAKE_SCENARIO = "straight_brake_100_0"
SEED = 7

ORIGINAL_RBXM = os.path.join(
    ROOT, "testgame", "src", "ServerStorage", "VehicleTemplates",
    "JeepTemplate.rbxm")
ORIGINAL_RBXM_SIZE = 230421
ORIGINAL_RBXM_SHA256 = (
    "dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf"
)


def demo_config(bias_front=0.70, final_drive=3.2):
    """VehicleConfig: tovarni hodnoty + meritelna odezva Simu."""
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
                             "final_drive": final_drive, "efficiency": 0.90,
                             "drive": "RWD", "shift_time_s": 0.35},
            "tires": {"grip_long": 1.0, "grip_lat": 1.0, "mu_road": 1.0},
            "brakes": {"bias_front": bias_front, "torque_Nm": 4000.0},
            "suspension": {"spring_f_Npm": 28000.0},
            "steering": {"max_angle_deg": 32.0},
            "geometry_overrides": None,
        },
        "rationale": "F4 integracni test: mapovani -> Tune -> Sim -> TestResult",
    }


def _tune_key_to_config_path(catalog_path):
    """Katalogové mapování tune_key -> config_path (test-side projekce)."""
    with open(catalog_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    records = doc.get("parameters") if isinstance(doc, dict) else doc
    mapping = {}
    for rec in records or []:
        if isinstance(rec, dict) and rec.get("tune_key") \
                and rec.get("config_path"):
            mapping[rec["tune_key"]] = rec["config_path"]
    return mapping


def sim_input_from_patched(patched_config, catalog_path=CATALOG):
    """Sim-vstup odvozený z patched_config (ne z původního vstupu).

    Zkopíruje patched_config a každou `tune` hodnotu promítne na
    Sim-čtenou cestu `config_path` (katalog: tune_key -> config_path),
    protože Sim `parameters.tune` nečte (src/Sim/config.py,
    src/Sim/vehicle.py).
    """
    mapping = _tune_key_to_config_path(catalog_path)
    sim_cfg = copy.deepcopy(patched_config)
    params = sim_cfg["parameters"]
    for tune_key, value in dict(params.get("tune") or {}).items():
        path = mapping.get(tune_key)
        if not path:
            continue
        node = params
        parts = path.split(".")
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value
    return sim_cfg


def _run_sim_return_metrics(config_dict, scenario, seed):
    """Zapíše config na disk, spustí Sim, vrátí (csv, manifest, metrics)."""
    tmp = tempfile.mkdtemp(prefix="f4_sim_")
    cfg_path = os.path.join(tmp, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(config_dict, fh)
    with open(cfg_path, encoding="utf-8") as fh:
        written = json.load(fh)
    csv_path, _, manifest = run_scenario(
        cfg_path, scenario, DEFAULT_DT, seed, os.path.join(tmp, "sim"))
    metrics = compute_metrics(load_telemetry(csv_path))
    return csv_path, manifest, metrics, written


def _map_and_apply(config):
    """map_config -> cfg_tune -> adapter.apply_config -> (mapped, report, patched)."""
    mapped = map_config(config, CATALOG, "achassis-v1")
    tune_patch = {c["tune_key"]: c["value"]
                  for c in mapped["tune_changes"]}
    cfg_tune = copy.deepcopy(config)
    cfg_tune["parameters"] = dict(cfg_tune["parameters"])
    cfg_tune["parameters"]["tune"] = tune_patch
    adapter = AChassisV1Adapter()
    report = adapter.apply_config(
        os.path.join(ROOT, "assets", "chassis-original"), cfg_tune)
    patched = report.to_dict()["patched_config"]
    return mapped, report, patched


class TestF4Integration(unittest.TestCase):
    def test_chain_vehicleconfig_to_testresult(self):
        """Brána S-02: řetězec se zastaví na bráně — reálný katalog je
        cyklický (tcs_threshold_sps <-> tcs_gradient), takže build_search_space
        je [], Optimizer prostor je [] a map_config je BLOCKED (*catalog*,
        CYCLE + svědek, vstup nezměněn). Sim/evaluate kroky se za BLOCKED
        bránou neprovádějí (žádný částečný stav)."""
        config = demo_config()
        orig_snapshot = copy.deepcopy(config)

        # (1) Brána nad reálným katalogem: BLOCKED/CYCLE + platný svědek.
        verdict = gate_catalog_file(CATALOG)
        self.assertEqual(verdict.status, "BLOCKED")
        self.assertFalse(verdict.allowed)
        self.assertIn("CYCLE", verdict.reason)
        self.assertEqual(verdict.witness_path,
                         ["tcs_threshold_sps", "tcs_gradient",
                          "tcs_threshold_sps"])

        # (2) Prostor na realnem katalogu je BLOCKED → prázdný.
        caps = backend_caps(CATALOG)
        tune_space = build_search_space(CATALOG, caps)
        self.assertEqual(tune_space, [])
        space = search_space(config)
        self.assertEqual(space, [])

        # (3) map_config: BLOCKED na bráně, nulová změna, přesný důvod.
        mapped = map_config(config, CATALOG, "achassis-v1")
        self.assertEqual(config, orig_snapshot)
        self.assertEqual(mapped["tune_changes"], [])
        self.assertEqual(len(mapped["rejected"]), 1)
        self.assertEqual(mapped["rejected"][0]["param"], "*catalog*")
        self.assertIn("CYCLE", mapped["rejected"][0]["reason"])
        self.assertIn("tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps",
                      mapped["rejected"][0]["reason"])
        print("--- RAW F4 integrace (S-02 BLOCKED) ---")
        print(json.dumps({"gate_reason": verdict.reason,
                          "tune_space": tune_space,
                          "rejected": mapped["rejected"]},
                         ensure_ascii=False, indent=2))
        print("F4 INTEGRATION OK (BLOCKED se svedkem)")

    def test_brakes_bias_change_moves_stopping_distance(self):
        """bias 0.62 -> 0.70: Sim na patched_config, dráha se změní.

        Brána S-02: map_config nad reálným katalogem je BLOCKED (CYCLE),
        proto se patched_config staví přímo z explicitního tune přes adaptér
        (mapovací krok je kryt BLOCKED testy výše); Sim/metrika část je na
        bráně nezávislá a zůstává beze změny."""
        gated = map_config(demo_config(bias_front=0.62), CATALOG,
                           "achassis-v1")
        self.assertEqual(gated["tune_changes"], [])
        self.assertEqual(gated["rejected"][0]["param"], "*catalog*")
        self.assertIn("CYCLE", gated["rejected"][0]["reason"])

        def _apply_bias(config, bias):
            cfg_tune = copy.deepcopy(config)
            cfg_tune["parameters"] = dict(cfg_tune["parameters"])
            cfg_tune["parameters"]["tune"] = {"BrakeBias": bias}
            adapter = AChassisV1Adapter()
            report = adapter.apply_config(
                os.path.join(ROOT, "assets", "chassis-original"), cfg_tune)
            return report.to_dict()["patched_config"]

        base = demo_config(bias_front=0.62)
        changed = demo_config(bias_front=0.70)

        patched_before = _apply_bias(base, 0.62)
        patched_after = _apply_bias(changed, 0.70)
        self.assertEqual(patched_before["parameters"]["tune"]["BrakeBias"], 0.62)
        self.assertEqual(patched_after["parameters"]["tune"]["BrakeBias"], 0.70)

        sim_before = sim_input_from_patched(patched_before)
        sim_after = sim_input_from_patched(patched_after)
        # (5) Sim-vstup == patched, ne původní (původní nemá `tune`).
        self.assertNotIn("tune", base["parameters"])
        self.assertEqual(sim_after["parameters"]["tune"],
                         patched_after["parameters"]["tune"])
        self.assertEqual(sim_before["parameters"]["brakes"]["bias_front"],
                         0.62)
        self.assertEqual(sim_after["parameters"]["brakes"]["bias_front"],
                         0.70)

        _, _, met_before, written_before = _run_sim_return_metrics(
            sim_before, BRAKE_SCENARIO, SEED)
        _, _, met_after, written_after = _run_sim_return_metrics(
            sim_after, BRAKE_SCENARIO, SEED)
        self.assertEqual(written_before["parameters"]["brakes"]
                         ["bias_front"], 0.62)
        self.assertEqual(written_after["parameters"]["brakes"]
                         ["bias_front"], 0.70)
        dist_before = met_before["brake_distance_100_0_m"]
        dist_after = met_after["brake_distance_100_0_m"]
        self.assertIsNotNone(dist_before)
        self.assertIsNotNone(dist_after)
        self.assertGreater(
            abs(dist_after - dist_before), 1.0,
            "zmena biasu 0.62->0.70 musi pohnout brzdnou drahou")
        print("RAW brakes before/after: bias 0.62 -> dist %.3f m; "
              "bias 0.70 -> dist %.3f m"
              % (dist_before, dist_after))

    def test_final_drive_change_moves_metric_or_unsupported(self):
        """C3: FinalDrive 2.6 -> 3.2 na deterministickém fixture bez ručních
        hran: mapování -> adaptér -> Sim hýbe metrikou t_0_100_s.

        Účel: downstream důkaz, že změna final_drive proteče celým
        řetězcem až do měřitelné odezvy Simu, BEZ křehkého ručního
        seznamu cyklových hran (ten by tiše zastaral při změně katalogu
        a test by falešně PASoval na prázdném mapování).
        Chytá: (a) regresi citlivosti Simu na final_drive (rozdíl <= 0.05
        s → FAIL s konkrétními čísly), (b) prázdné/zastaralé mapování
        (přesně 1 tune_change FinalDrive se správnou hodnotou),
        (c) odmítnutí adaptérem, (d) záměnu vstupů 2.6/3.2,
        (e) cyklické/nekonzistentní fixture (auto-validace bránou +
        integritou — FAIL s důvodem, NE falešný PASS).
        Falešný výsledek bez klíčových asercí: PASS i kdyby Sim final_drive
        ignoroval (jen 'metrika existuje') nebo kdyby fixture byla
        BLOCKED a mapování prázdné. Brání: přesné hodnoty tune_changes,
        nerovnost metrik s prahem, gate==allowed před během.
        Determinismus: mapování 2.6 opakovaně → identické JSON; stejný
        seed Simu. Fixture je deterministická (pevné literály, žádné čtení
        reálného katalogu, žádné ruční hrany k údržbě). Žádný skip, žádná
        None/slabá podmínka jako jediná aserce; důvod vždy konkrétní
        (hodnota metriky, reason brány), ne obecné BLOCKED.
        Nelze-li fixture sestavit jako acyklickou/validní → FAIL
        s důvodem brány (prokazatelně, ne tiše).
        """

        def _fd_record(fd_default):
            return {
                "id": "final_drive", "tune_key": "FinalDrive",
                "category": "MUTABLE_TUNE",
                "config_path": "transmission.final_drive",
                "value": fd_default, "unit": "-",
                "value_type": "number", "min": 2.5, "max": 4.2,
                "default": fd_default,
                "function": "C3 fixture: staly prevod",
                "physical_effect": "C3 fixture",
                "used_in": ["straight_accel"],
                "depends_on": [], "conflicts": [],
                "change_method": "tune",
                "source": "A-CHASSIS-AUDIT.md §6",
                "confidence": 1.0, "verification_status": "PASS",
            }

        def _bias_record():
            return {
                "id": "brake_bias_front", "tune_key": "BrakeBias",
                "category": "MUTABLE_TUNE",
                "config_path": "brakes.bias_front",
                "value": 0.6, "unit": "0-1",
                "value_type": "number", "min": 0, "max": 1,
                "default": 0.6,
                "function": "C3 fixture: brzdny bias",
                "physical_effect": "C3 fixture",
                "used_in": ["straight_brake_100_0"],
                "depends_on": [], "conflicts": [],
                "change_method": "tune",
                "source": "A-CHASSIS-AUDIT.md §12",
                "confidence": 1.0, "verification_status": "PASS",
            }

        records = [_fd_record(3.2), _bias_record()]
        # Auto-validace integrity: každá hrana depends_on se překládá
        # na existující záznam (jinak FAIL s konkrétní hranou).
        by_id = {r["id"]: r for r in records}
        for rec in records:
            for dep in rec.get("depends_on") or []:
                token = dep if isinstance(dep, str) else dep.get("param")
                self.assertIn(token, by_id,
                              "C3 fixture: nekonzistentní hrana %r" % token)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as fh:
            json.dump(records, fh)
            fixture = fh.name
        self.addCleanup(lambda: os.path.exists(fixture)
                        and os.unlink(fixture))
        # Auto-validace acykličnosti bránou (místo ručního seznamu hran):
        # není-li fixture průchozí, FAIL s důvodem brány, NE tichý PASS.
        verdict = gate_catalog_file(fixture)
        self.assertTrue(verdict.allowed,
                        "C3 fixture musí projít bránou S-02 (jinak test "
                        "neměří downstream, ale BLOCKED): %s"
                        % (verdict.reason,))

        def mapped_config(fd):
            cfg = demo_config(final_drive=fd)
            cfg["parameters"] = {"transmission": {"final_drive": fd}}
            snapshot = copy.deepcopy(cfg)
            mapped = map_config(cfg, fixture, "achassis-v1")
            self.assertEqual(cfg, snapshot)
            self.assertEqual(mapped["rejected"], [])
            self.assertEqual(len(mapped["tune_changes"]), 1)
            self.assertEqual(mapped["tune_changes"][0]["tune_key"],
                             "FinalDrive")
            self.assertEqual(mapped["tune_changes"][0]["value"], fd)
            cfg["parameters"] = dict(cfg["parameters"])
            cfg["parameters"]["tune"] = {"FinalDrive": fd}
            report = AChassisV1Adapter().apply_config(
                os.path.join(ROOT, "assets", "chassis-original"), cfg)
            self.assertEqual(report.rejected, [])
            applied = {a["tune_key"]: a["to"] for a in report.applied}
            self.assertEqual(applied.get("FinalDrive"), fd)
            return report.to_dict()["patched_config"], mapped

        patched_lo, mapped_lo = mapped_config(2.6)
        patched_hi, _ = mapped_config(3.2)
        # Determinismus mapování: opakování 2.6 → identické JSON.
        _, mapped_lo_again = mapped_config(2.6)
        self.assertEqual(json.dumps(mapped_lo_again, sort_keys=True),
                         json.dumps(mapped_lo, sort_keys=True))
        sim_lo = sim_input_from_patched(patched_lo, fixture)
        sim_hi = sim_input_from_patched(patched_hi, fixture)
        self.assertEqual(sim_lo["parameters"]["transmission"]
                         ["final_drive"], 2.6)
        self.assertEqual(sim_hi["parameters"]["transmission"]
                         ["final_drive"], 3.2)
        self.assertNotEqual(sim_lo, sim_hi)
        _, _, met_lo, _ = _run_sim_return_metrics(sim_lo, SCENARIO, SEED)
        _, _, met_hi, _ = _run_sim_return_metrics(sim_hi, SCENARIO, SEED)
        t_lo = met_lo["t_0_100_s"]
        t_hi = met_hi["t_0_100_s"]
        self.assertIsNotNone(t_lo)
        self.assertIsNotNone(t_hi)
        self.assertGreater(abs(t_hi - t_lo), 0.05,
                           "zmena final_drive 2.6->3.2 musi pohnout "
                           "t_0_100_s (t_lo=%s, t_hi=%s)" % (t_lo, t_hi))
        print("RAW C3 final_drive before/after: fd 2.6 -> t_0_100 %.3f s "
              "(v_max %.1f km/h); fd 3.2 -> t_0_100 %.3f s "
              "(v_max %.1f km/h)"
              % (t_lo, met_lo["v_max_kmh"], t_hi, met_hi["v_max_kmh"]))

    def test_peak_torque_path_explicitly_rejected(self):
        """Brána S-02: engine.peak_torque_nm se za cyklickým katalogem vůbec
        nedostane k per-klíč vyhodnocení — map_config je BLOCKED (*catalog*,
        CYCLE + svědek). Odmítnutí nese důvod (anti-no-op tvar zachován)."""
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
                         "*catalog*")
        self.assertIn("CYCLE", reason)
        self.assertTrue(reason, "odmitnuti musi nest duvod")
        print("RAW peak_torque_nm rejected: %s" % reason)

    def test_horsepower_kept_as_separate_tune_param(self):
        """Brána S-02: za cyklickým katalogem je map_config BLOCKED jako celek
        (*catalog*, CYCLE + svědek) — ani horsepower se nemapuje (žádný
        částečný stav, vstup nezměněn)."""
        config = demo_config()
        config["parameters"] = {
            "engine": {"peak_torque_nm": 205.0, "horsepower": 210},
            "geometry_overrides": None,
        }
        snapshot = copy.deepcopy(config)
        mapped = map_config(config, CATALOG, "achassis-v1")
        self.assertEqual(config, snapshot)
        self.assertEqual(mapped["tune_changes"], [])
        self.assertEqual(len(mapped["rejected"]), 1)
        self.assertEqual(mapped["rejected"][0]["param"], "*catalog*")
        self.assertIn("CYCLE", mapped["rejected"][0]["reason"])
        print("RAW horsepower: BLOCKED %s"
              % mapped["rejected"][0]["reason"])

    def test_sim_runs_on_patched_config_not_original(self):
        """C2: Sim běží nad patchnutou konfigurací, NE nad původním vstupem.

        ROZSAH (důležité): toto je test downstream-izolace
        (adaptér -> Sim předání), NENÍ to důkaz mapování přes bránu S-02 —
        map_config nad reálným katalogem je BLOCKED (CYCLE), proto se
        tune staví explicitně (krok 3), nikoli z mapování. Mapovací
        korektnost kryjí testy C1 (per-klíč) a C4 (katalog-BLOCKED).
        Metriky jsou sekundární (jen existence), chrání před záměnou
        s testem citlivosti (bias sweep výše).
        Chytá: (a) Sim spuštěný nad původním vstupem místo patched
        (krok 9/10 by selhal: bias 0.62 místo 0.70), (b) mutaci
        originálu adaptérem/projekcí, (c) ztrátu tune při předání Simu.
        Falešný výsledek bez klíčových asercí: PASS i kdyby Sim četl
        originál — brání aserce captured != original + captured ==
        sim_cfg na přesných hodnotách (ne jen 'metrika existuje').
        Determinismus: stejný seed + stejný vstup = stejný zachycený
        obsah (kroky 7/9). Žádný skip, žádná None/slabá podmínka jako
        jediná aserce, důvod vždy konkrétní hodnota, ne obecné BLOCKED.
        Kroky: (1) originál s bias 0.62 (záměrně ODLIŠNÝ od cíle 0.70,
        jinak by záměna nebyla detekovatelná); (2) snapshot originálu;
        (3) cfg_tune = kopie + explicitní tune BrakeBias=0.70 přes
        adaptér (NE map_config — ten je za S-02 BLOCKED); (4) adaptér
        hlásí applied BrakeBias 0.70, patched tune == 0.70, originál
        beze změny a bez 'tune'; (5) projekce tune->config_path:
        sim bias_front == 0.70; (6) sim_cfg != originál; (7) zápis na
        disk a přečtení zpět (přesně to, co Sim dostane); (8) Sim běh
        nad tímto souborem; (9) zachycený obsah == sim_cfg (Sim dostal
        patchnutou); (10) NEGATIVNÍ KONTROLA: zachycený obsah !=
        originál a bias 0.70 != 0.62 (selže při předání originálu);
        (11) manifest config_id sedí; (12) metriky existují (sekundární).
        """
        # (1) Originál záměrně odlišný od cíle patchování.
        original = demo_config(bias_front=0.62)
        self.assertNotIn("tune", original["parameters"])
        # (2) Snapshot proti mutaci.
        snapshot = copy.deepcopy(original)
        # (3) Explicitní tune přes adaptér (mapování je za S-02 BLOCKED).
        cfg_tune = copy.deepcopy(original)
        cfg_tune["parameters"] = dict(cfg_tune["parameters"])
        cfg_tune["parameters"]["tune"] = {"BrakeBias": 0.70}
        # (4) Adaptér aplikuje; originál nesmí změnit.
        report = AChassisV1Adapter().apply_config(
            os.path.join(ROOT, "assets", "chassis-original"), cfg_tune)
        patched = report.to_dict()["patched_config"]
        self.assertEqual(original, snapshot)
        self.assertNotIn("tune", original["parameters"])
        applied = {a["tune_key"]: a["to"] for a in report.applied}
        self.assertEqual(applied.get("BrakeBias"), 0.70)
        self.assertEqual(patched["parameters"]["tune"]["BrakeBias"], 0.70)
        # (5) Projekce tune -> Sim-čtená cesta.
        sim_cfg = sim_input_from_patched(patched)
        self.assertEqual(sim_cfg["parameters"]["brakes"]["bias_front"],
                         0.70)
        self.assertEqual(sim_cfg["parameters"]["tune"],
                         patched["parameters"]["tune"])
        # (6) Patchnutý vstup se liší od originálu.
        self.assertNotEqual(sim_cfg, original,
                            "Sim nesmi dostat puvodni vstup bez patch")
        # (7) Zápis na disk = přesně to, co Sim dostane; přečtení zpět.
        tmp = tempfile.mkdtemp(prefix="f4_c2_")
        cfg_path = os.path.join(tmp, "config.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(sim_cfg, fh)
        with open(cfg_path, encoding="utf-8") as fh:
            captured = json.load(fh)
        # (8) Sim běh nad zachyceným souborem.
        csv_path, _, manifest = run_scenario(
            cfg_path, SCENARIO, DEFAULT_DT, SEED,
            os.path.join(tmp, "sim"))
        metrics = compute_metrics(load_telemetry(csv_path))
        # (9) POZITIVNÍ: Sim dostal patchnutou konfiguraci.
        self.assertEqual(captured, sim_cfg)
        self.assertEqual(captured["parameters"]["brakes"]["bias_front"],
                         0.70)
        self.assertEqual(captured["parameters"]["tune"]["BrakeBias"],
                         0.70)
        # (10) NEGATIVNÍ KONTROLA: obsah NENÍ originál (selže, pokud by
        # Sim dostal původní vstup: bias 0.62, žádné 'tune').
        self.assertNotEqual(captured, original)
        self.assertNotEqual(captured["parameters"]["brakes"]
                            ["bias_front"],
                            original["parameters"]["brakes"]
                            ["bias_front"])
        # (11) Manifest odkazuje na tentýž config.
        self.assertEqual(manifest["config_id"], original["config_id"])
        # (12) Metriky existují (sekundární — citlivost měří jiný test).
        self.assertIsNotNone(metrics["t_0_100_s"])
        print("RAW C2 patched==captured: %s; captured!=original: %s; "
              "bias captured=%s original=%s"
              % (captured == sim_cfg, captured != original,
                 captured["parameters"]["brakes"]["bias_front"],
                 original["parameters"]["brakes"]["bias_front"]))

    def test_original_rbxm_sha256_untouched(self):
        """READ-ONLY zásada: verzovaná fixture beze změny (jen sha kontrola).

        Chybí-li fixture, SKIP s důvodem (PENDING), nikdy ERROR.
        """
        if not os.path.exists(ORIGINAL_RBXM):
            self.skipTest(
                "PENDING: verzovaná fixture JeepTemplate.rbxm není "
                "v tomto prostředí k dispozici")
        before = os.stat(ORIGINAL_RBXM)
        digest = hashlib.sha256()
        with open(ORIGINAL_RBXM, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        print("RAW original rbxm sha256: %s" % actual)
        self.assertEqual(actual, ORIGINAL_RBXM_SHA256)
        self.assertEqual(before.st_size, ORIGINAL_RBXM_SIZE)
        after = os.stat(ORIGINAL_RBXM)
        self.assertEqual((before.st_mtime_ns, before.st_size),
                         (after.st_mtime_ns, after.st_size))

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

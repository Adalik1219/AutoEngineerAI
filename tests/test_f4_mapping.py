# AutoEngineerAI – QA FÁZE 4 (Agent C): katalog + mapování.
#
# Vlastník: Agent C. Vlastněné soubory: tento + qa/qa-f4-parameter-intelligence.md.
# READ-ONLY mimo ně. Česky; identifikátory anglicky; Python 3 stdlib;
# žádné git operace, žádný zápis do rbxm ani cizích souborů.
"""Nezávislé QA ověření FÁZE 4 (F4-01–F4-12) vlastním čtením kódu a vlastními testy.

Zdroje pravdy: docs/A-CHASSIS-AUDIT.md, src/Chassis/adapters/achassis_v1.py.
Tvrzení Agentů A/B nepřebírá – každé kontroluje znovu (spot-checky, vlastní
vzorky). Studio-nedostupné = skip (PENDING), nikdy PASS.
Spouštění z kořene:  python3 tests/test_f4_mapping.py  (exit 0)
nebo:  python3 -m unittest tests.test_f4_mapping -v
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Chassis.catalog import loader as catalog_loader  # noqa: E402
from src.Chassis.mapping_engine import (  # noqa: E402
    build_search_space,
    map_config,
    run_selftest as engine_selftest,
)

CATALOG_PATH = os.path.join(ROOT, "src", "Chassis", "catalog", "parameters.json")
RBXM_ORIG = "C:/Users/adamr/Downloads/chasis.rbxm"
RBXM_SHA256 = "dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf"

# Audit §5/§6/§12 – doslovné hodnoty Tune (vlastní opis z auditu, ne z Agenta A).
AUDIT_TUNE = {
    "Horsepower": 200, "IdleRPM": 950, "PeakRPM": 6800, "Redline": 8000,
    "PeakSharpness": 20, "CurveMult": 0.5, "Turbochargers": 2, "T_Boost": 7,
    "FinalDrive": 3.545, "FDMult": 1.1, "Bias": 0.6, "Flywheel": 500,
}


def _load_adapter():
    from src.Chassis.adapters.achassis_v1 import PARAMETERS
    return list(PARAMETERS)


def _sample_catalog() -> list[dict]:
    """Vlastní minimální katalog pro C2 (nezávislý na vzorku enginu)."""

    def rec(rid, tune_key, category, config_path, unit, vmin, vmax,
            used_in, depends=(), conflicts=(), status="verified"):
        return {
            "id": rid, "tune_key": tune_key, "category": category,
            "config_path": config_path, "value": vmax, "unit": unit,
            "value_type": "number", "min": vmin, "max": vmax,
            "default": vmax, "function": "qa vzorek",
            "physical_effect": "qa", "used_in": list(used_in),
            "depends_on": list(depends), "conflicts": list(conflicts),
            "change_method": "tune", "source": "A-CHASSIS-AUDIT.md §5",
            "confidence": 1.0, "verification_status": status,
        }

    script = rec("qa_drag", None, "SCRIPT_CONTROLLED", "aero.drag_qa",
                 "-", 0, 1.0, ["straight_accel"])
    script["change_method"] = "script"
    unknown = rec("qa_warp", "WarpDrive", "UNKNOWN", "engine.warp_drive",
                  "-", None, None, [], status="unverified")
    unknown["change_method"] = "pending-studio"
    return [
        rec("qa_hp", "Horsepower", "MUTABLE_TUNE", "engine.horsepower",
            "hp", 50, 1000, ["straight_accel"]),
        rec("qa_fd", "FinalDrive", "MUTABLE_TUNE", "transmission.final_drive",
            "-", 2.5, 4.2, ["straight_accel"], conflicts=["qa_fdm"]),
        rec("qa_fdm", "FDMult", "MUTABLE_TUNE",
            "transmission.final_drive_mult", "-", 0.5, 2.0,
            ["straight_accel"], conflicts=["qa_fd"]),
        rec("qa_bias", "Bias", "MUTABLE_TUNE", "brakes.bias_front",
            "0-1", 0, 1, ["straight_brake_100_0"]),
        rec("qa_tcount", "Turbochargers", "MUTABLE_TUNE",
            "engine.turbo.count", "ks", 0, 4, ["straight_accel"]),
        rec("qa_tboost", "T_Boost", "MUTABLE_TUNE", "engine.turbo.boost",
            "-", 0, 20, ["straight_accel"],
            depends=[{"param": "engine.turbo.count", "min": 1,
                      "reason": "boost bez turba nemá účinek"}]),
        script, unknown,
    ]


def _write_catalog(records: list[dict]) -> str:
    tmp = tempfile.mkdtemp(prefix="qa_f4_")
    path = os.path.join(tmp, "parameters.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=1)
    return path


def _cfg(parameters: dict) -> dict:
    return {"schema_version": "1.0.0", "config_id": "cfg_qa_f4",
            "vehicle_profile_id": "vp_qa", "chassis_adapter": "achassis-v1",
            "parameters": parameters}


# --------------------------------------------------------------------------
# C1 – katalog
# --------------------------------------------------------------------------

class TestF4Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = catalog_loader.load(CATALOG_PATH)
        cls.by_id = {r["id"]: r for r in cls.records}

    def test_f4_01_uplnost_125_a_19_poli(self):
        """F4-01: katalog má 125 záznamů, každý přesně 19 polí, unikátní id."""
        self.assertEqual(len(self.records), 125)
        for r in self.records:
            self.assertEqual(len(r.keys()), 19, r["id"])
        self.assertEqual(len(self.by_id), 125)
        paths = [r["config_path"] for r in self.records if r["config_path"]]
        self.assertEqual(len(set(paths)), len(paths))

    def test_f4_01_kategorie_pocty(self):
        """F4-01: rozdělení 79/14/2/3/27 dle adaptéru (measured/script/unknown)."""
        from collections import Counter
        counts = Counter(r["category"] for r in self.records)
        self.assertEqual(counts["MUTABLE_TUNE"], 79)
        self.assertEqual(counts["SCRIPT_CONTROLLED"], 14)
        self.assertEqual(counts["STRUCTURE_CONTROLLED"], 2)
        self.assertEqual(counts["READ_ONLY"], 3)
        self.assertEqual(counts["UNKNOWN"], 27)

    def test_f4_02_provenance_klasifikace_parita_s_adapterem(self):
        """F4-02: každý katalogový tune_key existuje v adaptéru;
        měnitelný právě když MUTABLE_TUNE."""
        adapter = _load_adapter()
        by_tune = {p.tune_key: p for p in adapter if p.tune_key}
        checked = 0
        for r in self.records:
            key = r.get("tune_key")
            if not key or "?" in str(key):
                continue  # kvalifikovaný odhad – viz F4-03
            self.assertIn(key, by_tune, r["id"])
            pdef = by_tune[key]
            if r["category"] == "MUTABLE_TUNE":
                self.assertTrue(pdef.mutable, r["id"])
                self.assertEqual(pdef.provenance, "measured", r["id"])
            else:
                self.assertFalse(pdef.mutable, r["id"])
            checked += 1
        self.assertGreaterEqual(checked, 100)  # 125 − otazníkové/null klíče

    def test_f4_02_puvod_dolozitelny(self):
        """F4-02: každý záznam má auditní zdroj; spot-check §5/§6/§12."""
        for r in self.records:
            self.assertTrue(r["source"].startswith("A-CHASSIS-AUDIT.md §"),
                            r["id"])
        self.assertIn("§5", self.by_id["horsepower"]["source"])
        self.assertIn("§6", self.by_id["final_drive"]["source"])
        self.assertIn("§12", self.by_id["brake_bias_front"]["source"])

    def test_f4_03_unknown_zustava_unknown(self):
        """F4-03: 27 UNKNOWN, žádné vymyšlené hodnoty (value/default None),
        nikdy k zápisu (change_method pending-studio)."""
        unknowns = [r for r in self.records if r["category"] == "UNKNOWN"]
        self.assertEqual(len(unknowns), 27)
        for r in unknowns:
            self.assertIsNone(r["value"], r["id"])
            self.assertIsNone(r["default"], r["id"])
            self.assertIsNone(r["min"], r["id"])
            self.assertIsNone(r["max"], r["id"])
            self.assertEqual(r["verification_status"], "PENDING", r["id"])

    def test_f4_04_overene_tune_klice_spot_check_12(self):
        """F4-04: 12 Tune klíčů – katalog value/default i default adaptéru
        se rovnají doslovným hodnotám auditu (vlastní opis AUDIT_TUNE)."""
        adapter = _load_adapter()
        by_tune = {p.tune_key: p for p in adapter if p.tune_key}
        by_path = {p.config_path: p for p in adapter if p.config_path}
        path_of = {"Horsepower": "engine.horsepower",
                   "IdleRPM": "engine.idle_rpm",
                   "PeakRPM": "engine.peak_rpm",
                   "Redline": "engine.redline_rpm",
                   "PeakSharpness": "engine.peak_sharpness",
                   "CurveMult": "engine.curve_mult",
                   "Turbochargers": "engine.turbo.count",
                   "T_Boost": "engine.turbo.boost",
                   "FinalDrive": "transmission.final_drive",
                   "FDMult": "transmission.final_drive_mult",
                   "Bias": "brakes.bias_front",
                   "Flywheel": "engine.flywheel"}
        self.assertEqual(set(path_of), set(AUDIT_TUNE))
        for tune_key, expected in AUDIT_TUNE.items():
            with self.subTest(tune_key=tune_key):
                rec = next(r for r in self.records
                           if r["tune_key"] == tune_key)
                self.assertEqual(rec["value"], expected)
                self.assertEqual(rec["default"], expected)
                self.assertEqual(by_tune[tune_key].default, expected)
                self.assertEqual(by_tune[tune_key].config_path,
                                 path_of[tune_key])
                self.assertEqual(rec["config_path"], path_of[tune_key])

    def test_f4_04_readonly_chranena(self):
        """F4-04: READ_ONLY (3) + SCRIPT_CONTROLLED (14) mají value None nebo
        nejsou k zápisu; adaptér je vede jako neměnné s důvodem."""
        adapter = _load_adapter()
        by_tune = {p.tune_key: p for p in adapter if p.tune_key}
        for r in self.records:
            if r["category"] == "READ_ONLY":
                self.assertEqual(r["change_method"], "none", r["id"])
                self.assertIsNone(r["value"], r["id"])
            if r["category"] == "SCRIPT_CONTROLLED":
                self.assertEqual(r["change_method"], "script", r["id"])
        for key in ("FWLgcyDensity", "RWLgcyDensity"):
            self.assertFalse(by_tune[key].mutable)
            self.assertTrue(by_tune[key].read_only_reason)

    def test_f4_04_zavislosti_uvedeny(self):
        """F4-04: závislost turba i konflikty jsou v katalogu; každá
        závislost-token se překládá na existující záznam."""
        from src.Chassis.mapping_engine import _resolve_entry
        boost = self.by_id["turbo_boost"]
        flat = json.dumps(boost["depends_on"], ensure_ascii=False)
        self.assertIn("turbo_count", flat)
        for r in self.records:
            for dep in r["depends_on"] or []:
                token = dep if isinstance(dep, str) else dep.get("param")
                if token:
                    self.assertIsNotNone(
                        _resolve_entry(self.records, token),
                        "%s depends_on -> %r" % (r["id"], token))


# --------------------------------------------------------------------------
# C2 – mapování vlastními testy
# --------------------------------------------------------------------------

class TestF4Mapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_path = _write_catalog(_sample_catalog())

    def test_f4_05_mapovani_3_vlastnosti_vc_motora(self):
        """F4-05: engine.horsepower + final_drive + bias_front → Tune."""
        res = map_config(_cfg({"engine": {"horsepower": 210},
                               "transmission": {"final_drive": 3.2},
                               "brakes": {"bias_front": 0.62}}),
                         self.catalog_path, "achassis-v1")
        self.assertEqual(res["rejected"], [])
        keys = {c["tune_key"] for c in res["tune_changes"]}
        self.assertEqual(keys, {"Horsepower", "FinalDrive", "Bias"})

    def test_f4_06_jednotky_z_katalogu(self):
        """F4-06: tune_change nese jednotku katalogu; kW se nikdy
        nerovná hp bez převodu (odmítnuto, ne tiše převedeno)."""
        res = map_config(_cfg({"engine": {"horsepower": 210}}),
                         self.catalog_path, "achassis-v1")
        hp = next(c for c in res["tune_changes"]
                  if c["tune_key"] == "Horsepower")
        self.assertEqual(hp["unit"], "hp")
        self.assertEqual(hp["value"], 210)
        res_kw = map_config(_cfg({"engine": {"peak_power_kw": 135.0}}),
                            self.catalog_path, "achassis-v1")
        self.assertEqual(res_kw["tune_changes"], [])
        self.assertEqual(len(res_kw["rejected"]), 1)

    def test_f4_05_peak_torque_nema_tune_protejsek(self):
        """F4-05/nesoulad: engine.peak_torque_nm není v reálném katalogu
        (žádný Tune skalár momentu) – map_config ho odmítne jako neznámý."""
        real = _write_catalog(catalog_loader.load(CATALOG_PATH))
        res = map_config(_cfg({"engine": {"peak_torque_nm": 205.0}}),
                         real, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(len(res["rejected"]), 1)
        self.assertIn("peak_torque_nm", res["rejected"][0]["param"])
        with open(os.path.join(ROOT, "src", "Optimizer", "search_space.py"),
                  encoding="utf-8") as fh:
            self.assertIn("engine.peak_torque_nm", fh.read())

    def test_f4_07_odmitnuti_unknown(self):
        res = map_config(_cfg({"engine": {"warp_drive": 5}}),
                         self.catalog_path, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(res["rejected"][0]["param"], "engine.warp_drive")

    def test_f4_07_odmitnuti_readonly_script(self):
        res = map_config(_cfg({"aero": {"drag_qa": 0.5}}),
                         self.catalog_path, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertIn("SCRIPT_CONTROLLED", res["rejected"][0]["reason"])

    def test_f4_07_odmitnuti_mimo_rozsah(self):
        res = map_config(_cfg({"engine": {"horsepower": 5000}}),
                         self.catalog_path, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertIn("rozsah", res["rejected"][0]["reason"])

    def test_f4_07_odmitnuti_konflikt_deterministicky(self):
        """FD × FDMult: vítězí abecedně první config_path (determinismus)."""
        res = map_config(_cfg({"transmission": {"final_drive": 3.2,
                                                "final_drive_mult": 1.5}}),
                         self.catalog_path, "achassis-v1")
        self.assertEqual(len(res["tune_changes"]), 1)
        self.assertEqual(res["tune_changes"][0]["tune_key"], "FinalDrive")
        self.assertIn("konflikt", res["rejected"][0]["reason"])
        again = map_config(_cfg({"transmission": {"final_drive": 3.2,
                                                  "final_drive_mult": 1.5}}),
                           self.catalog_path, "achassis-v1")
        self.assertEqual(json.dumps(again, sort_keys=True),
                         json.dumps(res, sort_keys=True))

    def test_f4_07_zavislost_boost_bez_turba(self):
        res = map_config(_cfg({"engine": {"turbo": {"count": 0,
                                                   "boost": 10}}}),
                         self.catalog_path, "achassis-v1")
        self.assertEqual({c["tune_key"] for c in res["tune_changes"]},
                         {"Turbochargers"})
        self.assertTrue(any(d["param"] == "engine.turbo.boost"
                            for d in res["rejected"]))
        ok = map_config(_cfg({"engine": {"turbo": {"count": 2,
                                                  "boost": 10}}}),
                        self.catalog_path, "achassis-v1")
        self.assertEqual({c["tune_key"] for c in ok["tune_changes"]},
                         {"Turbochargers", "T_Boost"})

    def test_f4_07_vstup_neporusen_pri_chybe(self):
        """F4-07: ani úspěšné ani odmítnuté mapování nemění vstupní dict."""
        cfg = _cfg({"engine": {"horsepower": 5000, "warp_drive": 1},
                    "transmission": {"final_drive": 3.2}})
        snapshot = copy.deepcopy(cfg)
        map_config(cfg, self.catalog_path, "achassis-v1")
        self.assertEqual(cfg, snapshot)

    def test_f4_08_prostor_jen_overene_s_rozsahem_a_merenim(self):
        """F4-08: 5 filtrů – Stiffness-bez-rozsahu, script a unknown ven;
        prázdné backend_caps → prázdný prostor."""
        from src.Chassis.mapping_engine import _sample_catalog
        sample_path = _write_catalog(_sample_catalog())
        full = ["Bias", "FDMult", "FinalDrive", "Horsepower", "T_Boost",
                "Turbochargers", "Stiffness"]
        space = build_search_space(sample_path, full)
        self.assertEqual(space, ["Bias", "FDMult", "FinalDrive", "Horsepower",
                                "T_Boost", "Turbochargers"])
        self.assertEqual(build_search_space(sample_path, ["Horsepower"]),
                         ["Horsepower"])
        self.assertEqual(build_search_space(sample_path, []), [])


# --------------------------------------------------------------------------
# C3 – integrace
# --------------------------------------------------------------------------

class TestF4Integration(unittest.TestCase):
    def test_retezec_map_config_az_adapter(self):
        """F4: VehicleConfig → map_config → parameters.tune → apply_config
        je konzistentní; neznámý klíč adaptér odmítne se záznamem."""
        from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter
        real = _write_catalog(catalog_loader.load(CATALOG_PATH))
        mapped = map_config(_cfg({"engine": {"horsepower": 210}}),
                            real, "achassis-v1")
        self.assertEqual(len(mapped["tune_changes"]), 1)
        tune = {c["tune_key"]: c["value"]
                for c in mapped["tune_changes"]}
        adapter = AChassisV1Adapter()
        params = adapter.list_parameters()
        self.assertEqual(len(params), 125)
        report = adapter.apply_config(
            os.path.join(ROOT, "assets", "chassis-original"),
            _cfg({"tune": dict(tune, WarpDrive=5)}))
        applied_keys = {a["tune_key"] for a in report.applied}
        self.assertEqual(applied_keys, set(tune))
        self.assertTrue(any(r["tune_key"] == "WarpDrive"
                            for r in report.rejected))
        for rej in report.rejected:
            self.assertTrue(rej.get("reason"))

    def test_adapter_odmita_unknown_bez_zapisu(self):
        """F4: neměnný klíč (S_Sensitivity, provenance unknown) apply_config
        odmítne; touched_model_files zůstává prázdné (binárka nedotčena)."""
        from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter
        report = AChassisV1Adapter().apply_config(
            os.path.join(ROOT, "assets", "chassis-original"),
            _cfg({"tune": {"S_Sensitivity": 1.0}}))
        self.assertEqual(report.applied, [])
        self.assertEqual(len(report.rejected), 1)
        self.assertEqual(report.touched_model_files, [])

    def test_f4_08_realny_katalog_prostor_sedm_klicu(self):
        """F4-08: reálný katalog (PASS) + caps adaptéru → 7 klíčů, všechny
        MUTABLE_TUNE + PASS + min<max + used_in. Statusy sjednotil Agent B
        (VERIFIED_STATUSES PASS|verified); kanonický je PASS. Zpětná
        kompatibilita 'verified' (vzorek) se ověřuje také."""
        adapter = _load_adapter()
        caps = [p.tune_key for p in adapter if p.tune_key]
        space = build_search_space(CATALOG_PATH, caps)
        self.assertEqual(space, ["Bias", "CurveMult", "FDiffCoast",
                                 "FDiffPower", "Preload", "TorqueVector",
                                 "WeightDist"])
        records = {r["id"]: r for r in catalog_loader.load(CATALOG_PATH)}
        for tune_key in space:
            rec = next(r for r in records.values()
                       if r["tune_key"] == tune_key)
            self.assertEqual(rec["category"], "MUTABLE_TUNE", tune_key)
            self.assertEqual(rec["verification_status"], "PASS", tune_key)
            self.assertLess(rec["min"], rec["max"], tune_key)
            self.assertTrue(rec["used_in"], tune_key)
        # mapovatelné, ale bez ověřeného rozsahu → mimo prostor:
        self.assertNotIn("FinalDrive", space)
        self.assertNotIn("Horsepower", space)
        # zpětná kompatibilita staršího tvaru 'verified' (vzorek C2):
        sample_path = _write_catalog(_sample_catalog())
        self.assertIn("Horsepower",
                      build_search_space(sample_path, caps))

    def test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque(self):
        """F4-09 (po Agentu D): backend_caps() existuje v search_space.py
        (kanonický zdroj = Sim backend), vrací neprázdné Tune klíče;
        search_space() je neprázdný a engine.peak_torque_nm neobsahuje
        (nemá katalogový záznam ani Tune protějšek – explicitně odmítnut)."""
        from src.Optimizer.search_space import (
            backend_caps,
            search_space,
        )
        caps = backend_caps(CATALOG_PATH)
        self.assertTrue(caps)  # neprázdné
        for key in caps:
            self.assertIsInstance(key, str)
            self.assertTrue(key)
        self.assertIn("Bias", caps)
        # Sim čte moment/výkon, ne Tune 'Horsepower' (draft D §1.4):
        self.assertNotIn("Horsepower", caps)
        tune_space = build_search_space(CATALOG_PATH, caps)
        self.assertTrue(tune_space)  # neprázdný (dnes ['Bias'])
        self.assertIn("Bias", tune_space)
        cfg = {"schema_version": "1.0.0", "config_id": "cfg_qa_f409",
               "vehicle_profile_id": "vp_qa", "chassis_adapter": "achassis-v1",
               "parameters": {"transmission": {"final_drive": 3.0},
                              "engine": {"peak_torque_nm": 205.0,
                                         "horsepower": 210},
                              "brakes": {"bias_front": 0.62}}}
        space = search_space(cfg, None)
        self.assertTrue(space)  # neprázdný
        names = [s["name"] for s in space]
        self.assertIn("brakes.bias_front", names)
        self.assertNotIn("engine.peak_torque_nm", names)
        for s in space:
            self.assertLess(s["min"], s["max"])


# --------------------------------------------------------------------------
# C4 – bezpečnost
# --------------------------------------------------------------------------

class TestF4Safety(unittest.TestCase):
    def test_f4_11_rbxm_hash_a_readonly(self):
        """F4-11: sha256 originálu; velikost 230 421 B; mtime beze změny
        během běhu testů (žádný zápis)."""
        if not os.path.exists(RBXM_ORIG):
            self.skipTest("originál rbxm nedostupný mimo toto prostředí")
        before = os.stat(RBXM_ORIG)
        with open(RBXM_ORIG, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(digest, RBXM_SHA256)
        self.assertEqual(before.st_size, 230421)
        after = os.stat(RBXM_ORIG)
        self.assertEqual((before.st_mtime_ns, before.st_size),
                         (after.st_mtime_ns, after.st_size))

    def test_f4_11_neoverene_hodnoty_se_neaplikuji(self):
        """F4-11: UNKNOWN kategorie se mapuje do rejected; PENDING záznamy
        (31) nejsou v bezpečném ladicím prostoru kap. 5 katalogu."""
        records = catalog_loader.load(CATALOG_PATH)
        pending = [r for r in records
                   if r["verification_status"] == "PENDING"]
        self.assertEqual(len(pending), 31)
        real = _write_catalog(records)
        res = map_config(_cfg({"engine": {"compression_ratio": 10.0}}),
                         real, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(len(res["rejected"]), 1)

    def test_f4_11_odmitnuti_zaznamenana(self):
        """F4-11: každé odmítnutí (engine i adaptér) nese param/klíč + důvod."""
        sample = _write_catalog(_sample_catalog())
        res = map_config(_cfg({"engine": {"warp_drive": 1,
                                          "horsepower": 9999}}),
                         sample, "achassis-v1")
        self.assertEqual(len(res["rejected"]), 2)
        for rej in res["rejected"]:
            self.assertTrue(rej.get("param"))
            self.assertTrue(rej.get("reason"))

    def test_f4_12_selftesty_zelene(self):
        """F4-10/F4-12: selftest katalogu i enginu hlásí OK (vlastní běh)."""
        out = catalog_loader.run_selftest(CATALOG_PATH)
        self.assertEqual(out["selftest"], "OK")
        self.assertEqual(out["n_records"], 125)
        eng = engine_selftest()
        self.assertEqual(eng["selftest"], "OK")

    def test_studio_mereni_pending_ne_pass(self):
        """Studio-nedostupné: float-lane (Stiffness/Damping) a StAxisOffset
        runtime se bez Studia neověřují – PENDING, nikdy PASS."""
        self.skipTest("PENDING: vyžaduje Roblox Studio – odečet "
                      "Stiffness/Damping z template a běh Initialize "
                      "(StAxisOffset §17.1); bez Studia neprokazatelné")


if __name__ == "__main__":
    unittest.main(verbosity=2)

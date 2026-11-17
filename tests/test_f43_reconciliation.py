# AutoEngineerAI – QA FÁZE 4.3 vlna 2 (Agent F): rekonciliace s live Tune.
#
# Vlastník: Agent F. Vlastněný soubor: tento. READ-ONLY mimo něj.
# Česky; identifikátory anglicky; Python 3 stdlib; žádné git operace,
# rbxm se nesahá. Ground truth: vehicle-data/analyzed/live-tune-keys.txt
# (167 živých klíčů) + src/Chassis/catalog/parameters.json (138 záznamů).
#
# Smysl: důkaz proti tichému no-op – každé odmítnutí musí nést důvod
# a každá kladná cesta musí projít až do applied (prázdný applied při
# očekávané změně = FAIL, ne PASS).
"""F4.3 rekonciliace: katalog/adaptér/VehicleManager proti živým klíčům.

Spouštění z kořene:  python3 -m unittest tests.test_f43_reconciliation -v
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter  # noqa: E402
from src.Chassis.catalog import loader as catalog_loader  # noqa: E402
from src.Chassis.mapping_engine import map_config  # noqa: E402

CATALOG_PATH = os.path.join(
    ROOT, "src", "Chassis", "catalog", "parameters.json")
LIVE_KEYS_PATH = os.path.join(
    ROOT, "vehicle-data", "analyzed", "live-tune-keys.txt")
VEHICLE_MANAGER_PATH = os.path.join(
    ROOT, "testgame", "src", "ServerScriptService",
    "AutoEngineer", "VehicleManager.lua")


def _cfg(parameters: dict) -> dict:
    return {"schema_version": "1.0.0", "config_id": "cfg_f43",
            "vehicle_profile_id": "vp_f43", "chassis_adapter": "achassis-v1",
            "parameters": parameters}


def _live_keys() -> list[str]:
    with open(LIVE_KEYS_PATH, encoding="utf-8") as fh:
        return [ln.strip().split("=")[0] for ln in fh
                if ln.strip() and not ln.startswith("#")]


def _catalog_records() -> list[dict]:
    return catalog_loader.load(CATALOG_PATH)


class TestF43Reconciliation(unittest.TestCase):
    def test_katalog_pocty_138_82_14_2_3_37(self):
        """F4.3: katalog 138 záznamů, kategorie 82/14/2/3/37."""
        from collections import Counter
        records = _catalog_records()
        counts = Counter(r["category"] for r in records)
        self.assertEqual(len(records), 138)
        self.assertEqual(counts["MUTABLE_TUNE"], 82)
        self.assertEqual(counts["SCRIPT_CONTROLLED"], 14)
        self.assertEqual(counts["STRUCTURE_CONTROLLED"], 2)
        self.assertEqual(counts["READ_ONLY"], 3)
        self.assertEqual(counts["UNKNOWN"], 37)
        print("RAW F4.3 katalog: n=138 MUTABLE=82 UNKNOWN=37")

    def test_diff_katalog_vs_live_bez_fantomu(self):
        """F4.3: žádný katalogový tune_key není mimo live klíče (0 fantomů).

        Čte OBA soubory: parameters.json i live-tune-keys.txt.
        """
        live = set(_live_keys())
        self.assertEqual(len(live), 167, "live klíčů má být 167")
        tune_keys = [r["tune_key"] for r in _catalog_records()
                     if r.get("tune_key")]
        fantomy = sorted(set(tune_keys) - live)
        self.assertEqual(fantomy, [], "fantomové klíče: %r" % (fantomy,))
        self.assertIn("BrakeBias", live)
        self.assertIn("BrakeBias", tune_keys)
        self.assertNotIn("Bias", tune_keys)
        print("RAW F4.3 diff: katalog_tune=%d live=167 FANTOMU=0"
              % len(set(tune_keys)))

    def test_map_config_odmitne_neexistujici_klic_s_duvodem(self):
        """F4.3: map_config neexistující klíč odmítne s důvodem (ne tiše)."""
        res = map_config(_cfg({"engine": {"warp_drive": 1}}),
                         CATALOG_PATH, "achassis-v1")
        # Anti-no-op: odmítnutí musí být VIDITELNÉ v rejected, ne jen
        # prázdné tune_changes.
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(len(res["rejected"]), 1)
        self.assertEqual(res["rejected"][0]["param"], "engine.warp_drive")
        self.assertTrue(res["rejected"][0]["reason"])
        print("RAW F4.3 map_config rejected: %s"
              % res["rejected"][0]["reason"])

    def test_adapter_odmitne_fantom_bias_s_duvodem(self):
        """F4.3: apply_config fantom 'Bias' odmítne s důvodem, nic nezapíše."""
        report = AChassisV1Adapter().apply_config(
            os.path.join(ROOT, "assets", "chassis-original"),
            _cfg({"tune": {"Bias": 0.6}}))
        # Anti-no-op: applied MUSÍ být prázdné a rejected MUSÍ nést důvod.
        self.assertEqual(report.applied, [])
        self.assertEqual(len(report.rejected), 1)
        self.assertEqual(report.rejected[0]["tune_key"], "Bias")
        self.assertTrue(report.rejected[0].get("reason"))
        self.assertEqual(report.touched_model_files, [])
        print("RAW F4.3 adapter fantom rejected: %s"
              % report.rejected[0]["reason"])

    def test_adapter_brakebias_projede(self):
        """F4.3: živý klíč BrakeBias projde až do applied (kladná cesta)."""
        report = AChassisV1Adapter().apply_config(
            os.path.join(ROOT, "assets", "chassis-original"),
            _cfg({"tune": {"BrakeBias": 0.62}}))
        self.assertEqual(report.rejected, [])
        applied = {a["tune_key"]: a for a in report.applied}
        self.assertIn("BrakeBias", applied)
        self.assertEqual(applied["BrakeBias"]["to"], 0.62)
        print("RAW F4.3 adapter BrakeBias applied: %r" % (report.applied,))

    def test_vehiclemanager_mutable_set_82_live_klicu(self):
        """F4.3: VehicleManager MUTABLE set = 82 živých klíčů, bez fantomů."""
        with open(VEHICLE_MANAGER_PATH, encoding="utf-8") as fh:
            src = fh.read()
        block = re.search(r"MUTABLE_TUNE_SET = \{(.*?)\n\}",
                          src, re.S).group(1)
        keys = re.findall(r"^\s*(\w+)\s*=\s*true", block, re.M)
        self.assertEqual(len(keys), 82)
        self.assertIn("BrakeBias", keys)
        self.assertIn("FDiffPreload", keys)
        self.assertIn("RDiffPreload", keys)
        for fantom in ("Bias", "Damping", "Stiffness", "Preload",
                       "SlipThres", "LockThres", "SusLength", "PreCompress",
                       "ExtensionLim", "CompressLim", "SusAngle",
                       "AnchorOffset"):
            self.assertNotIn(fantom, keys, "fantom v MUTABLE setu")
        live = set(_live_keys())
        self.assertEqual(sorted(set(keys) - live), [])
        deny = re.search(r"DENY_REASONS = \{(.*?)\n\}", src, re.S).group(1)
        for known in ("Bias", "StAxisOffset", "CompressionRatio",
                      "FWLgcyDensity"):
            self.assertIn(known, deny, "chybí důvod pro %s" % known)
        print("RAW F4.3 VehicleManager: MUTABLE=82, fantomy DENIED s důvodem")

    def test_vehiclemanager_read_write_guard(self):
        """F4.3: ReadTune/WriteTune stojí za IsMutable branou s DenyReason.

        Lua runtime tu neběží – ověřuje se zdroj: brána musí existovat
        a BrakeBias jí prochází, zatímco UNKNOWN/read-only ne.
        """
        with open(VEHICLE_MANAGER_PATH, encoding="utf-8") as fh:
            src = fh.read()
        # Obě funkce odmítají neměnný klíč s důvodem (ne tichý no-op).
        for fn in ("ReadTune", "WriteTune"):
            body = re.search(
                r"function VehicleManager\.%s\(.*?\)\n(.*?)\nend" % fn,
                src, re.S).group(1)
            self.assertIn("IsMutable(key)", body, fn)
            self.assertIn("DenyReason(key)", body, fn)
        # Brána: jen MUTABLE_TUNE_SET prochází; DenyReason pro ostatní
        # vždy vrací text (žádná cesta nevrací nil/mlčení).
        deny_fn = re.search(
            r"function VehicleManager\.DenyReason\(key\)\n(.*?)\nend",
            src, re.S).group(1)
        self.assertIn("MUTABLE_TUNE_SET[key]", deny_fn)
        self.assertIn('return nil', deny_fn)  # jen pro mutable klíče
        self.assertIn("UNKNOWN: klic neni v MUTABLE_TUNE katalogu",
                      deny_fn)  # fallback důvod pro cokoli jiného
        # ReadTune(BrakeBias): BrakeBias je v MUTABLE setu → brána pustí.
        block = re.search(r"MUTABLE_TUNE_SET = \{(.*?)\n\}",
                          src, re.S).group(1)
        keys = set(re.findall(r"^\s*(\w+)\s*=\s*true", block, re.M))
        self.assertIn("BrakeBias", keys)
        # UNKNOWN (StAxisOffset, CompressionRatio) a fantom Bias branou
        # neprojdou → Read/Write je odmítne s důvodem.
        for k in ("StAxisOffset", "CompressionRatio", "Bias"):
            self.assertNotIn(k, keys)


if __name__ == "__main__":
    unittest.main(verbosity=2)

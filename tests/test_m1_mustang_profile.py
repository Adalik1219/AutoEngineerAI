"""Akceptační testy M1-T01…M1-T07 — Mustang GT 2024 EU manuál standard.

Vazba: docs/IMPLEMENTATION_ROADMAP.md (M1), docs/VEHICLE-SPECIFICATIONS.md,
docs/ACCEPTANCE_CRITERIA.md (M1-T01…M1-T07), vehicle-data/references/.
Pravidla: stdlib only (unittest), česky komentáře, identifikátory anglicky.
"""

import copy
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Reference import loader
from src.Reference import validate as vmod

MUSTANG_FILENAME = "ford-mustang-gt-2024-eu-manual-standard.json"

#: Známky Performance Packu — nesmí se objevit ve standardním profilu (M1.7).
PACK_MARKERS = ("performance pack", "brembo")


def check_variant_compatibility(profile: dict) -> None:
    """Kontrola kompatibility variant M1.6/M1.7: EU≠US, GT≠Pack.

    Vyhazuje ValueError při záměně trhu (US místo EU) nebo při smíchání
    výbavy Performance Packu do standardního GT.
    """
    identity = profile.get("identity", {})
    if identity.get("market") != "EU":
        raise ValueError(
            "záměna varianty EU/US: market=%r (očekáváno 'EU')"
            % (identity.get("market"),))
    vehicle_id = profile.get("vehicle_id", "")
    if "-eu-" not in vehicle_id or not vehicle_id.endswith("-standard"):
        raise ValueError(
            "vehicle_id %r nepatří variantě EU standard" % (vehicle_id,))
    trim = str(identity.get("trim", "")).lower()
    if "performance pack" in trim and "bez performance packu" not in trim:
        raise ValueError("trim hlásí Performance Pack: %r" % (identity.get("trim"),))
    text = "".join([
        str((profile.get("brakes", {}).get("front_type", ""))),
        str((profile.get("brakes", {}).get("rear_type", ""))),
        str((profile.get("drivetrain", {}).get("differential_rear", ""))),
    ]).lower()
    for marker in PACK_MARKERS:
        if marker in text:
            raise ValueError(
                "smíchání GT/Pack: komponenta Packu %r ve standardním GT" % marker)


class MustangProfileTest(unittest.TestCase):
    """M1-T01…M1-T07."""

    @classmethod
    def setUpClass(cls):
        cls.schema = loader.load_schema()
        cls.profile = loader.load_profile(
            loader.references_dir() / MUSTANG_FILENAME)

    def _errors(self, profile):
        errors, _ = vmod.validate_profile(profile, self.schema)
        return errors

    def test_m1_t01_mustang_loads_valid(self):
        """M1-T01: Mustang se načte jako validní verzovaný profil."""
        self.assertEqual(
            self.profile["vehicle_id"],
            "ford-mustang-gt-2024-eu-manual-standard")
        self.assertTrue(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$",
                                 self.profile["vehicle_id"]))
        self.assertEqual(self.profile["schema_version"], "1.0.0")
        for key in ("schema_version", "vehicle_id", "identity", "meta"):
            self.assertIn(key, self.profile)
        errors = self._errors(self.profile)
        self.assertEqual(errors, [])
        check_variant_compatibility(self.profile)

    def test_m1_t02_missing_required_field_rejected(self):
        """M1-T02: chybějící povinné pole → odmítnuto."""
        mutant = copy.deepcopy(self.profile)
        del mutant["vehicle_id"]
        self.assertTrue(self._errors(mutant))
        mutant2 = copy.deepcopy(self.profile)
        del mutant2["identity"]
        self.assertTrue(self._errors(mutant2))

    def test_m1_t03_invalid_transmission_rejected(self):
        """M1-T03: neplatná převodovka → odmítnuto."""
        mutant = copy.deepcopy(self.profile)
        mutant["transmission"]["gears_count"] = 0  # minimum dle schématu je 1
        self.assertTrue(self._errors(mutant))

    def test_m1_t04_eu_us_swap_rejected(self):
        """M1-T04: záměna EU/US → odmítnuto."""
        mutant = copy.deepcopy(self.profile)
        mutant["identity"]["market"] = "US"
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant)
        mutant2 = copy.deepcopy(self.profile)
        mutant2["vehicle_id"] = "ford-mustang-gt-2024-us-manual-standard"
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant2)

    def test_m1_t05_unknowns_stay_unknown(self):
        """M1-T05: neznámá křivka a neznámé převodové poměry zůstávají UNKNOWN."""
        tc = self.profile["torque_curve"]
        self.assertEqual(tc["points"], [])
        self.assertEqual(tc["interpolation"], "none")
        curve = tc["curve_source"]
        self.assertIsNone(curve.get("value", None))
        self.assertTrue(str(curve.get("notes") or "").startswith("CHYBÍ:"))
        for entry in self.profile["transmission"]["gear_ratios"]:
            self.assertIsNone(entry["ratio"]["value"])
            self.assertTrue(
                str(entry["ratio"].get("notes") or "").startswith("CHYBÍ:"))
        self.assertIsNone(self.profile["transmission"]["final_drive"]["value"])
        # M1.9 výjimka: prázdná křivka UNKNOWN je validní (žádné chyby).
        self.assertEqual(self._errors(self.profile), [])

    def test_m1_t06_verified_without_source_rejected(self):
        """M1-T06: VERIFIED (factory) bez zdroje → odmítnuto."""
        mutant = copy.deepcopy(self.profile)
        mutant["engine"]["max_power"] = {
            "value": 328, "unit": "kW", "source": "",
            "source_type": "factory", "confidence": 1.0,
        }
        errors = self._errors(mutant)
        self.assertTrue(any("bez zdroje" in e for e in errors), errors)

    def test_m1_t07_gt_pack_mix_rejected(self):
        """M1-T07: smíchání GT/Pack → odmítnuto."""
        mutant = copy.deepcopy(self.profile)
        mutant["brakes"]["front_type"] = "Brembo 6-piston (Performance Pack)"
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant)
        # Originál žádné znaky Packu nenese.
        check_variant_compatibility(self.profile)
        claimed = " ".join([
            str(self.profile["identity"].get("trim", "")),
            str(self.profile.get("brakes", {}).get("front_type", "")),
            str(self.profile.get("brakes", {}).get("rear_type", "")),
            str(self.profile.get("drivetrain", {}).get("differential_rear", "")),
        ]).lower()
        self.assertNotIn("brembo", claimed)
        self.assertNotIn("performance pack", claimed.replace(
            "bez performance packu", ""))


    def test_m1_t08_m19_bypass_single_point_rejected(self):
        """M1.9: jeden vymyšlený bod křivky → odmítnuto (minItems 2)."""
        mutant = copy.deepcopy(self.profile)
        mutant["torque_curve"]["points"] = [
            {"rpm": 3000, "torque_nm": 400, "point_type": "estimated"}]
        errors = self._errors(mutant)
        self.assertTrue(any("minItems" in e for e in errors), errors)

    def test_m1_t09_m19_bypass_missing_point_type_rejected(self):
        """M1.9: body bez point_type → odmítnuto (schéma i point_type)."""
        mutant = copy.deepcopy(self.profile)
        mutant["torque_curve"]["points"] = [
            {"rpm": 3000, "torque_nm": 400},
            {"rpm": 5100, "torque_nm": 540}]
        mutant["torque_curve"]["interpolation"] = "linear"
        errors = self._errors(mutant)
        self.assertTrue(any("point_type" in e for e in errors), errors)

    def test_m1_t10_m19_bypass_estimate_without_odhad_rejected(self):
        """M1.9: neprázdná křivka estimate bez 'ODHAD:' → odmítnuto."""
        mutant = copy.deepcopy(self.profile)
        mutant["torque_curve"]["points"] = [
            {"rpm": 3000, "torque_nm": 400, "point_type": "estimated"},
            {"rpm": 5100, "torque_nm": 540, "point_type": "estimated"}]
        mutant["torque_curve"]["interpolation"] = "linear"
        mutant["torque_curve"]["curve_source"] = {
            "source": "x", "source_type": "estimate",
            "confidence": 0.4, "notes": "bez prefixu"}
        errors = self._errors(mutant)
        self.assertTrue(any("ODHAD" in e for e in errors), errors)

    def test_m1_t11_m19_bypass_empty_curve_wrong_shape_rejected(self):
        """M1.9: prázdná křivka s interpolation != none → výjimka neplatí."""
        mutant = copy.deepcopy(self.profile)
        mutant["torque_curve"]["interpolation"] = "linear"
        errors = self._errors(mutant)
        self.assertTrue(any("minItems" in e for e in errors), errors)
        mutant2 = copy.deepcopy(self.profile)
        mutant2["torque_curve"]["curve_source"]["confidence"] = 0.9
        errors2 = self._errors(mutant2)
        self.assertTrue(any("minItems" in e for e in errors2), errors2)

    def test_m1_t12_m15_promoted_fields_are_factory_verified(self):
        """M1.5: POTVRZENO hodnoty jsou factory, confidence >= 0.8, zdroj s URL."""
        paths = [
            ("engine", "displacement"), ("engine", "bore"),
            ("engine", "stroke"), ("engine", "max_power"),
            ("engine", "max_power_rpm"), ("engine", "max_torque"),
            ("engine", "max_torque_rpm"), ("dimensions", "wheelbase"),
            ("dimensions", "track_front"), ("dimensions", "track_rear"),
            ("dimensions", "length"), ("dimensions", "width_excl_mirrors"),
            ("dimensions", "width_incl_mirrors"), ("dimensions", "height"),
        ]
        for section, key in paths:
            with self.subTest(field="%s.%s" % (section, key)):
                env = self.profile[section][key]
                self.assertEqual(env["source_type"], "factory")
                self.assertGreaterEqual(env["confidence"], 0.8)
                self.assertIn("http", env["source"])
                self.assertIsNotNone(env["value"])
        for axle in ("tire_front", "tire_rear"):
            for key in ("designation", "width_mm", "aspect_ratio_pct",
                        "rim_in"):
                with self.subTest(field="%s.%s" % (axle, key)):
                    env = self.profile["wheels_tires"][axle][key]
                    self.assertEqual(env["source_type"], "factory")
                    self.assertGreaterEqual(env["confidence"], 0.8)
                    self.assertIn("http", env["source"])
        # Hmotnost zůstává ESTIMATED (Ford sám uvádí "Est."), ale s dohledatelným zdrojem.
        curb = self.profile["mass"]["curb_weight"]
        self.assertEqual(curb["source_type"], "estimate")
        self.assertIn("1808", curb["source"])

    def test_m1_t13_m15_unknowns_stay_unknown_with_candidates(self):
        """M1.5: křivka/rozložení/bias/Cd/stálý převod zůstávají UNKNOWN + kandidáti v notes."""
        null_paths = [
            ("aero", "drag_coefficient_cd"), ("aero", "frontal_area"),
            ("mass", "weight_distribution_front_pct"),
            ("mass", "cog_height"),
            ("brakes", "brake_bias_front_pct"),
            ("transmission", "final_drive"),
        ]
        for section, key in null_paths:
            with self.subTest(field="%s.%s" % (section, key)):
                env = self.profile[section][key]
                self.assertIsNone(env["value"])
                self.assertTrue(
                    str(env.get("notes") or "").startswith("CHYBÍ:"),
                    env.get("notes"))
        self.assertEqual(self.profile["torque_curve"]["points"], [])
        for entry in self.profile["transmission"]["gear_ratios"]:
            self.assertIsNone(entry["ratio"]["value"])
            self.assertIn("kandidat", entry["ratio"]["notes"].lower())
        self.assertIn("3.15", self.profile["transmission"]["final_drive"]["notes"])
        self.assertIsNone(self.profile["performance"]["accel_0_100"]["value"])
        self.assertIsNone(self.profile["performance"]["vmax"]["value"])


if __name__ == "__main__":
    unittest.main()

"""Akceptační testy M1-T01…M1-T07 + M1.5 promoce — Mustang GT 2024 EU manuál.

Vazba: docs/IMPLEMENTATION_ROADMAP.md (M1), docs/VEHICLE-SPECIFICATIONS.md,
docs/ACCEPTANCE_CRITERIA.md (M1-T01…M1-T07), vehicle-data/references/.
Pravidla: stdlib only (unittest), česky komentáře, identifikátory anglicky.

Varianta (rozhodnutí uživatele 2026-11-19): EUROPEAN FACTORY STANDARD
SPECIFICATION — Performance Pack je standardem EU GT, Brembo/LSD patří
do EU profilu. vehicle_id je stabilní a nemění se.
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

# Testy musi byt repo-relative: loader default (src/Reference/loader.py)
# ukazuje na lokalni cestu vyvojare, proto testy sjednoti koren repa
# pres env promennou (src/ se nesmi menit — patri jinemu agentovi).
os.environ["AUTOENGINEERAI_ROOT"] = ROOT

from src.Reference import loader
from src.Reference import validate as vmod

MUSTANG_FILENAME = "ford-mustang-gt-2024-eu-manual-standard.json"
MUSTANG_VEHICLE_ID = "ford-mustang-gt-2024-eu-manual-standard"

#: US znaky — nesmí se objevit v komponentních řetězcích EU profilu
#: (nikoli v notes, kde smí být zmíněny v negaci: "není Torsen …").
US_MARKERS = ("tremec", "tr-3160", "torsen", "dark horse", "453 ps")

#: Starý název varianty — po přejmenování odmítnut.
OLD_NAME_MARKERS = ("bez performance packu", "without performance pack")


def _component_text(profile: dict) -> str:
    """Texty určující variantu (bez notes — ty smí US hodnoty negovat)."""
    parts = [
        str(profile.get("identity", {}).get("trim", "")),
        str((profile.get("transmission") or {}).get("type", "")),
        str((profile.get("brakes") or {}).get("front_type", "")),
        str((profile.get("brakes") or {}).get("rear_type", "")),
    ]
    diff = (profile.get("drivetrain") or {}).get("differential_rear")
    if isinstance(diff, dict):
        parts.append(str(diff.get("value", "")))
    elif diff is not None:
        parts.append(str(diff))
    return "\n".join(parts)


def check_variant_compatibility(profile: dict) -> None:
    """Kontrola kompatibility variant M1.6/M1.7: EU factory standard.

    EU≠US (žádné US komponenty do EU profilu); starý název
    "bez Performance Packu" odmítnut; Brembo/LSD jsou EU standardem
    (povoleny). Vyhazuje ValueError při porušení.
    """
    identity = profile.get("identity", {})
    if identity.get("market") != "EU":
        raise ValueError(
            "záměna varianty EU/US: market=%r (očekáváno 'EU')"
            % (identity.get("market"),))
    if profile.get("vehicle_id") != MUSTANG_VEHICLE_ID:
        raise ValueError(
            "vehicle_id %r nepatří variantě EU factory standard"
            % (profile.get("vehicle_id"),))
    trim = str(identity.get("trim", ""))
    if "european factory standard" not in trim.lower():
        raise ValueError(
            "trim nehlásí EUROPEAN FACTORY STANDARD SPECIFICATION: %r"
            % (identity.get("trim"),))
    if any(m in trim.lower() for m in OLD_NAME_MARKERS):
        raise ValueError("starý název varianty: %r" % (identity.get("trim"),))
    text = _component_text(profile).lower()
    for marker in US_MARKERS:
        if marker in text:
            raise ValueError(
                "US komponenta %r nepatří do EU profilu" % marker)


def resolve_final_drive_value(profile: dict) -> float:
    """GUARD: stálý převod smí do M3/M4 jen jako definitivní hodnota.

    UNKNOWN (value None) → ValueError (použití musí skončit chybou,
    nikdy tichým dosazením kandidáta 3.15:1 / 3.55:1).
    """
    node = (profile.get("transmission") or {}).get("final_drive") or {}
    value = node.get("value")
    if value is None:
        raise ValueError(
            "final_drive je UNKNOWN (kandidáti 3.15:1 / 3.55:1 bez přiřazení) "
            "— nelze použít jako definitivní hodnotu pro výpočty M3/M4")
    return float(value)


class MustangProfileTest(unittest.TestCase):
    """M1-T01…M1-T07 + promoce M1.5 (EU factory standard)."""

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
        self.assertEqual(self.profile["vehicle_id"], MUSTANG_VEHICLE_ID)
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
        """M1-T05: neznámá křivka, bias a aero zůstávají UNKNOWN."""
        tc = self.profile["torque_curve"]
        self.assertEqual(tc["points"], [])
        self.assertEqual(tc["interpolation"], "none")
        curve = tc["curve_source"]
        self.assertIsNone(curve.get("value", None))
        self.assertTrue(str(curve.get("notes") or "").startswith("CHYBÍ:"))
        for section, key in (
                ("brakes", "brake_bias_front_pct"),
                ("aero", "drag_coefficient_cd"),
                ("aero", "frontal_area"),
                ("mass", "weight_distribution_front_pct"),
                ("mass", "cog_height")):
            with self.subTest(field="%s.%s" % (section, key)):
                env = self.profile[section][key]
                self.assertIsNone(env["value"])
                self.assertTrue(
                    str(env.get("notes") or "").startswith("CHYBÍ:"),
                    env.get("notes"))
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

    def test_m1_t07_eu_factory_standard_brembo_allowed(self):
        """M1-T07: Brembo/LSD jsou EU standardem (povoleny), starý název ne."""
        check_variant_compatibility(self.profile)
        self.assertIn("brembo",
                      str(self.profile["brakes"].get("front_type", "")).lower())
        # Starý název varianty je po přejmenování odmítnut.
        mutant = copy.deepcopy(self.profile)
        mutant["identity"]["trim"] = (
            "GT 5.0 Ti-VCT V8, 6MT, standard (bez Performance Packu)")
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant)

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

    def test_m1_t13_m15_final_drive_unknown_with_candidates(self):
        """M1.5: stálý převod UNKNOWN + oba kandidáti v notes, žádný výběr."""
        env = self.profile["transmission"]["final_drive"]
        self.assertIsNone(env["value"])
        self.assertTrue(
            str(env.get("notes") or "").startswith("CHYBÍ:"),
            env.get("notes"))
        self.assertIn("3.15", env["notes"])
        self.assertIn("3.55", env["notes"])

    def test_m1_t14_gear_ratios_verified(self):
        """Povýšení M1.5: 6 poměrů Getrag MT-82 VERIFIED (factory, URL)."""
        expected = {1: 3.237, 2: 2.104, 3: 1.422,
                    4: 1.000, 5: 0.814, 6: 0.622}
        gears = self.profile["transmission"]["gear_ratios"]
        self.assertEqual(len(gears), 6)
        for entry in gears:
            with self.subTest(gear=entry["gear"]):
                ratio = entry["ratio"]
                self.assertAlmostEqual(ratio["value"],
                                       expected[entry["gear"]], places=3)
                self.assertEqual(ratio["unit"], ":1")
                self.assertEqual(ratio["source_type"], "factory")
                self.assertGreaterEqual(ratio["confidence"], 0.8)
                self.assertIn("http", ratio["source"])
                self.assertIn("media.ford.com", ratio["source"])

    def test_m1_t15_performance_verified(self):
        """Povýšení M1.5: 0-100 5.3 s + V-max 250 km/h VERIFIED (EU PDF)."""
        accel = self.profile["performance"]["accel_0_100"]
        self.assertAlmostEqual(accel["value"], 5.3, places=1)
        self.assertEqual(accel["unit"], "s")
        self.assertEqual(accel["source_type"], "factory")
        self.assertGreaterEqual(accel["confidence"], 0.8)
        self.assertIn("http", accel["source"])
        vmax = self.profile["performance"]["vmax"]
        self.assertEqual(vmax["value"], 250)
        self.assertEqual(vmax["unit"], "km/h")
        self.assertEqual(vmax["source_type"], "factory")
        self.assertGreaterEqual(vmax["confidence"], 0.8)
        self.assertIn("http", vmax["source"])

    def test_m1_t16_brakes_verified_brembo_eu_standard(self):
        """Povýšení M1.5: brzdy 390x36 / 355x28 + Brembo VERIFIED."""
        front = self.profile["brakes"]["front_disc_diameter"]
        self.assertEqual(front["value"], 390)
        self.assertEqual(front["source_type"], "factory")
        self.assertGreaterEqual(front["confidence"], 0.8)
        self.assertIn("http", front["source"])
        rear = self.profile["brakes"]["rear_disc_diameter"]
        self.assertEqual(rear["value"], 355)
        self.assertEqual(rear["source_type"], "factory")
        self.assertGreaterEqual(rear["confidence"], 0.8)
        self.assertIn("http", rear["source"])
        self.assertIn("brembo",
                      str(self.profile["brakes"].get("front_type", "")).lower())
        self.assertIn("six-piston",
                      str(self.profile["brakes"].get("front_type", "")).lower())
        # Bias zůstává UNKNOWN.
        bias = self.profile["brakes"]["brake_bias_front_pct"]
        self.assertIsNone(bias["value"])
        self.assertTrue(str(bias.get("notes") or "").startswith("CHYBÍ:"))

    def test_m1_t17_final_drive_guard_rejects_use_as_definitive(self):
        """GUARD: UNKNOWN final_drive nelze použít jako definitivní hodnotu."""
        with self.assertRaises(ValueError):
            resolve_final_drive_value(self.profile)
        # Po budoucím ověření guard propustí číselnou hodnotu.
        mutant = copy.deepcopy(self.profile)
        mutant["transmission"]["final_drive"]["value"] = 3.55
        self.assertAlmostEqual(resolve_final_drive_value(mutant), 3.55)

    def test_m1_t18_us_parts_rejected(self):
        """US hodnoty (Torsen, Tremec TR-3160, Dark Horse 453 PS) → odmítnuty."""
        mutant = copy.deepcopy(self.profile)
        mutant["transmission"]["type"] = "6-speed manual Tremec TR-3160 (US)"
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant)
        mutant2 = copy.deepcopy(self.profile)
        mutant2["drivetrain"]["differential_rear"] = {
            "value": "Torsen limited-slip differential", "unit": "type",
            "source": "US brožura", "source_type": "factory",
            "confidence": 0.9, "notes": None}
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant2)
        mutant3 = copy.deepcopy(self.profile)
        mutant3["identity"]["trim"] = "Dark Horse, 453 PS, 6MT (US)"
        with self.assertRaises(ValueError):
            check_variant_compatibility(mutant3)
        # Notes smí US hodnoty zmiňovat v negaci ("není Torsen") — originál projde.
        check_variant_compatibility(self.profile)

    def test_m1_t19_wheels_verified(self):
        """Kontrola M1.5: kola 19x9.0 / 19x9.5 VERIFIED (factory, URL)."""
        front = self.profile["wheels_tires"]["wheel_front"]
        self.assertIn("9.0", str(front["value"]))
        self.assertEqual(front["source_type"], "factory")
        self.assertGreaterEqual(front["confidence"], 0.8)
        self.assertIn("http", front["source"])
        rear = self.profile["wheels_tires"]["wheel_rear"]
        self.assertIn("9.5", str(rear["value"]))
        self.assertEqual(rear["source_type"], "factory")
        self.assertGreaterEqual(rear["confidence"], 0.8)
        self.assertIn("http", rear["source"])

    def test_m1_t20_variant_renamed_id_stable(self):
        """Přejmenování: trim nese EU factory standard, vehicle_id beze změny."""
        self.assertEqual(self.profile["vehicle_id"], MUSTANG_VEHICLE_ID)
        trim = str(self.profile["identity"].get("trim", ""))
        self.assertIn("european factory standard", trim.lower())
        self.assertNotIn("bez performance packu", trim.lower())
        self.assertIn("european factory standard",
                      str(self.profile["transmission"].get("type", "")).lower())


class ContractValidatorConsistencyTest(unittest.TestCase):
    """Konzistence tools/validate_contracts.py s M1.9 výjimkou (Fáze B).

    tools/validate_contracts.py kontroluje vehicle-data proti _schema.json
    (minItems 2 na torque_curve.points); bez M1.9 výjimky by legitimní
    prázdnou křivku UNKNOWN (CHYBÍ:, interpolation none) falešně zamítal,
    zatímco src/Reference/validate.py ji přijímá.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util
        tool_path = os.path.join(ROOT, "tools", "validate_contracts.py")
        spec = importlib.util.spec_from_file_location(
            "validate_contracts", tool_path)
        cls.vc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.vc)
        schema_path = os.path.join(
            ROOT, "vehicle-data", "references", "_schema.json")
        import json
        with open(schema_path, encoding="utf-8") as fh:
            cls.schema = json.load(fh)

    def _tool_errors(self, profile):
        errs = self.vc.validate_against_schema(profile, self.schema)
        if self.vc._is_m19_empty_torque_curve(profile):
            errs = [e for e in errs
                    if e != "$/torque_curve/points: pole je příliš krátké (0 < 2)"]
        return errs

    def test_m1_t21_contract_validator_accepts_empty_unknown_curve(self):
        """M1.9: prázdná křivka UNKNOWN projde i přes tools validátor."""
        profile = loader.load_profile(
            loader.references_dir() / MUSTANG_FILENAME)
        self.assertEqual(self._tool_errors(profile), [])
        checks, failures, _ = self.vc.check_vehicle_data()
        self.assertGreater(checks, 0)
        self.assertEqual(failures, 0)

    def test_m1_t22_contract_validator_rejects_single_point_bypass(self):
        """M1.9: jeden vymyšlený bod zamítne i tools validátor (minItems 2)."""
        mutant = copy.deepcopy(loader.load_profile(
            loader.references_dir() / MUSTANG_FILENAME))
        mutant["torque_curve"]["points"] = [
            {"rpm": 3000, "torque_nm": 400, "point_type": "estimated"}]
        errs = self.vc.validate_against_schema(mutant, self.schema)
        self.assertTrue(any("příliš krátké" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
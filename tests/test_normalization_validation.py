"""Negativní testy validátoru normalizace E1–E6 (Agent E).

Každý test zmutuje kopii normalized_ids.json v paměti a prokáže, že
tools/validate_normalization.py mutaci odmítne (FAIL, exit 1), resp.
u nedoloženého seznamu 60 vrátí PENDING (exit 2), nikdy PASS.

Jen stdlib, unittest. Žádné zápisy do repozitáře.
"""
import copy
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load_validator():
    path = os.path.join(ROOT, "tools", "validate_normalization.py")
    spec = importlib.util.spec_from_file_location(
        "validate_normalization", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vn = _load_validator()


def _code(fails, pendings):
    if fails:
        return 1
    if pendings:
        return 2
    return 0


class TestValidatorNegativni(unittest.TestCase):
    """51 negativních případů E6 — každý musí prokázat FAIL/PENDING."""

    @classmethod
    def setUpClass(cls):
        jpath = os.path.join(ROOT, "reports", "NIGHT-WORK",
                             "normalized_ids.json")
        cls.doc = vn.load_doc(jpath)
        meta = cls.doc["meta"]
        cls.f_rel = meta["zdroj_60_a_78"]["soubor"]
        fpath = os.path.join(ROOT, *cls.f_rel.split("/"))
        with open(fpath, "rb") as f:
            cls.f_blob = vn.git_blob_sha(f.read())
        cls.rows = vn.parse_f_rows(fpath)
        kpath = os.path.join(ROOT, "src", "Chassis", "catalog",
                             "parameters.json")
        with open(kpath, encoding="utf-8") as f:
            kdoc = json.load(f)
        cls.catalog_ids = {e["id"] for e in kdoc}
        cls.catalog_tune = {e["id"]: e.get("tune_key") for e in kdoc}

    def fresh(self):
        return copy.deepcopy(self.doc)

    def evaluate(self, doc):
        return vn.evaluate(doc, self.rows, self.f_blob, self.f_rel,
                           self.catalog_ids, self.catalog_tune)

    def by_id(self, doc, lid):
        return next(e for e in doc["ids"]
                    if e["logical_id"] == lid)

    def assert_fail(self, fails, pendings, klic):
        self.assertTrue(
            any(klic in f for f in fails),
            "očekáván FAIL s klíčem %r, fails=%s" % (klic, fails))
        self.assertEqual(_code(fails, pendings), 1)

    def assert_pending(self, fails, pendings, klic):
        self.assertEqual(fails, [], "očekáváno fails=[], fails=%s"
                         % (fails,))
        self.assertTrue(
            any(klic in p for p in pendings),
            "očekáván PENDING s klíčem %r, pendings=%s"
            % (klic, pendings))
        self.assertEqual(_code(fails, pendings), 2)

    # 1. ID přiřazené k řádku, který ho neobsahuje (E1).
    def test_01_spatny_radek(self):
        doc = self.fresh()
        doc["ids"][0]["source_rows"] = [9999]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "cizí source_rows")

    # 2. ID, které v buňce Interní ID daného řádku není (E1 + katalog).
    def test_02_neexistujici_id(self):
        doc = self.fresh()
        doc["ids"][0]["logical_id"] = "vymyslene_id_xyz"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "neobsahuje")

    # 3. Alias (Název/Tune klíč) vydávaný za ID (R3).
    def test_03_alias_jako_id(self):
        doc = self.fresh()
        rec = next(e for e in doc["ids"]
                   if e["logical_id"] == "weight_lb")
        rec["logical_id"] = "Weight"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "alias-jako-ID")

    # 4. Skupinový člen bez katalogového ID jako ID (R4).
    def test_04_skupina_neexistujici_clen(self):
        doc = self.fresh()
        vzor = next(e for e in doc["ids"]
                    if e["logical_id"] == "clutch_enabled")
        novy = copy.deepcopy(vzor)
        novy["logical_id"] = "clutch_rpm"
        novy["primary_name"] = "clutch_rpm"
        doc["ids"].append(novy)
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "nedoložený člen jako ID")

    # 5. Vynechaný člen skupiny — rozbalení neúplné (R2).
    def test_05_vynechany_clen_skupiny(self):
        doc = self.fresh()
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] != "rev_decay"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "vynechaný člen skupiny")

    # 6. Duplicita = multi-přiřazení (R5).
    def test_06_duplicita(self):
        doc = self.fresh()
        doc["ids"].append(copy.deepcopy(doc["ids"][0]))
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "duplicity ID")

    # 7. Jeden záznam přes řádky s různým stavem (R7).
    def test_07_konfliktni_statusy(self):
        doc = self.fresh()
        rec = next(e for e in doc["ids"]
                   if e["logical_id"] == "weight_lb")
        rec["source_rows"] = [52, 53]  # ESTIMATED vs UNKNOWN řádek
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "konfliktní statusy")

    # 8. VERIFIED bez věcné evidence (E3).
    def test_08_verified_bez_evidence(self):
        doc = self.fresh()
        rec = next(e for e in doc["ids"]
                   if e["logical_id"] == "drive_config")
        rec["evidence"] = {"mustang_cil": "UNKNOWN",
                           "zdroj_cile": "—", "puvod": "—"}
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "VERIFIED-bez-evidence")

    # 9. Sloučení F/R páru do jednoho ID (R8 + R2).
    def test_09_fr_slouceni(self):
        doc = self.fresh()
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] not in ("downforce_f",
                                                 "downforce_r")]
        vzor = next(e for e in self.doc["ids"]
                    if e["logical_id"] == "downforce_f")
        sloucene = copy.deepcopy(vzor)
        sloucene["logical_id"] = "downforce"
        sloucene["primary_name"] = "downforce"
        doc["ids"].append(sloucene)
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "vynechaný člen skupiny")

    # 10. Odkaz na neexistující blob/řádek (E1 reference).
    def test_10_neexistujici_reference(self):
        doc = self.fresh()
        doc["ids"][0]["source_reference"] = doc["ids"][0][
            "source_reference"].replace(self.f_blob, "0" * 40)
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "neexistující reference")

    # 11. Poškozené source_rows (není seznam celých čísel).
    def test_11_spatne_source_rows(self):
        doc = self.fresh()
        doc["ids"][0]["source_rows"] = "122"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "špatné source_rows")

    # 12. Seznam 60 nedoložen → PENDING, exit ≠ 0, nikdy PASS (E4/E5).
    def test_12_seznam_60_nedolozen_pending(self):
        fails, pendings, _ = self.evaluate(self.fresh())
        self.assertEqual(fails, [])
        self.assertTrue(
            any("ORIGINAL_LOGICAL_IDS" in p for p in pendings),
            "pendings=%s" % pendings)
        self.assertEqual(_code(fails, pendings), 2)

    # 13. Meta agregace nesedí se strojovým výpočtem.
    def test_13_metadata_nesoulad(self):
        doc = self.fresh()
        doc["meta"]["odvozeno_strojove"]["stavy_id"]["VERIFIED"] += 1
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "metadata-nesoulad")

    # 14. Neplatný JSON se nenačte jako data.
    def test_14_neplatny_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            f.write("{ toto neni json !!!")
            tmp = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                vn.load_doc(tmp)
            self.assertIn("FAIL", str(ctx.exception))
        finally:
            os.unlink(tmp)


    # ---- E1: zdrojová vazba (6 nových) ----
    def test_15_source_rows_bool(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["source_rows"] = [True]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "špatné source_rows")

    def test_16_source_rows_duplicita(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["source_rows"] = [52, 52]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "duplicitní source_rows")

    def test_17_radek_bez_id(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["source_rows"] = [53]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "neodpovídá zdrojovému řádku")

    def test_18_chybejici_clen_skupiny(self):
        doc = self.fresh()
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] != "rev_accel"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "E1-neúplná-vazba")

    def test_19_id_bez_opory(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["source_rows"] = [52, 53]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "E1-ID-bez-opory")

    def test_20_prazdne_source_rows(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["source_rows"] = []
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "špatné source_rows")

    # ---- R7: status dědí zdrojový řádek (4 nové) ----
    def test_21_r7_prohozeni_statusu(self):
        doc = self.fresh()
        a = self.by_id(doc, "drive_config")      # VERIFIED, ř.158
        b = self.by_id(doc, "differential_type")  # UNKNOWN, ř.159
        a["status"], b["status"] = b["status"], a["status"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "status-neodpovídá-zdroji")

    def test_22_r7_chybny_status_jednoho_id(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["status"] = "UNKNOWN"  # ř.52 ESTIMATED
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "status-neodpovídá-zdroji")

    def test_23_r7_status_clena_skupiny(self):
        doc = self.fresh()
        self.by_id(doc, "downforce_f")["status"] = "PENDING"  # ř.173 UNKNOWN
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "status-neodpovídá-zdroji")

    def test_24_r7_zadne_multi_source_rows(self):
        doc = self.fresh()
        multi = [e["logical_id"] for e in doc["ids"]
                 if isinstance(e.get("source_rows"), list)
                 and len(e["source_rows"]) > 1]
        self.assertEqual(multi, [],
                         "očekáváno: žádný záznam nemá více source_rows")
        rec = self.by_id(doc, "weight_lb")
        rec["source_rows"] = [52, 53]  # ESTIMATED vs UNKNOWN řádek
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "konfliktní statusy")

    # ---- R8: F/R a L/R (5 nových) ----
    def test_25_r8_fr_slouceni(self):
        doc = self.fresh()
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] not in ("downforce_f",
                                                 "downforce_r")]
        vzor = next(e for e in self.doc["ids"]
                    if e["logical_id"] == "downforce_f")
        sloucene = copy.deepcopy(vzor)
        sloucene["logical_id"] = "downforce"
        sloucene["primary_name"] = "downforce"
        doc["ids"].append(sloucene)
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "F/R pár sloučen/chybí")

    def test_26_r8_chybejici_clen(self):
        doc = self.fresh()
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] != "sus_stiffness_r"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "F/R pár sloučen/chybí")

    def test_27_r8_lr_chybejici_clen(self):
        doc = self.fresh()
        vzor = self.by_id(self.doc, "weight_lb")
        novy = copy.deepcopy(vzor)
        novy["logical_id"] = "zk_test_l"
        novy["primary_name"] = "ZkTestL"
        doc["ids"].append(novy)
        orig_lr = vn.LR_PAIRS
        vn.LR_PAIRS = [("zk_test_l", "zk_test_r")]  # type: ignore
        try:
            fails, pendings, _ = self.evaluate(doc)
        finally:
            vn.LR_PAIRS = orig_lr  # type: ignore
        self.assert_fail(fails, pendings, "L/R pár sloučen/chybí")

    def test_28_r8_falesne_sparovani(self):
        # front_diff_power / rear_diff_power nejsou R8 pár (odlišné osy
        # power/coast) — odebrání jednoho nesmí hlásit R8, jen E1/R2.
        doc = self.fresh()
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] != "front_diff_power"]
        fails, pendings, _ = self.evaluate(doc)
        self.assertTrue(any("E1-neúplná-vazba" in f for f in fails),
                        "fails=%s" % fails)
        self.assertFalse(any("pár sloučen" in f for f in fails),
                         "falešný R8 pár, fails=%s" % fails)
        self.assertEqual(_code(fails, pendings), 1)

    def test_29_r8_spravne_oddeleni(self):
        fails, pendings, _ = self.evaluate(self.fresh())
        self.assertFalse(any("pár sloučen" in f for f in fails),
                         "fails=%s" % fails)
        self.assertFalse(any("nerozlišený klíč" in f for f in fails),
                         "fails=%s" % fails)

    # ---- R3/R6: názvy a aliasy (8 nových) ----
    def test_30_r6_primary_bezneho(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["primary_name"] = "Hmotnost"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "R6-název-nesouhlasí")

    def test_31_r6_cizi_alias_bezneho(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["aliases"] = ["Hmotnost-navic"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "R6-cizí-alias")

    def test_32_r6_nazev_chybi_v_aliases(self):
        doc = self.fresh()
        rec = self.by_id(doc, "rev_decay")
        rec["aliases"] = ["RevDecay"]  # bez Název řádku
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "R6 názvy")

    def test_33_r6_prazdne_aliases_clena(self):
        doc = self.fresh()
        self.by_id(doc, "downforce_f")["aliases"] = []
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "R6 názvy")

    def test_34_r6_alias_je_cizi_id(self):
        doc = self.fresh()
        rec = self.by_id(doc, "clutch_enabled")
        rec["aliases"] = ["Clutch", "clutch_engage"]
        if "clutch_engage" not in self.catalog_ids:
            rec["aliases"] = ["Clutch", "rev_decay"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "alias-je-ID")

    def test_35_r6_cizi_tune_key(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["aliases"] = ["Weight"]
        rec = self.by_id(doc, "idle_rpm")
        rec["aliases"] = ["Weight"]  # tune_key weight_lb
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "R6-cizí-alias")

    def test_36_r6_primary_clena_musi_byt_id(self):
        doc = self.fresh()
        self.by_id(doc, "downforce_f")["primary_name"] = "Downforce"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "R6 názvy")

    def test_37_r3_cizi_tune_jako_id(self):
        doc = self.fresh()
        rec = self.by_id(doc, "weight_lb")
        rec["logical_id"] = "IdleRPM"  # primary_name, ne Interní ID
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "alias-jako-ID")

    # ---- E3: provenience (8 nových) ----
    def test_38_e3_verified_vymysl(self):
        doc = self.fresh()
        self.by_id(doc, "drive_config")["evidence"]["mustang_cil"] = "xxx"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "VERIFIED-bez-evidence")

    def test_39_e3_verified_bez_hodnoty(self):
        doc = self.fresh()
        self.by_id(doc, "drive_config")["evidence"]["mustang_cil"] = "—"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "VERIFIED-bez-evidence")

    def test_40_e3_verified_bez_lokatoru(self):
        doc = self.fresh()
        self.by_id(doc, "drive_config")["evidence"]["zdroj_cile"] = \
            "viz audit"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "VERIFIED-bez-evidence")

    def test_41_e3_verified_odhad_neni_dukaz(self):
        doc = self.fresh()
        self.by_id(doc, "drive_config")["evidence"]["puvod"] = "odhad"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "VERIFIED-bez-evidence")

    def test_42_e3_estimated_bez_puvodu(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["evidence"]["puvod"] = "N/A"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ESTIMATED-bez-původu")

    def test_43_e3_estimated_bez_zdroje(self):
        doc = self.fresh()
        self.by_id(doc, "weight_lb")["evidence"]["zdroj_cile"] = "—"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ESTIMATED-bez-zdroje")

    def test_44_e3_estimated_slaby_puvod_k_revizi(self):
        doc = self.fresh()
        rec = self.by_id(doc, "weight_lb")
        rec["evidence"]["puvod"] = "odhad"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_pending(fails, pendings, "ESTIMATED-k-revizi")

    def test_45_e3_unknown_konkretni_cil_k_revizi(self):
        doc = self.fresh()
        rec = self.by_id(doc, "differential_type")
        rec["evidence"]["mustang_cil"] = "LSD Torsen?"
        fails, pendings, _ = self.evaluate(doc)
        self.assert_pending(fails, pendings, "ruční-review")

    # ---- 60/94: oddělené množiny (6 nových) ----
    def test_46_g60_z_94_se_neprijima(self):
        doc = self.fresh()
        doc["meta"]["original_60_set"]["seznam"] = \
            [e["logical_id"] for e in doc["ids"][:60]]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ORIGINAL_LOGICAL_IDS")

    def test_47_g60_kratky_seznam_se_neprijima(self):
        doc = self.fresh()
        doc["meta"]["original_60_set"]["seznam"] = \
            [e["logical_id"] for e in doc["ids"][:59]]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ORIGINAL_LOGICAL_IDS")

    def test_48_g94_schvaleni_strukturalne_ok(self):
        import hashlib
        doc = self.fresh()
        idset = sorted(e["logical_id"] for e in doc["ids"])
        doc["meta"]["accepted_mapped_set"] = {
            "status": "APPROVED",
            "seznam": idset,
            "sha_data": hashlib.sha256(",".join(idset).encode("utf-8")
                                       ).hexdigest(),
            "rozhodnuti": "test-fixture",
            "datum": "2026-11-20",
        }
        fails, pendings, _ = self.evaluate(doc)
        self.assertFalse(any("ACCEPTED" in f for f in fails),
                         "fails=%s" % fails)
        self.assertTrue(any("ORIGINAL_LOGICAL_IDS" in p
                            for p in pendings),
                        "historická 60 zůstává PENDING, pendings=%s"
                        % pendings)
        self.assertEqual(_code(fails, pendings), 2)

    def test_49_g94_schvaleni_spatne_sha(self):
        import hashlib
        doc = self.fresh()
        idset = sorted(e["logical_id"] for e in doc["ids"])
        doc["meta"]["accepted_mapped_set"] = {
            "status": "APPROVED",
            "seznam": idset,
            "sha_data": "0" * 64,
            "rozhodnuti": "test-fixture",
            "datum": "2026-11-20",
        }
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ACCEPTED_MAPPED_SET")

    def test_50_g94_schvaleni_chybi_id(self):
        import hashlib
        doc = self.fresh()
        idset = sorted(e["logical_id"] for e in doc["ids"])[:-1]
        doc["meta"]["accepted_mapped_set"] = {
            "status": "APPROVED",
            "seznam": idset,
            "sha_data": hashlib.sha256(",".join(idset).encode("utf-8")
                                       ).hexdigest(),
            "rozhodnuti": "test-fixture",
            "datum": "2026-11-20",
        }
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ACCEPTED_MAPPED_SET")

    def test_51_g94_zmena_dat_po_schvaleni(self):
        import hashlib
        doc = self.fresh()
        idset = sorted(e["logical_id"] for e in doc["ids"])
        doc["meta"]["accepted_mapped_set"] = {
            "status": "APPROVED",
            "seznam": idset,
            "sha_data": hashlib.sha256(",".join(idset).encode("utf-8")
                                       ).hexdigest(),
            "rozhodnuti": "test-fixture",
            "datum": "2026-11-20",
        }
        doc["ids"] = [e for e in doc["ids"]
                      if e["logical_id"] != "weight_lb"]
        fails, pendings, _ = self.evaluate(doc)
        self.assert_fail(fails, pendings, "ACCEPTED_MAPPED_SET")


if __name__ == "__main__":
    unittest.main()

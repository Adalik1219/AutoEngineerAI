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
    """14 negativních případů E6 — každý musí prokázat FAIL/PENDING."""

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
            cls.catalog_ids = {e["id"] for e in json.load(f)}

    def fresh(self):
        return copy.deepcopy(self.doc)

    def evaluate(self, doc):
        return vn.evaluate(doc, self.rows, self.f_blob, self.f_rel,
                           self.catalog_ids)

    def assert_fail(self, fails, pendings, klic):
        self.assertTrue(
            any(klic in f for f in fails),
            "očekáván FAIL s klíčem %r, fails=%s" % (klic, fails))
        self.assertEqual(_code(fails, pendings), 1)

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


if __name__ == "__main__":
    unittest.main()

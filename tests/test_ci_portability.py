"""Regresní testy CI přenositelnosti (Test & Fuzzing Engineer).

Každý test kryje jednu příčinu červeného CI (run 44581124660):
  1. žádné absolutní cesty v tests/ a tools/ (repo-relative),
  2. loader referencí repo-relative (default z umístění souboru,
     env jen explicitní override; žádný import-time side effect),
  3. RBXM fixture = verzovaný JeepTemplate se SHA kontrolou,
  4. chybějící ne-verzovaný soubor -> SKIP (PENDING), ne ERROR,
  5. kanonický runner = tests/run_all.py (i ve workflow).

Pravidla: stdlib only, česky komentáře, identifikátory anglicky.
"""

import hashlib
import os
import re
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Záměrně ŽÁDNÝ import-time side effect na prostředí (žádné
# os.environ[...] = ... na úrovni modulu): loader default odvozuje kořen
# z vlastního umístění, takže testy musí projít i bez přednastaveného env
# — jinak by maskovaly regresi hardcoded defaultu (původní chyba CI).

from src.Reference import loader  # noqa: E402

try:
    import test_m2_rbxm_parser as m2  # noqa: E402
except ImportError:  # beh pres `python -m unittest tests.test_...` z korene
    from tests import test_m2_rbxm_parser as m2  # noqa: E402

JEEP_FIXTURE = os.path.join(
    ROOT, "testgame", "src", "ServerStorage", "VehicleTemplates",
    "JeepTemplate.rbxm")
EXPECTED_SHA256 = ("dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd"
                   "7c070c2c1fefdf")
EXPECTED_SIZE = 230421

#: Absolutní cesty — v testech zakázané: windowsovský disk (C:\…)
#: a unixový absolut ("/home…" v řetězci). Relativní "tests/…" a dělení
#: řetězců (split("/")) záměrně nechytá: za lomítkem musí být znak cesty.
ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:[\\/]|['\"]/[A-Za-z~]")


class TestRepoRelativePaths(unittest.TestCase):
    """1. Žádné absolutní cesty v tests/ a tools/."""

    def test_no_absolute_paths_in_tests_and_tools(self):
        """Grep-regrese: zadne absolutni disky ani absolutni /cesty."""
        bad = []
        for dirname in ("tests", "tools"):
            dpath = os.path.join(ROOT, dirname)
            for name in sorted(os.listdir(dpath)):
                if not name.endswith(".py"):
                    continue
                if name == "__init__.py":
                    continue
                fpath = os.path.join(dpath, name)
                with open(fpath, encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        code = line.split("#", 1)[0]
                        if ABSOLUTE_PATH_RE.search(code):
                            bad.append("%s:%d: %s"
                                       % (name, lineno, line.strip()))
        self.assertEqual(bad, [],
                         "absolutní cesty v testech/nástrojích: %r" % (bad,))


class TestLoaderRepoRelative(unittest.TestCase):
    """2. Loader referencí funguje repo-relative (bez defaultu vývojáře)."""

    def _without_env(self):
        """Kontext bez override proměnné (senses repo z umístění souboru)."""
        env = dict(os.environ)
        env.pop("AUTOENGINEERAI_ROOT", None)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_load_schema_repo_relative(self):
        """_schema.json se načte z tohoto repa (default, bez env)."""
        with self._without_env():
            schema = loader.load_schema()
            self.assertIsInstance(schema, dict)
            self.assertEqual(loader.schema_path(),
                             loader.references_dir() / "_schema.json")

    def test_references_dir_points_into_this_repo(self):
        """references_dir() leží uvnitř tohoto repa (ne default vývojáře)."""
        with self._without_env():
            refs = str(loader.references_dir())
            self.assertTrue(refs.startswith(ROOT),
                            "references_dir mimo repo: %r" % refs)

    def test_mustang_test_has_no_import_time_env_side_effect(self):
        """Regrese: mustang test nesjednocuje kořen zápisem do env při importu.

        Původní stav (os.environ[...] = ... na úrovni modulu) maskoval
        hardcoded default loaderu; kořen se nyní odvozuje z umístění
        souboru (kryto v tests/test_reference_loader_root.py). Testuje se
        jen kód (bez # komentářů) na nejvyšší úrovni odsazení — záměrně
        projde i na souboru, kde AUTOENGINEERAI_ROOT zmiňuje jen komentář.
        """
        fpath = os.path.join(ROOT, "tests", "test_m1_mustang_profile.py")
        with open(fpath, encoding="utf-8") as fh:
            src = fh.read()
        bad = []
        for lineno, line in enumerate(src.splitlines(), 1):
            code = line.split("#", 1)[0]
            if not code.strip():
                continue
            if code[0].isspace():
                continue  # uvnitř funkcí/tříd (např. mock.patch.dict) je OK
            if re.search(r"os\.environ|os\.putenv", code):
                bad.append("%d: %s" % (lineno, line.strip()))
        self.assertEqual(bad, [],
                         "import-time side effect na env: %r" % (bad,))

    def test_mustang_fixture_resolves_without_env(self):
        """Mustang profil se najde přes default kořen i bez env."""
        with self._without_env():
            fpath = (loader.references_dir()
                     / "ford-mustang-gt-2024-eu-manual-standard.json")
            self.assertTrue(os.path.exists(str(fpath)),
                            "mustang profil mimo default kořen: %s" % fpath)

    def test_loader_source_has_no_hardcoded_default(self):
        """Regrese: v loader.py není hardcoded absolutní default kořene.

        Behaviorální testy výše chytí hardcoded default, jen když repo
        leží jinde (na tomto stroji se kryje s cestou vývojáře);
        tento zdrojový test chytí původní chybu i zde.
        """
        fpath = os.path.join(ROOT, "src", "Reference", "loader.py")
        with open(fpath, encoding="utf-8") as fh:
            bad = ["%d: %s" % (lineno, line.strip())
                   for lineno, line in enumerate(fh, 1)
                   if ABSOLUTE_PATH_RE.search(line.split("#", 1)[0])]
        self.assertEqual(bad, [],
                         "hardcoded absolutní cesta v loaderu: %r" % (bad,))


class TestJeepFixture(unittest.TestCase):
    """3. Fixture = verzovaný JeepTemplate se SHA kontrolou."""

    def test_jeep_fixture_exists_with_expected_hash_and_size(self):
        """Fixture existuje v repu, hash + velikost = dokumentovaná."""
        self.assertTrue(os.path.exists(JEEP_FIXTURE),
                        "verzovaná fixture chybí: %s" % JEEP_FIXTURE)
        digest = hashlib.sha256()
        with open(JEEP_FIXTURE, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        self.assertEqual(digest.hexdigest(), EXPECTED_SHA256)
        self.assertEqual(os.path.getsize(JEEP_FIXTURE), EXPECTED_SIZE)


class TestSkipNotError(unittest.TestCase):
    """4. Chybějící ne-verzovaný soubor -> SKIP, ne ERROR."""

    def test_require_real_copy_skips_when_both_missing(self):
        """Guard hlásí SkipTest (PENDING), když chybí oba RBXM."""
        orig_jeep, orig_work = m2.JEEP_COPY, m2.WORK_COPY
        m2.JEEP_COPY = os.path.join(ROOT, "neexistuje-fixture-xyz.rbxm")
        m2.WORK_COPY = os.path.join(ROOT, "neexistuje-work-xyz.rbxm")
        try:
            with self.assertRaises(unittest.SkipTest):
                m2._require_real_copy(self)
        finally:
            m2.JEEP_COPY, m2.WORK_COPY = orig_jeep, orig_work

    def test_require_real_copy_prefers_versioned_fixture(self):
        """Je-li fixture přítomna, guard vrátí ji (CI stabilita)."""
        if not os.path.exists(JEEP_FIXTURE):
            self.skipTest("PENDING: fixture není v prostředí")
        self.assertEqual(m2._require_real_copy(self), m2.JEEP_COPY)


class TestCanonicalRunner(unittest.TestCase):
    """5. Kanonický runner = tests/run_all.py (i ve workflow)."""

    def test_workflow_runs_run_all(self):
        """CI workflow spouští právě tests/run_all.py."""
        wf = os.path.join(ROOT, ".github", "workflows", "ci.yml")
        if not os.path.exists(wf):
            for name in os.listdir(os.path.join(ROOT, ".github",
                                                "workflows")):
                if name.endswith((".yml", ".yaml")):
                    wf = os.path.join(ROOT, ".github", "workflows", name)
                    break
        with open(wf, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("python tests/run_all.py", content)

    def test_run_all_reports_pass_fail_pending(self):
        """run_all tiskne souhrn PASS/FAIL/PENDING (smlouva runneru)."""
        fpath = os.path.join(ROOT, "tests", "run_all.py")
        with open(fpath, encoding="utf-8") as fh:
            src = fh.read()
        for token in ("SOUHRN", "PENDING", "VYSLEDEK"):
            self.assertIn(token, src)


if __name__ == "__main__":
    unittest.main(verbosity=2)

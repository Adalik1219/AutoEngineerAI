"""Regresní testy kořene loaderu referencí (Reference Loader Engineer).

Kryje opravu project_root() v src/Reference/loader.py: defaultní kořen se
odvozuje z umístění loader.py (loader.py -> src/Reference -> root), env
AUTOENGINEERAI_ROOT zůstává explicitním overridem. Žádný import-time side
effect na prostředí — env se mění jen lokálně v rámci testů.

Pravidla: stdlib only (unittest), česky komentáře, identifikátory anglicky.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Reference import loader  # noqa: E402


def _without_env():
    """Kontext bez override proměnné (senses repo z umístění souboru)."""
    env = dict(os.environ)
    env.pop("AUTOENGINEERAI_ROOT", None)
    return mock.patch.dict(os.environ, env, clear=True)


class LoaderRootTest(unittest.TestCase):
    """Default z umístění souboru + explicitní env override."""

    def test_default_root_derived_from_loader_location(self):
        """Bez env: root = parents[2] souboru loader.py, uvnitř tohoto repa."""
        with _without_env():
            expected = Path(loader.__file__).resolve().parents[2]
            self.assertEqual(loader.project_root(), expected)
            self.assertEqual(str(loader.project_root()), ROOT)

    def test_references_dir_inside_repo_without_env(self):
        """Bez env: references_dir() leží uvnitř tohoto repa."""
        with _without_env():
            refs = loader.references_dir()
            self.assertTrue(str(refs).startswith(ROOT),
                            "references_dir mimo repo: %r" % (str(refs),))
            self.assertEqual(refs, Path(ROOT) / "vehicle-data" / "references")

    def test_explicit_env_overrides_default(self):
        """S explicitním env: project_root() vrací právě jeho hodnotu."""
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AUTOENGINEERAI_ROOT": tmp}):
                self.assertEqual(loader.project_root(), Path(tmp))
                self.assertEqual(loader.references_dir(),
                                 Path(tmp) / "vehicle-data" / "references")

    def test_load_schema_without_env(self):
        """Bez env: _schema.json se načte z tohoto repa."""
        with _without_env():
            schema = loader.load_schema()
            self.assertIsInstance(schema, dict)
            self.assertIn("properties", schema)
            self.assertIn("schema_version", schema["properties"])

    def test_load_all_without_env(self):
        """Bez env: load_all() načte povinnou trojici profilů."""
        with _without_env():
            profiles = loader.load_all()
            self.assertEqual(len(profiles), len(loader.REFERENCE_FILENAMES))
            for filename in loader.REFERENCE_FILENAMES:
                data = loader.load_profile(loader.references_dir() / filename)
                self.assertIn(data.get("vehicle_id", filename), profiles)


if __name__ == "__main__":
    unittest.main()

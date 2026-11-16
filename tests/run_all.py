"""Spoustec cele testovaci sady — stdlib unittest, exit 0/1.

Použití:
    python tests/run_all.py            # cela sada, souhrn PASS/FAIL/PENDING
    python -m unittest discover -s tests [-v]

PENDING = skipped testy (moduly vlny 1 zatim neexistuji nebo baseline
chybi). PENDING neni PASS: slouzi koordinatorovi jako seznam toho,
co vlna 1 jeste nedodala. Zadny externi framework ani sluzba.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    loader = unittest.TestLoader()
    suite = loader.discover(HERE, pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    passed = (result.testsRun - len(result.failures)
              - len(result.errors) - len(result.skipped))
    print("=" * 60)
    print("SOUHRN: behu=%d PASS=%d FAIL=%d ERROR=%d PENDING=%d" % (
        result.testsRun, passed, len(result.failures),
        len(result.errors), len(result.skipped)))
    if result.skipped:
        print("PENDING (neschvaluj nehotove — neni to PASS):")
        for test, reason in result.skipped:
            print("  - %s: %s" % (test, reason))
    if not result.wasSuccessful():
        print("VYSLEDEK: FAIL")
        return 1
    print("VYSLEDEK: PASS (s %d PENDING)" % len(result.skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Spolecne pomocne funkce pro testy vlny 1 (Agent H, integracni tester).

Pravidla: stdlib only, zadne sitove/exter magazines sluzby.
PENDING = modul vlny 1 jeste neexistuje -> test se preskoci proti
ARCHITECTURE kontraktu (§5), nehlasi PASS ani FAIL.
"""
import importlib
import unittest

# Kontrakt: jmena modulu vlny 1, jak je ocekava zadani.
# Skutecna struktura dle ARCHITECTURE §7 je src/Physics, src/Chassis, ...
# Testy zkousi obe varianty zapisu a pri neexistenci hlasi PENDING (skip).
EXPECTED_MODULES = [
    "Physics",
    "Sim",
    "Chassis",
    "Reference",
    "Telemetry",
    "Optimizer",
]

SRC_CANDIDATES = ["src.{m}", "{m}"]


def try_import(module_short_name):
    """Vrati (module, used_name) nebo (None, None) pri neexistenci."""
    for pattern in SRC_CANDIDATES:
        name = pattern.format(m=module_short_name)
        try:
            return importlib.import_module(name), name
        except ImportError:
            continue
    return None, None


def requires_module(testcase_func=None, *, module):
    """Dekorator: preskoci test jako PENDING, chybi-li modul vlny 1."""
    def decorator(fn):
        def wrapper(self):
            mod, _ = try_import(module)
            if mod is None:
                self.skipTest("PENDING: modul %s (kontrakt ARCHITECTURE §5) "
                              "ve vlne 1 zatim neexistuje" % module)
            return fn(self, mod)
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    if testcase_func is not None:
        return decorator(testcase_func)
    return decorator


class ContractTestCase(unittest.TestCase):
    """Base pro kontraktni testy: helper pro PENDING skip."""

    def load_or_pending(self, module):
        mod, used = try_import(module)
        if mod is None:
            self.skipTest("PENDING: modul %s (kontrakt ARCHITECTURE §5) "
                          "ve vlne 1 zatim neexistuje" % module)
        return mod

"""Regresni kostra (TESTING-OPTIMIZATION §6.2).

Zamer: po kazdem povyseni best_variant spustit rychlou matici na vsech
drive projetych scenari a overit, ze zadna drive splnena tolerance se
nerozbila; historie je append-only (§5.4, §6.2).

Stav vlny 1: zadna baseline zatim neexistuje (Faze 9/10 neprobehly).
Kostra je spustitelna: kontroluje strukturu zaznamu, pravidla
append-only historie a detekci regrese na syntetickych datech.
Napojeni na VariantStore z vlny 1 je oznaceno PENDING.
"""
import unittest

try:
    from _helpers import try_import
except ImportError:  # unittest discover z korene: tests jako balik
    from tests._helpers import try_import

# Regresni prahy — kalibruje Faze 9/10 dle namereneho rozptylu (§8.2 P5).
# Docasne hodnoty = navrhy z §4.6/§5.5, verzovane zde.
REPEAT_TOL = {"times": 0.02, "distances": 0.03, "rms": 0.05}
SCENARIO_TOL = 0.03  # §5.5 bod 3: zadny scenar se nesmi zhorsit o > 3 %


def check_no_regression(baseline_metrics, candidate_metrics, tol=SCENARIO_TOL):
    """Vrati seznam regresi [(metrika, baseline, kandidat, rel_zmena)]."""
    regressions = []
    for name, base in baseline_metrics.items():
        if name not in candidate_metrics:
            continue
        cand = candidate_metrics[name]
        if base == 0:
            continue
        rel = (cand - base) / abs(base)
        if rel > tol:
            regressions.append((name, base, cand, rel))
    return regressions


class AppendOnlyHistory:
    """Minimalni model VariantStore historie (nemenne varianty, §5.4)."""

    def __init__(self):
        self._entries = []
        self.best_id = None

    def add(self, variant_id, result):
        entry = {"variant_id": variant_id, "result": dict(result)}
        self._entries.append(entry)
        return entry

    def promote(self, variant_id):
        ids = [e["variant_id"] for e in self._entries]
        if variant_id not in ids:
            raise KeyError("neznama varianta: %s" % variant_id)
        old = self.best_id
        self.best_id = variant_id
        return old, variant_id

    def rollback(self, previous_id):
        return self.promote(previous_id)

    def __len__(self):
        return len(self._entries)


class TestRegressionDetection(unittest.TestCase):
    def test_no_change_no_regression(self):
        base = {"t_0_100": 7.5, "brake_distance": 41.2}
        self.assertEqual(check_no_regression(base, dict(base)), [])

    def test_improvement_no_regression(self):
        base = {"t_0_100": 7.5, "brake_distance": 41.2}
        cand = {"t_0_100": 7.0, "brake_distance": 40.0}
        self.assertEqual(check_no_regression(base, cand), [])

    def test_worsening_detected(self):
        base = {"t_0_100": 7.5, "brake_distance": 41.2}
        cand = {"t_0_100": 7.5, "brake_distance": 44.0}  # +6.8 %
        regs = check_no_regression(base, cand)
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0][0], "brake_distance")

    def test_within_tolerance_ok(self):
        base = {"t_0_100": 7.5}
        cand = {"t_0_100": 7.5 * 1.02}  # +2 % < 3 %
        self.assertEqual(check_no_regression(base, cand), [])

    def test_protected_metric_example(self):
        # Priklad zakazaneho obchodu z §5.3: t_0_100 -8 %, brzdy +3 %.
        base = {"t_0_100": 7.5, "brake_distance": 41.2}
        cand = {"t_0_100": 6.9, "brake_distance": 41.2 * 1.03 + 0.01}
        regs = dict((r[0], r) for r in check_no_regression(base, cand))
        self.assertIn("brake_distance", regs)


class TestAppendOnlyHistory(unittest.TestCase):
    def test_add_never_overwrites(self):
        h = AppendOnlyHistory()
        h.add("cfg_0001", {"total": 0.90})
        h.add("cfg_0002", {"total": 0.85})
        self.assertEqual(len(h), 2)
        self.assertEqual(h._entries[0]["variant_id"], "cfg_0001")

    def test_rollback_is_pointer_swap(self):
        h = AppendOnlyHistory()
        h.add("cfg_0001", {"total": 0.90})
        h.add("cfg_0002", {"total": 0.95})
        h.promote("cfg_0001")
        old, new = h.rollback("cfg_0001")
        self.assertEqual(h.best_id, "cfg_0001")
        self.assertEqual(len(h), 2)  # historie nesmazana

    def test_promote_unknown_fails(self):
        h = AppendOnlyHistory()
        with self.assertRaises(KeyError):
            h.promote("cfg_9999")

    def test_results_immutable_snapshot(self):
        h = AppendOnlyHistory()
        res = {"total": 0.90}
        h.add("cfg_0001", res)
        res["total"] = 0.10  # pozdejsi mutace nesmi sahnout do historie
        self.assertEqual(h._entries[0]["result"]["total"], 0.90)


class TestStoredBaseline(unittest.TestCase):
    """Napojeni na skutecnou baseline z vlny 1 — aktualne PENDING (Faze 9/10)."""

    def test_baseline_exists(self):
        self.skipTest("PENDING: baseline best_variant z Faze 9/10 zatim "
                      "neexistuje; po dodani VariantStore zde pripojit "
                      "plnou regresni sadu (§6.2)")

    def test_variant_store_append_only(self):
        mod, _ = try_import("Optimizer")
        if mod is None or not hasattr(mod, "VariantStore"):
            self.skipTest("PENDING: Optimizer.VariantStore ve vlne 1 "
                          "zatim neexistuje")
        self.skipTest("PENDING: VariantStore existuje, regresni napojeni "
                      "zatim neovereno proti realnym datum")


if __name__ == "__main__":
    unittest.main()

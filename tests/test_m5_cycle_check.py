# Testy detektoru cyklu zavislosti S-02 + integrace validace (Agent C).
"""Testy pro src/Chassis/mapping/cycle_check.py a validate_catalog.py.

Nove API Agenta B: has_cycle(graph) -> CycleResult, find_witness(graph),
check_integrity(graph), build_graph_from_catalog/records,
check_catalog_records/file -> CatalogCheckResult (.valid),
check_known_tables() -> CycleResult; find_cycles() = DEPRECATED wrapper.

Pouzivaji se pouze synteticka data + skutecny katalog parameters.json
(read-only). Zadna RBXM, zadna sit, zadne VERIFIED hodnoty.
"""

import copy
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Chassis.mapping.cycle_check import (
    CatalogCheckResult,
    CycleResult,
    InvalidGraphError,
    build_graph_from_catalog,
    build_graph_from_records,
    check_catalog_file,
    check_catalog_records,
    check_integrity,
    check_known_tables,
    find_witness,
    has_cycle,
)
from src.Chassis.mapping.gate import (
    gate_catalog_file,
    gate_catalog_records,
)
from src.Chassis.mapping_engine import (
    build_search_space,
    map_config,
)
from src.Chassis.mapping.validate_catalog import (
    STATUS_BLOCKED,
    STATUS_OK,
    validate_catalog_for_mapping,
    validate_records_for_mapping,
)

CATALOG_PATH = os.path.join(ROOT, "src", "Chassis", "catalog", "parameters.json")

# Zname vzajemne pary z auditu Agenta A (AGENT-A-S02-CATALOG-AUDIT.md, §5):
# kazdy je overeny 2-cyklus depends_on v realnych datech.
KNOWN_MUTUAL_PAIRS = frozenset([
    frozenset(("auto_shift_type", "shift_down_time")),
    frozenset(("auto_shift_type", "shift_up_time")),
    frozenset(("auto_up_thresh", "peak_rpm")),
    frozenset(("clutch_engage", "flywheel")),
    frozenset(("compress_lim_f", "sus_length_f")),
    frozenset(("compress_lim_r", "sus_length_r")),
    frozenset(("compression_ratio", "turbo_boost")),
    frozenset(("extension_lim_f", "sus_length_f")),
    frozenset(("extension_lim_r", "sus_length_r")),
    frozenset(("final_drive", "gear_ratios")),
    frozenset(("flywheel", "rev_accel")),
    frozenset(("lock_to_lock", "steer_ratio")),
    frozenset(("pbrake_bias", "pbrake_force")),
    frozenset(("pre_compress_f", "sus_length_f")),
    frozenset(("pre_compress_r", "sus_length_r")),
    frozenset(("redline_rpm", "rev_bounce")),
    frozenset(("tcs_gradient", "tcs_threshold_sps")),
    frozenset(("tcs_limit_pct", "tcs_threshold_sps")),
    frozenset(("weight_box_size", "weight_lb")),
])

OVERLAP_GRAPH = {"a": ["b", "c"], "b": ["c"], "c": ["a"]}


def assertValidWitness(testcase, graph, witness):
    """Overi svedka hranu po hrane: uzavrena cesta v grafu (ne jen non-None)."""
    testcase.assertIsInstance(witness, list)
    testcase.assertGreaterEqual(len(witness), 2,
                                "svedek musi mit aspon 2 prvky (uzavrena cesta)")
    testcase.assertEqual(witness[0], witness[-1],
                         "svedek musi byt uzavrena cesta (prvni == posledni)")
    for src, dst in zip(witness, witness[1:]):
        testcase.assertIn(src, graph, "uzel %r svedka neni v grafu" % (src,))
        testcase.assertIn(dst, graph.get(src, []),
                          "hrana %r -> %r svedka neni v grafu" % (src, dst))


def make_records(pairs):
    """Pomocna stavba zaznamu katalogu: pairs = [(id, [deps])]."""
    return [{"id": pid, "depends_on": list(deps)} for pid, deps in pairs]


class TestMigratedCore(unittest.TestCase):
    """Migrace pokryti starych testu na nove API (CycleResult semantika)."""

    def test_acyclic_graph_ok(self):
        graph = {"a": ["b", "c"], "b": ["c"], "c": ["d"]}
        result = has_cycle(graph)
        self.assertIsInstance(result, CycleResult)
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.witness_path, [])
        self.assertIsNone(find_witness(graph))

    def test_self_loop(self):
        result = has_cycle({"a": ["a"]})
        self.assertTrue(result.has_cycle)
        self.assertEqual(result.witness_path, ["a", "a"])
        assertValidWitness(self, {"a": ["a"]}, result.witness_path)

    def test_two_cycle(self):
        graph = {"a": ["b"], "b": ["a"]}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)
        self.assertEqual(len(result.witness_path), 3)

    def test_three_cycle(self):
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)
        self.assertEqual(len(result.witness_path), 4)

    def test_determinism(self):
        graph = {
            "m": ["n", "o"],
            "n": ["m", "o"],
            "o": ["o"],
            "p": ["m"],
        }
        first = has_cycle(graph)
        second = has_cycle(graph)
        self.assertEqual(first, second)
        self.assertEqual(find_witness(graph), find_witness(graph))

    def test_known_tables_acyclic(self):
        # Opravena semantika: check_known_tables vraci CycleResult, ne list.
        result = check_known_tables()
        self.assertIsInstance(result, CycleResult)
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.witness_path, [])


class TestOverlapWitness(unittest.TestCase):
    """Povinny prekryvovy graf: a->[b,c], b->[c], c->[a]."""

    def test_overlap_graph_cycle_with_valid_witness(self):
        result = has_cycle(OVERLAP_GRAPH)
        self.assertTrue(result.has_cycle)
        # Svedek musi byt platny cyklus overeny hranu po hrane.
        assertValidWitness(self, OVERLAP_GRAPH, result.witness_path)


class TestExtraCases(unittest.TestCase):
    """Dalsi pripady detekce, integrity a neplatnych vstupu."""

    def test_self_loop_in_larger_graph(self):
        graph = {"a": ["b"], "b": ["c"], "c": ["c", "d"], "d": []}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)

    def test_two_separate_cycles(self):
        graph = {"a": ["b"], "b": ["a"], "c": ["d"], "d": ["c"]}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)

    def test_cycles_sharing_node(self):
        # Dva cykly se spolecnym uzlem a: a->b->a a a->c->a.
        graph = {"a": ["b", "c"], "b": ["a"], "c": ["a"]}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)

    def test_cycles_sharing_edge(self):
        # Dva cykly se spolecnou hranou a->b: a->b->a a a->b->c->a.
        graph = {"a": ["b"], "b": ["a", "c"], "c": ["a"]}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)

    def test_longer_cycle_5(self):
        graph = {"a": ["b"], "b": ["c"], "c": ["d"], "d": ["e"], "e": ["a"]}
        result = has_cycle(graph)
        self.assertTrue(result.has_cycle)
        assertValidWitness(self, graph, result.witness_path)
        self.assertEqual(len(result.witness_path), 6)

    def test_large_acyclic_graph(self):
        # Retez 500 uzlu + odbocka: acyklicky, statistika sedi.
        graph = {"n%03d" % i: (["n%03d" % (i + 1)] if i < 499 else [])
                 for i in range(500)}
        graph["n000"].append("n499")
        result = has_cycle(graph)
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.witness_path, [])
        self.assertEqual(result.checked_nodes, 500)
        self.assertEqual(result.checked_edges, 500)

    def test_duplicate_edge(self):
        # Duplicitni hrana neni cyklus; statistika pocita unikatni hrany.
        result = has_cycle({"a": ["b", "b"], "b": []})
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.checked_edges, 1)

    def test_unknown_target_is_integrity_not_cycle(self):
        graph = {"a": ["ghost"]}
        self.assertEqual(check_integrity(graph), [("a", "ghost")])
        # Chybejici cil = chyba integrity, NE cyklus.
        self.assertFalse(has_cycle(graph).has_cycle)
        records = make_records([("a", ["ghost"])])
        checked = check_catalog_records(records)
        self.assertEqual(checked.integrity_errors, [("a", "ghost")])
        self.assertFalse(checked.has_cycle)
        self.assertFalse(checked.valid)

    def test_empty_graph(self):
        result = has_cycle({})
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.witness_path, [])
        self.assertEqual(result.checked_nodes, 0)
        self.assertEqual(result.checked_edges, 0)
        self.assertEqual(check_integrity({}), [])

    def test_invalid_graph_not_dict(self):
        with self.assertRaises(InvalidGraphError):
            has_cycle([("a", ["b"])])  # type: ignore

    def test_invalid_graph_non_string_node(self):
        with self.assertRaises(InvalidGraphError):
            has_cycle({1: ["a"]})  # type: ignore

    def test_invalid_graph_neighbours_not_list(self):
        with self.assertRaises(InvalidGraphError):
            has_cycle({"a": "b"})  # type: ignore

    def test_invalid_graph_non_string_target(self):
        with self.assertRaises(InvalidGraphError):
            has_cycle({"a": [1]})  # type: ignore

    def test_invalid_catalog_duplicate_id(self):
        records = make_records([("a", []), ("a", [])])
        with self.assertRaises(InvalidGraphError):
            check_catalog_records(records)

    def test_same_graph_different_edge_order(self):
        # Stejny graf v ruznem poradi hran: stejny vysledek i svedek.
        first = {"a": ["b", "c"], "b": ["c"], "c": ["a"]}
        second = {"c": ["a"], "b": ["c"], "a": ["c", "b"]}
        self.assertEqual(has_cycle(first), has_cycle(second))
        self.assertEqual(find_witness(first), find_witness(second))


class TestRealCatalog(unittest.TestCase):
    """Skutecny katalog parameters.json (read-only)."""

    def test_real_catalog_counts(self):
        graph = build_graph_from_catalog(CATALOG_PATH)
        self.assertEqual(len(graph), 138)
        self.assertEqual(sum(len(v) for v in graph.values()), 101)

    def test_real_catalog_has_cycle(self):
        result = check_catalog_file(CATALOG_PATH)
        self.assertIsInstance(result, CatalogCheckResult)
        self.assertTrue(result.has_cycle)
        self.assertFalse(result.valid)
        self.assertEqual(result.checked_nodes, 138)
        self.assertEqual(result.checked_edges, 101)

    def test_real_catalog_witness_matches_agent_a(self):
        # Ocekavany svedek z auditu Agenta A: cyklus c. 1
        # tcs_gradient <-> tcs_threshold_sps.
        result = check_catalog_file(CATALOG_PATH)
        graph = build_graph_from_catalog(CATALOG_PATH)
        assertValidWitness(self, graph, result.witness_path)
        self.assertEqual(
            result.witness_path,
            ["tcs_threshold_sps", "tcs_gradient", "tcs_threshold_sps"])
        self.assertIn(frozenset(result.witness_path), KNOWN_MUTUAL_PAIRS)

    def test_real_catalog_integrity_clean(self):
        graph = build_graph_from_catalog(CATALOG_PATH)
        self.assertEqual(check_integrity(graph), [])
        self.assertEqual(check_catalog_file(CATALOG_PATH).integrity_errors, [])


class TestValidationIntegration(unittest.TestCase):
    """Integrace: verdikt katalogu pro mapovaci cestu (validate_catalog)."""

    def _write_tmp_catalog(self, records):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False, encoding="utf-8")
        self.addCleanup(
            lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        with tmp:
            json.dump(records, tmp)
        return tmp.name

    def test_clean_catalog_ok(self):
        verdict = validate_records_for_mapping(
            make_records([("a", ["b"]), ("b", [])]))
        self.assertEqual(verdict.status, STATUS_OK)
        self.assertTrue(verdict.allowed)
        self.assertEqual(verdict.witness_path, [])

    def test_cyclic_catalog_blocked_with_path(self):
        verdict = validate_records_for_mapping(
            make_records([("a", ["b"]), ("b", ["a"])]))
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertFalse(verdict.allowed)
        graph = build_graph_from_records(
            make_records([("a", ["b"]), ("b", ["a"])]))
        assertValidWitness(self, graph, verdict.witness_path)
        self.assertIn("CYCLE", verdict.reason)

    def test_integrity_error_blocked_with_different_reason(self):
        verdict = validate_records_for_mapping(make_records([("a", ["ghost"])]))
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.integrity_errors, [("a", "ghost")])
        self.assertIn("INTEGRITY", verdict.reason)
        self.assertNotIn("CYCLE", verdict.reason)

    def test_negative_probe_cyclic_must_not_pass(self):
        # Katalog s cyklem NESMI projit PASS (souborova cesta).
        path = self._write_tmp_catalog(make_records(
            [("x", ["y"]), ("y", ["x"]), ("z", [])]))
        verdict = validate_catalog_for_mapping(path)
        self.assertNotEqual(verdict.status, STATUS_OK)
        self.assertEqual(verdict.status, STATUS_BLOCKED)

    def test_negative_probe_unknown_id_must_not_pass(self):
        # Katalog s neexistujicim id NESMI projit PASS (souborova cesta).
        path = self._write_tmp_catalog(make_records([("x", ["neexistuje"])]))
        verdict = validate_catalog_for_mapping(path)
        self.assertNotEqual(verdict.status, STATUS_OK)
        self.assertEqual(verdict.status, STATUS_BLOCKED)

    def test_real_catalog_blocked_for_mapping(self):
        verdict = validate_catalog_for_mapping(CATALOG_PATH)
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertFalse(verdict.allowed)
        self.assertIn("CYCLE", verdict.reason)
        graph = build_graph_from_catalog(CATALOG_PATH)
        assertValidWitness(self, graph, verdict.witness_path)


class TestMappingEntryPointIntegration(unittest.TestCase):
    """Integracni testy SKUTECNEHO mapovaciho entry pointu (Agent C, S-02).

    Kryje oba verejne vstupy z B-reportu §1 (map_config, build_search_space)
    pres spolecnou branu gate.py: Test A acyklicky OK; B 2-cyklus BLOCKED;
    C prekryvny graf svedek hranu po hrane; D INTEGRITY (ne cyklus);
    E neplatny katalog → NOT OK; F nulova zmena cile; G skutecny
    parameters.json → BLOCKED + svedek (brana neobejitelna).
    """

    @staticmethod
    def _mappable(rid, tune_key, config_path, vmin, vmax, depends=()):
        """Plny mapovatelny zaznam (5 filtru build_search_space + zavislosti)."""
        return {
            "id": rid, "tune_key": tune_key, "category": "MUTABLE_TUNE",
            "config_path": config_path, "value": vmax, "unit": "u",
            "value_type": "number", "min": vmin, "max": vmax,
            "default": vmax, "function": "test", "physical_effect": "test",
            "used_in": ["straight_accel"], "depends_on": list(depends),
            "conflicts": [], "change_method": "tune", "source": "test",
            "confidence": 1.0, "verification_status": "verified",
        }

    @staticmethod
    def _cfg(parameters):
        return {"schema_version": "1.0.0", "config_id": "cfg_s02",
                "vehicle_profile_id": "vp_s02",
                "chassis_adapter": "achassis-v1",
                "parameters": parameters}

    def _write_tmp_catalog(self, records):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False, encoding="utf-8")
        self.addCleanup(
            lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        with tmp:
            json.dump(records, tmp)
        return tmp.name

    def _acyclic_records(self):
        return [self._mappable("m_a", "T_A", "engine.a", 0, 10, ["m_b"]),
                self._mappable("m_b", "T_B", "engine.b", 0, 5)]

    def test_a_acyclic_catalog_ok_and_mapping(self):
        """Test A: acyklicky katalog → OK + mapovani probehne, hodnoty sedi."""
        records = self._acyclic_records()
        verdict = gate_catalog_records(records)
        self.assertEqual(verdict.status, STATUS_OK)
        self.assertTrue(verdict.allowed)
        self.assertEqual(verdict.witness_path, [])
        path = self._write_tmp_catalog(records)
        self.assertEqual(gate_catalog_file(path), verdict)
        res = map_config(self._cfg({"engine": {"a": 4, "b": 2}}),
                         path, "achassis-v1")
        self.assertEqual(res["rejected"], [])
        by_tune = {c["tune_key"]: c for c in res["tune_changes"]}
        self.assertEqual(set(by_tune), {"T_A", "T_B"})
        self.assertEqual(by_tune["T_A"]["value"], 4)
        self.assertEqual(by_tune["T_A"]["unit"], "u")
        self.assertEqual(by_tune["T_B"]["value"], 2)
        self.assertEqual(build_search_space(path, ["T_A", "T_B", "X"]),
                         ["T_A", "T_B"])

    def test_b_two_cycle_blocked_with_witness(self):
        """Test B: cyklicky katalog (2-cyklus) → BLOCKED + svedek, nic se
        nemapuje."""
        records = [self._mappable("m_a", "T_A", "engine.a", 0, 10, ["m_b"]),
                   self._mappable("m_b", "T_B", "engine.b", 0, 5, ["m_a"])]
        verdict = gate_catalog_records(records)
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertFalse(verdict.allowed)
        self.assertIn("CYCLE", verdict.reason)
        graph = build_graph_from_records(records)
        assertValidWitness(self, graph, verdict.witness_path)
        self.assertIn(" -> ".join(verdict.witness_path), verdict.reason)
        path = self._write_tmp_catalog(records)
        cfg = self._cfg({"engine": {"a": 4, "b": 2}})
        snapshot = copy.deepcopy(cfg)
        res = map_config(cfg, path, "achassis-v1")
        self.assertEqual(cfg, snapshot)
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(len(res["rejected"]), 1)
        self.assertEqual(res["rejected"][0]["param"], "*catalog*")
        self.assertIn("CYCLE", res["rejected"][0]["reason"])
        self.assertEqual(build_search_space(path, ["T_A", "T_B"]), [])

    def test_c_overlap_witness_edge_by_edge(self):
        """Test C: prekryv a->[b,c], b->[c], c->[a] → BLOCKED, svedek overen
        hranu po hrane pres souborovy entry point."""
        records = [self._mappable("m_a", "T_A", "engine.a", 0, 10,
                                  ["m_b", "m_c"]),
                   self._mappable("m_b", "T_B", "engine.b", 0, 5, ["m_c"]),
                   self._mappable("m_c", "T_C", "engine.c", 0, 7, ["m_a"])]
        path = self._write_tmp_catalog(records)
        verdict = gate_catalog_file(path)
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertIn("CYCLE", verdict.reason)
        graph = build_graph_from_catalog(path)
        assertValidWitness(self, graph, verdict.witness_path)
        res = map_config(self._cfg({"engine": {"a": 1}}), path, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(res["rejected"][0]["param"], "*catalog*")

    def test_d_unknown_id_is_integrity_not_cycle(self):
        """Test D: hrana na neexistujici id → BLOCKED INTEGRITY (NE cyklus)."""
        records = [self._mappable("m_a", "T_A", "engine.a", 0, 10, ["ghost"]),
                   self._mappable("m_b", "T_B", "engine.b", 0, 5)]
        verdict = gate_catalog_records(records)
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertFalse(verdict.allowed)
        self.assertIn("INTEGRITY", verdict.reason)
        self.assertNotIn("CYCLE", verdict.reason)
        self.assertEqual(verdict.integrity_errors, [("m_a", "ghost")])
        self.assertEqual(verdict.witness_path, [])
        path = self._write_tmp_catalog(records)
        res = map_config(self._cfg({"engine": {"a": 1}}), path, "achassis-v1")
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(res["rejected"][0]["param"], "*catalog*")
        self.assertIn("INTEGRITY", res["rejected"][0]["reason"])
        self.assertEqual(build_search_space(path, ["T_A", "T_B"]), [])

    def test_e_invalid_catalog_never_ok(self):
        """Test E: neplatny katalog (chybejici id / spatny typ / duplicitni
        id / ne-JSON / chybejici soubor) → vzdy BLOCKED/INVALID, nikdy OK,
        zadna vyjimka nepropadne ven."""
        bad_cases = [
            [{"depends_on": []}],  # chybejici id
            [{"id": "m_a", "depends_on": "m_b"}],  # spatny typ (str misto list)
            [{"id": "m_a", "depends_on": []},  # duplicitni id
             {"id": "m_a", "depends_on": []}],
        ]
        for records in bad_cases:
            verdict = gate_catalog_records(records)
            self.assertEqual(verdict.status, STATUS_BLOCKED, records)
            self.assertFalse(verdict.allowed)
            self.assertIn("INVALID", verdict.reason)
            path = self._write_tmp_catalog(records)
            res = map_config(self._cfg({"engine": {"a": 1}}), path,
                             "achassis-v1")
            self.assertEqual(res["tune_changes"], [])
            self.assertEqual(res["rejected"][0]["param"], "*catalog*")
            self.assertIn("INVALID", res["rejected"][0]["reason"])
            self.assertEqual(build_search_space(path, ["T_A"]), [])
        d = tempfile.mkdtemp()
        non_json = os.path.join(d, "bad.json")
        with open(non_json, "w", encoding="utf-8") as fh:
            fh.write("neni json {{{")
        for path in (non_json, os.path.join(d, "chybi.json")):
            verdict = gate_catalog_file(path)  # nesmi vyhodit
            self.assertEqual(verdict.status, STATUS_BLOCKED, path)
            self.assertIn("INVALID", verdict.reason)
            res = map_config(self._cfg({"engine": {"a": 1}}), path,
                             "achassis-v1")
            self.assertEqual(res["tune_changes"], [])
            self.assertIn("INVALID", res["rejected"][0]["reason"])
            self.assertEqual(build_search_space(path, ["T_A"]), [])

    def test_f_zero_target_change_when_blocked(self):
        """Test F: pri BLOCKED nulova zmena cile — vstup deepcopy-shodny,
        soubor katalogu byte-shodny, 2 behy deterministicky shodne."""
        records = [self._mappable("m_a", "T_A", "engine.a", 0, 10, ["m_b"]),
                   self._mappable("m_b", "T_B", "engine.b", 0, 5, ["m_a"])]
        path = self._write_tmp_catalog(records)
        with open(path, "rb") as fh:
            before_bytes = fh.read()
        cfg = self._cfg({"engine": {"a": 4, "b": 2}})
        snapshot = copy.deepcopy(cfg)
        first = map_config(cfg, path, "achassis-v1")
        second = map_config(cfg, path, "achassis-v1")
        self.assertEqual(cfg, snapshot)
        self.assertEqual(first, second)
        self.assertEqual(first["tune_changes"], [])
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), before_bytes)
        self.assertEqual(build_search_space(path, ["T_A", "T_B"]), [])
        self.assertEqual(build_search_space(path, ["T_A", "T_B"]), [])

    def test_g_real_catalog_blocked_unbypassable(self):
        """Test G: skutecny parameters.json → BLOCKED + platny svedek;
        brana neobejitelna: OBA entry pointy vraceji blokovano prazdno."""
        verdict = gate_catalog_file(CATALOG_PATH)
        self.assertEqual(verdict.status, STATUS_BLOCKED)
        self.assertFalse(verdict.allowed)
        self.assertIn("CYCLE", verdict.reason)
        self.assertEqual(
            verdict.reason,
            "CYCLE: katalog obsahuje cyklus depends_on "
            "(tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps)")
        self.assertEqual(verdict.witness_path,
                         ["tcs_threshold_sps", "tcs_gradient",
                          "tcs_threshold_sps"])
        self.assertEqual(verdict.integrity_errors, [])
        graph = build_graph_from_catalog(CATALOG_PATH)
        assertValidWitness(self, graph, verdict.witness_path)
        # Determinismus brany: 2 behy = stejny verdikt.
        self.assertEqual(gate_catalog_file(CATALOG_PATH), verdict)
        # Entry point 1: map_config — blokovano, vstup nezmenen.
        cfg = self._cfg({"engine": {"horsepower": 210},
                         "brakes": {"bias_front": 0.62}})
        snapshot = copy.deepcopy(cfg)
        res = map_config(cfg, CATALOG_PATH, "achassis-v1")
        self.assertEqual(cfg, snapshot)
        self.assertEqual(res["tune_changes"], [])
        self.assertEqual(len(res["rejected"]), 1)
        self.assertEqual(res["rejected"][0]["param"], "*catalog*")
        self.assertIn(verdict.reason, res["rejected"][0]["reason"])
        # Entry point 2: build_search_space — blokovano, prazdny prostor.
        self.assertEqual(
            build_search_space(CATALOG_PATH, ["BrakeBias", "WeightDist"]), [])


if __name__ == "__main__":
    unittest.main()

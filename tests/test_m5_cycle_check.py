# Testy detektoru cyklů závislostí S-02 (Agent B).
"""Testy pro src/Chassis/mapping/cycle_check.py.

Pouze syntetická data + KNOWN_* tabulky z dependencies.py (read-only).
Žádné RBXM, žádná síť, žádné VERIFIED hodnoty.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Chassis.mapping.cycle_check import check_known_tables, find_cycles


class TestFindCycles(unittest.TestCase):
    def test_acyclic_graph_ok(self):
        # Acyklický graf: lineární řetěz + větev, včetně listového uzlu mimo klíče.
        graph = {
            "a": ["b", "c"],
            "b": ["c"],
            "c": ["d"],
        }
        self.assertEqual(find_cycles(graph), [])

    def test_self_loop(self):
        # Smyčka na vlastním uzlu.
        self.assertEqual(find_cycles({"a": ["a"]}), [["a"]])

    def test_two_cycle(self):
        # Vzájemná závislost dvou parametrů.
        self.assertEqual(find_cycles({"a": ["b"], "b": ["a"]}), [["a", "b"]])

    def test_three_cycle(self):
        # Cyklus délky 3.
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        self.assertEqual(find_cycles(graph), [["a", "b", "c"]])

    def test_determinism(self):
        # Dvě volání nad stejným grafem (včetně více cyklů) dají stejný výsledek.
        graph = {
            "m": ["n", "o"],
            "n": ["m", "o"],
            "o": ["o"],
            "p": ["m"],
        }
        first = find_cycles(graph)
        second = find_cycles(graph)
        self.assertEqual(first, second)
        # Výstup je navíc setříděný.
        self.assertEqual(first, sorted(first))

    def test_known_tables_acyclic(self):
        # Známé tabulky z dependencies.py nesmí obsahovat cyklus.
        self.assertEqual(check_known_tables(), [])


if __name__ == "__main__":
    unittest.main()

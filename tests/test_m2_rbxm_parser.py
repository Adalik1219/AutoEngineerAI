"""Testy produkcniho RBXM parseru (M2, milnik C05-A/B): header, chunky,
LZ4, INST, PRNT + bezpecnostni pripady. Pouze stdlib (unittest).

Vstup: skutecna pracovni kopie
  assets/chassis-original/chasis-work-copy.rbxm (POUZE CTENI, nikdy zapis;
  test_hash_before_after overuje SHA-256 pred/po + shodu s dokumentovanou
  hodnotou). Synteticke poskozene varianty se stavi v pameti (builder nize,
  raw chunky bez komprese + rucne skladane LZ4 bloky), zadny zapis na disk.

Ocekavany integracni vysledek (poctivy castecny): hierarchie se dekoduje
uplne (815 instanci, 37 typu, koren, Model:Wheels + FL/FR/RL/RR), ale
geometrie je BLOCKED (shape=None, PROP hodnoty se v C05 neinterpretuji) —
wheel_detect proto hlasi UNKNOWN/bad_shape a BLOCKED, nikdy falesna kola.
"""
import hashlib
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.Inspection.rbxm_parser import (
    NULL_PARENT,
    RbxmCorruptError,
    RbxmError,
    RbxmHierarchyError,
    lz4_decompress,
    parse_bytes,
    parse_rbxm,
)
from src.Inspection.wheel_detect import detect_wheels, is_blocked

WORK_COPY = os.path.join(ROOT, "assets", "chassis-original",
                         "chasis-work-copy.rbxm")
# Dokumentovany hash pracovni kopie (reports/RBXM-SPIKE.md §2, audit §1).
EXPECTED_SHA256 = ("dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd"
                   "7c070c2c1fefdf")

MAGIC = b"<roblox!"
SIGNATURE = bytes((0x89, 0xFF, 0x0D, 0x0A, 0x1A, 0x0A))


def _zz_encode(value):
    """Zigzag kodovani (pouze pro stavbu syntetickych fixture)."""
    return (value << 1) ^ (value >> 31)


def _encode_referents(values):
    """Zakoduje absolutni referenty: delty -> zigzag -> 4 lane MSB prvni."""
    deltas = []
    prev = 0
    for value in values:
        deltas.append(_zz_encode(value - prev))
        prev = value
    count = len(values)
    lanes = [bytearray(count) for _ in range(4)]
    for i, delta in enumerate(deltas):
        lanes[0][i] = (delta >> 24) & 0xFF
        lanes[1][i] = (delta >> 16) & 0xFF
        lanes[2][i] = (delta >> 8) & 0xFF
        lanes[3][i] = delta & 0xFF
    return b"".join(bytes(lane) for lane in lanes)


def _u32(value):
    return struct.pack("<I", value)


def _string(text):
    encoded = text.encode("utf-8")
    return _u32(len(encoded)) + encoded


def _chunk(name, body, compress=False):
    """Postavi ramecek chunku (raw, nebo rucni LZ4 z cistych literalu)."""
    if isinstance(name, str):
        name = name.encode("ascii")
    if not compress:
        return (name + _u32(0) + _u32(len(body)) + b"\x00" * 4 + body)
    size = len(body)
    head = min(size, 15)
    extra = size - head
    block = bytearray((head << 4,))
    while extra > 0:
        byte = min(extra, 255)
        block.append(byte)
        extra -= byte
    block += body  # token: ciste literaly, zadny match
    return (name + _u32(len(block)) + _u32(size) + b"\x00" * 4
            + bytes(block))


def _inst(type_id, class_name, referents):
    return (_u32(type_id & 0xFFFFFFFF) + _string(class_name) + b"\x00"
            + _u32(len(referents)) + _encode_referents(referents))


def _name_prop(type_id, names):
    body = _u32(type_id & 0xFFFFFFFF) + _string("Name") + b"\x01"
    for text in names:
        body += _string(text)
    return body


def _prnt(kids, parents):
    assert len(kids) == len(parents)
    pars = [NULL_PARENT if p is None else p for p in parents]
    return (b"\x00" + _u32(len(kids))
            + _encode_referents(kids) + _encode_referents(pars))


def _sstr():
    return _u32(0)


def _meta():
    return _u32(1) + _string("ExplicitAutoJoints") + _string("true")


def _header(num_types, num_instances):
    return (MAGIC + SIGNATURE + struct.pack("<H", 0) + _u32(num_types)
            + _u32(num_instances) + b"\x00" * 8)


def build_model(inst_specs, links, extra_chunks=(), compress_names=False):
    """Minimalni platny RBXM v pameti.

    inst_specs: [(type_id, class_name, [jmena...])] v poradi referentu;
    links: [(child, parent)] (parent None = koren).
    """
    referents = []
    cursor = 0
    chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr())]
    for type_id, class_name, names in inst_specs:
        refs = list(range(cursor, cursor + len(names)))
        referents.extend(refs)
        cursor += len(names)
        chunks.append(_chunk("INST", _inst(type_id, class_name, refs)))
        chunks.append(_chunk("PROP", _name_prop(type_id, names),
                             compress=compress_names))
    kids = [c for c, _ in links]
    parents = [-1 if p is None else p for _, p in links]
    chunks.append(_chunk("PRNT", _prnt(kids, parents)))
    for name, body in extra_chunks:
        chunks.append(_chunk(name, body))
    chunks.append(b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>")
    return _header(len(inst_specs), len(referents)) + b"".join(chunks)


def mini_tree():
    """Zdravy strom: Model Root(0) <- Model Wheels(1) <- 4x Part FL..RR."""
    return build_model(
        [(0, "Model", ["Root", "Wheels"]),
         (1, "Part", ["FL", "FR", "RL", "RR"])],
        [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)])


def sha256_of(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class TestRbxmParser(unittest.TestCase):
    """12 povinnych pripadu C05-A/B (zadny tichy pruchod)."""

    def test_valid_rbxm_full_hierarchy(self):
        """1. Platny RBXM: 815 instanci, 37 typu, koren, census, Wheels."""
        model = parse_rbxm(WORK_COPY)
        self.assertEqual(model["num_types"], 37)
        self.assertEqual(model["num_instances"], 815)
        self.assertEqual(len(model["instances"]), 815)
        self.assertEqual([i["id"] for i in model["instances"]],
                         list(range(815)))
        self.assertEqual(model["meta"], {"ExplicitAutoJoints": "true"})
        self.assertEqual(model["chunk_census"],
                         {"META": 1, "SSTR": 1, "INST": 37, "PROP": 928,
                          "PRNT": 1, "END\x00": 1})
        roots = [i for i in model["instances"] if i["parent_id"] is None]
        self.assertEqual([i["id"] for i in roots], [0])
        by_id = {i["id"]: i for i in model["instances"]}
        for inst in model["instances"]:
            parent = inst["parent_id"]
            if parent is not None:
                self.assertIn(parent, by_id)
        wheels = [i for i in model["instances"]
                  if i["class_name"] == "Model" and i["name"] == "Wheels"]
        self.assertEqual(len(wheels), 1)
        # Vsechny instance maji jmeno; zadna geometrie (C05-C/D).
        self.assertEqual(model["missing_name_count"], 0)
        for inst in model["instances"]:
            self.assertIsNone(inst["shape"])
        self.assertEqual(model["geometry"]["status"], "BLOCKED")

    def test_corrupt_header(self):
        """2. Poskozena hlavicka (magic / signatura / verze) = odmitnout."""
        good = mini_tree()
        for pos, bad in ((0, b"X"), (8, b"\x00"), (14, b"\x01")):
            broken = good[:pos] + bad + good[pos + 1:]
            with self.assertRaises(RbxmCorruptError):
                parse_bytes(broken)
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(mini_tree()[:16])  # useknuta hlavicka

    def test_bad_chunk_length(self):
        """3. Spatna delka chunku (useknuti / prestreleny ramec) = odmitnout."""
        good = mini_tree()
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(good[:len(good) // 2])  # useknuty soubor
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(good + b"\x00")  # data za END
        # Prestrelna delka: uncomp_len vetsi nez zbytek souboru.
        broken = bytearray(good)
        struct.pack_into("<I", broken, 32 + 8, 0x7FFFFFFF)
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(bytes(broken))

    def test_corrupt_lz4(self):
        """4. Poskozena LZ4 data (useknuti / spatny offset) = odmitnout."""
        with self.assertRaises(RbxmCorruptError):
            lz4_decompress(b"\x40AB", 4)  # slibene 4 B, dodany 2
        with self.assertRaises(RbxmCorruptError):
            lz4_decompress(b"\x10A\x00\x00", 5)  # nulovy offset
        with self.assertRaises(RbxmCorruptError):
            lz4_decompress(b"\x40ABCD", 3)  # prestreleny vystup
        with self.assertRaises(RbxmCorruptError):
            lz4_decompress(b"\x40ABCDEX", 4)  # prebytecny vstup
        # Cely soubor s poskozenym komprimovanym chunkem.
        good = build_model(
            [(0, "Model", ["Root"])], [(0, None)], compress_names=True)
        broken = bytearray(good)
        broken[-20] ^= 0xFF
        try:
            parse_bytes(bytes(broken))
        except RbxmError:
            pass
        else:
            # Bit-flip mohl nahodou prezit jen u necitelnych dat;
            # garantovany pripad je useknuti komprimovaneho tela.
            prop_pos = good.find(b"PROP")
            comp_len = struct.unpack("<I", good[prop_pos + 4:prop_pos + 8])[0]
            cut = good[:prop_pos + 16 + comp_len - 1]
            with self.assertRaises(RbxmCorruptError):
                parse_bytes(cut)

    def test_unknown_type_skipped(self):
        """5. Neznamy typ: neznamy chunk i neznamy PROP typ se preskoci
        (evidovane v censu), parsovani uspeje; Name s jinym typem = chyba."""
        model = parse_bytes(build_model(
            [(0, "Model", ["Root"])], [(0, None)],
            extra_chunks=[(b"XXXX", b"\x01\x02\x03")]))
        self.assertEqual(len(model["instances"]), 1)
        self.assertIn("XXXX", model["skipped_chunks"])
        # Neznamy typ hodnoty u bezne PROP (vtype 0xFF) = preskocit, ne
        # interpretovat; geometrie zustava BLOCKED.
        weird = (_u32(0) + _string("Shape") + b"\xFF" + b"\x00" * 8)
        model2 = parse_bytes(build_model(
            [(0, "Model", ["Root"])], [(0, None)],
            extra_chunks=[("PROP", weird)]))
        self.assertEqual(model2["geometry"]["status"], "BLOCKED")
        self.assertTrue(any(p["prop_name"] == "Shape"
                            for p in model2["skipped_props"]))
        # Name s ne-retezcovym typem by zamlcela identitu = odmitnout.
        bad_name = _u32(0) + _string("Name") + b"\x02" + b"\x00" * 4
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(build_model(
                [(0, "Model", ["Root"])], [(0, None)],
                extra_chunks=[("PROP", bad_name)]))

    def test_invalid_parent(self):
        """6. Neplatny parent (mimo rozsah) = hierarchicka chyba/BLOCKED."""
        data = build_model([(0, "Model", ["Root", "Orphan"])],
                           [(0, None), (1, 999)])
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(data)

    def test_duplicate_id(self):
        """7. Duplicitni ID napric INST = poskozeny soubor."""
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", _inst(0, "Model", [0, 1])),
                  _chunk("INST", _inst(1, "Part", [1, 2])),
                  _chunk("PROP", _name_prop(0, ["A", "B"])),
                  _chunk("PROP", _name_prop(1, ["C", "D"])),
                  _chunk("PRNT", _prnt([0, 1, 2], [None, 0, 0])),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(_header(2, 3) + b"".join(chunks))

    def test_cycle(self):
        """8. Cyklus v parent retezci (A<->B) = hierarchicka chyba."""
        data = build_model([(0, "Model", ["A", "B"])], [(0, 1), (1, 0)])
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(data)

    def test_missing_wheels_model(self):
        """9. Chybejici Model:Wheels na realne kopii -> wheel BLOCKED."""
        model = parse_rbxm(WORK_COPY)
        without = [i for i in model["instances"] if i["id"] != 2]
        result = detect_wheels(without)
        self.assertTrue(is_blocked(result))
        self.assertTrue(any("missing Model:Wheels" in r
                            for r in result["blocked_reasons"]))

    def test_four_wheels_honest_partial(self):
        """10. Realna kopie: hierarchie kompletni, geometrie BLOCKED —
        zadna falesna kola (vse UNKNOWN/bad_shape), oznaceni pritomna."""
        model = parse_rbxm(WORK_COPY)
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertEqual(by_id[2]["name"], "Wheels")
        found = sorted(i["name"] for i in model["instances"]
                       if i["id"] in (3, 52, 101, 150))
        self.assertEqual(found, ["FL", "FR", "RL", "RR"])
        for iid in (3, 52, 101, 150):
            self.assertEqual(by_id[iid]["class_name"], "Part")
            self.assertIsNone(by_id[iid]["shape"])
        result = detect_wheels(model["instances"])
        self.assertTrue(is_blocked(result))
        self.assertFalse(any(w.get("status") == "WHEEL"
                             for w in result["wheels"].values()))
        recs = {r["instance_id"]: r for r in result["unidentified"]}
        for iid in (3, 52, 101, 150):
            self.assertIn("bad_shape", recs[iid]["failed_checks"])

    def test_unknown_designation(self):
        """11. Nezname oznaceni kola = UNKNOWN se zaznamem + BLOCKED."""
        model = parse_bytes(mini_tree())
        broken = [dict(i) for i in model["instances"]]
        for inst in broken:
            if inst["id"] == 2:
                inst["name"] = "FrontLeft"
        result = detect_wheels(broken)
        self.assertTrue(is_blocked(result))
        recs = {r["instance_id"]: r for r in result["unidentified"]}
        self.assertIn("bad_designation", recs[2]["failed_checks"])

    def test_hash_before_after(self):
        """12. Hash pracovni kopie pred/po + shoda s dokumentovanou hodnotou
        (parser cte pouze 'rb', nikdy nezapisuje)."""
        before = sha256_of(WORK_COPY)
        parse_rbxm(WORK_COPY)
        after = sha256_of(WORK_COPY)
        self.assertEqual(before, after)
        self.assertEqual(after, EXPECTED_SHA256)

    def test_fuzz_never_unsafe(self):
        """13. Fuzz (Agent D): nahodne mutace/trunkace realne kopie nikdy
        nezpusobi neocekavanou vyjimku ani tichy pruchod se spatnou
        strukturou — jen RbxmError, nebo platny model se stejnymi pocty
        a platnymi parenty. Mutace uvnitr retezcovych dat (\"Mesh\"->\"Me8h\")
        zustava detekovatelna jen hashem (test 12), format nema checksum."""
        import random
        with open(WORK_COPY, "rb") as handle:
            raw = handle.read()
        rng = random.Random(20261119)
        for trial in range(120):
            blob = bytearray(raw)
            for _ in range(rng.randint(1, 3)):
                blob[rng.randrange(len(blob))] = rng.randrange(256)
            try:
                model = parse_bytes(bytes(blob))
            except RbxmError:
                continue
            self.assertEqual(model["num_instances"], 815,
                             "fuzz trial %d" % trial)
            self.assertEqual(len(model["instances"]), 815)
            by_id = {i["id"] for i in model["instances"]}
            for inst in model["instances"]:
                parent = inst["parent_id"]
                if parent is not None:
                    self.assertIn(parent, by_id, "fuzz trial %d" % trial)
                self.assertIsNone(inst["shape"], "fuzz trial %d" % trial)
        for cut in (1, 32, 1000, len(raw) // 2, len(raw) - 10):
            with self.assertRaises(RbxmError):
                parse_bytes(raw[:cut])


if __name__ == "__main__":
    unittest.main()

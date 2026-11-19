"""Testy produkcniho RBXM parseru (M2, milnik C05-A/B/C/D): header, chunky,
LZ4, INST, PRNT, geometrie (shape/size/CFrame) + hardening.

Vstup: prednostne verzovana fixture
  testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm,
fallback lokalni pracovni kopie assets/chassis-original/chasis-work-copy.rbxm
(POUZE CTENI, nikdy zapis; test_hash_before_after overuje SHA-256
pred/po + shodu s dokumentovanou hodnotou). Oba soubory maji stejny
hash dc8747e0 (230421 B) — v repu je jediny distinctni model; jako
LIMIT je to vyslovne zaznamenano a druhy soubor se testuje zvlast.
Chybi-li oba soubory, testy cteni hlasi SKIP (PENDING), nikdy ERROR.
Synteticke poskozene varianty se stavi v pameti (builder nize,
raw chunky bez komprese + rucne skladane LZ4 bloky), zadny zapis na disk.

Ocekavany integracni vysledek (poctivy castecny): hierarchie se dekoduje
uplne (815 instanci, 37 typu, koren, Model:Wheels + FL/FR/RL/RR), tvary
Ball/Block/Cylinder se ctou (kola = Ball), size/CFrame strukturalne
(2.7 kostky, symetricky obdelnik stredu); wheel_detect hlasi 4x WHEEL,
ale BLOCKED (44 dilu podvozku ve strome Wheels); geometricke posouzeni
vraci stredy/rozmery, ale BLOCKED (neunavena kalibrace NOT IMPLEMENTED).
Zadne falesne geometrie z nazvu, nikdy.
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
    PART_TYPE_NAMES,
    RbxmCorruptError,
    RbxmError,
    RbxmHierarchyError,
    RbxmUnsupportedError,
    assess_wheel_geometry,
    calibrate_studs_per_meter,
    lz4_decompress,
    parse_bytes,
    parse_rbxm,
)
from src.Inspection.wheel_detect import detect_wheels, is_blocked

WORK_COPY = os.path.join(ROOT, "assets", "chassis-original",
                         "chasis-work-copy.rbxm")
JEEP_COPY = os.path.join(ROOT, "testgame", "src", "ServerStorage",
                         "VehicleTemplates", "JeepTemplate.rbxm")
# Dokumentovany hash obou praconich kopii (reports/RBXM-SPIKE.md §2).
# LIMIT: oba soubory maji stejny hash = jediny distinctni model v repu;
# treti ruzny RBXM neexistuje (overeno hashem).
EXPECTED_SHA256 = ("dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd"
                   "7c070c2c1fefdf")

# Fuzz: reprodukovatelny, pevny seed, hlaseny pocet pripadu.
FUZZ_SEED = 20261119
FUZZ_MUT_TRIALS = 200
FUZZ_TRUNC_CASES = (1, 32, 1000)

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


def _rol32(value, bits):
    """Rotace u32 vlevo (inverze k _ror1 v parseru; jen pro fixture)."""
    value &= 0xFFFFFFFF
    return ((value << bits) | (value >> (32 - bits))) & 0xFFFFFFFF


def _encode_enum(values):
    """Zakoduje enum/int PROP: 4 lane, LSB lane prvni (viz parser)."""
    count = len(values)
    lanes = [bytearray(count) for _ in range(4)]
    for i, value in enumerate(values):
        lanes[0][i] = value & 0xFF
        lanes[1][i] = (value >> 8) & 0xFF
        lanes[2][i] = (value >> 16) & 0xFF
        lanes[3][i] = (value >> 24) & 0xFF
    return b"".join(bytes(lane) for lane in lanes)


def _encode_floats_comps(comps):
    """Zakoduje 3 float slozky: component-major, MSB lane prvni, rol1."""
    count = len(comps[0])
    out = bytearray()
    for comp in comps:
        words = []
        for value in comp:
            bits = struct.unpack("<I", struct.pack("<f", value))[0]
            words.append(_rol32(bits, 1))
        for lane in range(4):
            shift = 24 - 8 * lane
            out += bytes((word >> shift) & 0xFF for word in words)
    return bytes(out)


def _geom_prop(type_id, prop_name, value_type, payload):
    """Telo PROP chunku pro geometrickou vlastnost (synteticke fixture)."""
    return (_u32(type_id & 0xFFFFFFFF) + _string(prop_name)
            + bytes((value_type,)) + payload)


def _shape_prop(type_id, values):
    return _geom_prop(type_id, "shape", 0x12, _encode_enum(values))


def _size_prop(type_id, triples):
    comps = [[t[d] for t in triples] for d in range(3)]
    return _geom_prop(type_id, "size", 0x0E, _encode_floats_comps(comps))


def _cframe_prop(type_id, prop_name, positions, orient_ids, matrices):
    """CFrame PROP: orientacni bloky + pozicni lane (viz parser).

    orient_ids: list u8 (0 = vlastni matice, 2 = identita, jine = preseta);
    matrices: list 9-tic (jen pro id 0, jinak None).
    """
    blocks = bytearray()
    for oid, mat in zip(orient_ids, matrices):
        blocks.append(oid)
        if oid == 0:
            blocks += struct.pack("<9f", *mat)
    comps = [[p[d] for p in positions] for d in range(3)]
    return _geom_prop(type_id, prop_name, 0x10,
                       bytes(blocks) + _encode_floats_comps(comps))


def build_model(inst_specs, links, extra_chunks=(), compress_names=False,
                ref_lists=None):
    """Minimalni platny RBXM v pameti.

    inst_specs: [(type_id, class_name, [jmena...])] v poradi referentu;
    links: [(child, parent)] (parent None = koren).
    ref_lists: volitelne explicitni referenty [[r...], ...] pro kazdy typ
      (nesouvisle referenty pro test A); jinak souvisle od 0.
    """
    referents = []
    cursor = 0
    chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr())]
    for idx, (type_id, class_name, names) in enumerate(inst_specs):
        if ref_lists is not None:
            refs = list(ref_lists[idx])
            assert len(refs) == len(names), "ref_lists/names mismatch"
        else:
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


def _require_real_copy(testcase) -> str:
    """Realny RBXM model pro cteni: prednostne verzovany JeepTemplate
    (funguje i na CI), fallback lokalni pracovni kopie; chybi-li oba,
    SKIP s duvodem (PENDING), nikdy ERROR/FileNotFoundError."""
    for path in (JEEP_COPY, WORK_COPY):
        if os.path.exists(path):
            return path
    testcase.skipTest(
        "PENDING: realny RBXM model neni v tomto prostredi k dispozici "
        "(chybi JeepTemplate i pracovni kopie) — cteni neni mozne overit")
    raise AssertionError("nedosazitelne: skipTest vzdy vyhazuje SkipTest")


class TestRbxmParser(unittest.TestCase):
    """12 povinnych pripadu C05-A/B (zadny tichy pruchod)."""

    def test_valid_rbxm_full_hierarchy(self):
        """1. Platny RBXM: 815 instanci, 37 typu, koren, census, Wheels."""
        model = parse_rbxm(_require_real_copy(self))
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
        # Vsechny instance maji jmeno; geometrie PARTIAL s provenienci.
        self.assertEqual(model["missing_name_count"], 0)
        self.assertEqual(model["unnamed_ids"], [])
        self.assertEqual(model["geometry"]["status"], "PARTIAL")
        self.assertEqual(model["geometry"]["calibration"]["status"],
                         "NOT_IMPLEMENTED")
        for name in ("shape", "size", "CFrame"):
            # Model:Wheels nema vlastni geometrii — zadny zaznam, ne odhad.
            self.assertNotIn(name, by_id[2]["props"])
        self.assertEqual(by_id[3]["props"]["shape"],
                         {"status": "read", "trusted": True,
                          "how": ("PROP shape enum u32 lane LSB-prvni; "
                                  "mapovano PartType Ball/Block/Cylinder"),
                          "value": "Ball"})

    def test_corrupt_header(self):
        """2. Poskozena hlavicka (magic / signatura) = odmitnout;
        jina verze = nepodporovano (rozliseni poskozeny/nepodporovany)."""
        good = mini_tree()
        for pos, bad in ((0, b"X"), (8, b"\x00")):
            broken = good[:pos] + bad + good[pos + 1:]
            with self.assertRaises(RbxmCorruptError):
                parse_bytes(broken)
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(mini_tree()[:16])  # useknuta hlavicka
        broken = good[:14] + b"\x01" + good[15:]
        with self.assertRaises(RbxmUnsupportedError):
            parse_bytes(broken)

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
        # interpretovat; geometrie zustava PARTIAL, zaznam ma status unread.
        weird = (_u32(0) + _string("Shape") + b"\xFF" + b"\x00" * 8)
        model2 = parse_bytes(build_model(
            [(0, "Model", ["Root"])], [(0, None)],
            extra_chunks=[("PROP", weird)]))
        self.assertEqual(model2["geometry"]["status"], "PARTIAL")
        shape_skipped = [p for p in model2["skipped_props"]
                         if p["prop_name"] == "Shape"]
        self.assertTrue(shape_skipped)
        for entry in shape_skipped:
            self.assertEqual(entry["status"], "unread")
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
        model = parse_rbxm(_require_real_copy(self))
        without = [i for i in model["instances"] if i["id"] != 2]
        result = detect_wheels(without)
        self.assertTrue(is_blocked(result))
        self.assertTrue(any("missing Model:Wheels" in r
                            for r in result["blocked_reasons"]))

    def test_four_wheels_honest_partial(self):
        """10. Realna kopie: hierarchie kompletni, tvary Ball (kola),
        size/CFrame strukturalne; wheel_detect 4x WHEEL, ale BLOCKED
        (44 dilu podvozku ve strome Wheels); geometrie se nikdy
        neodvozuje z nazvu (jen z PROP)."""
        model = parse_rbxm(_require_real_copy(self))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertEqual(by_id[2]["name"], "Wheels")
        found = sorted(i["name"] for i in model["instances"]
                       if i["id"] in (3, 52, 101, 150))
        self.assertEqual(found, ["FL", "FR", "RL", "RR"])
        for iid in (3, 52, 101, 150):
            self.assertEqual(by_id[iid]["class_name"], "Part")
            self.assertEqual(by_id[iid]["shape"], "Ball")
            size = by_id[iid]["size"]
            self.assertTrue(all(abs(v - 2.7) < 1e-4 for v in size))
            self.assertEqual(by_id[iid]["props"]["size"]["status"], "read")
            self.assertFalse(by_id[iid]["props"]["size"]["trusted"])
            self.assertEqual(by_id[iid]["props"]["CFrame"]["status"],
                             "read")
        # Stredy kol: symetricky obdelnik (rozvor x rozchod), stejne Y.
        pos = {iid: by_id[iid]["position"] for iid in (3, 52, 101, 150)}
        xs = sorted(p[0] for p in pos.values())
        zs = sorted(p[2] for p in pos.values())
        self.assertEqual(len(set(round(v, 2) for v in xs)), 2)
        self.assertEqual(len(set(round(v, 2) for v in zs)), 2)
        self.assertTrue(max(p[1] for p in pos.values())
                        - min(p[1] for p in pos.values()) < 0.05)
        result = detect_wheels(model["instances"])
        self.assertTrue(is_blocked(result))
        self.assertTrue(all(w["status"] == "WHEEL"
                            for w in result["wheels"].values()))
        self.assertTrue(any("UNKNOWN candidate(s) inside Model:Wheels" in r
                            for r in result["blocked_reasons"]))
        # Geometricke posouzeni: 4x GEOMETRY_OK se stredy/rozmery, ale
        # BLOCKED (neoverena kalibrace + UNKNOWN dilci ve strome Wheels).
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        for des in ("FL", "FR", "RL", "RR"):
            self.assertEqual(geo["wheels"][des]["status"], "GEOMETRY_OK")
        self.assertEqual(geo["calibration"]["status"], "NOT_IMPLEMENTED")
        self.assertTrue(
            any("float_decode_unverified" in r
                for r in geo["blocked_reasons"]))

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
        real = _require_real_copy(self)
        before = sha256_of(real)
        parse_rbxm(real)
        after = sha256_of(real)
        self.assertEqual(before, after)
        self.assertEqual(after, EXPECTED_SHA256)

    def test_second_file_same_model(self):
        """12b. Druhy soubor (JeepTemplate.rbxm): stejny hash = LIMIT
        (jediny distinctni model v repu), parsuje se identicky, cteni
        nemeni hash."""
        self.assertTrue(os.path.exists(JEEP_COPY))
        before = sha256_of(JEEP_COPY)
        self.assertEqual(before, EXPECTED_SHA256)  # LIMIT: stejny model
        model = parse_rbxm(JEEP_COPY)
        after = sha256_of(JEEP_COPY)
        self.assertEqual(before, after)
        self.assertEqual(model["num_types"], 37)
        self.assertEqual(model["num_instances"], 815)
        self.assertEqual(len(model["instances"]), 815)
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertEqual(by_id[2]["name"], "Wheels")
        for iid in (3, 52, 101, 150):
            self.assertEqual(by_id[iid]["shape"], "Ball")

    def test_fuzz_never_unsafe(self):
        """13. Fuzz: nahodne mutace/trunkace realne kopie nikdy
        nezpusobi neocekavanou vyjimku ani tichy pruchod se spatnou
        strukturou — jen RbxmError, nebo platny model se stejnymi pocty,
        platnymi parenty a tvary ze zname mnoziny. Reprodukovatelne:
        seed FUZZ_SEED, FUZZ_MUT_TRIALS mutaci + trunkace.
        Mutace uvnitr retezcovych dat ("Mesh"->"Me8h") zustava
        detekovatelna jen hashem (test 12), format nema checksum."""
        import random
        real = _require_real_copy(self)
        with open(real, "rb") as handle:
            raw = handle.read()
        rng = random.Random(FUZZ_SEED)
        accepted = 0
        for trial in range(FUZZ_MUT_TRIALS):
            blob = bytearray(raw)
            for _ in range(rng.randint(1, 3)):
                blob[rng.randrange(len(blob))] = rng.randrange(256)
            try:
                model = parse_bytes(bytes(blob))
            except RbxmError:
                continue
            accepted += 1
            self.assertEqual(model["num_instances"], 815,
                             "fuzz trial %d" % trial)
            self.assertEqual(len(model["instances"]), 815)
            by_id = {i["id"] for i in model["instances"]}
            for inst in model["instances"]:
                parent = inst["parent_id"]
                if parent is not None:
                    self.assertIn(parent, by_id, "fuzz trial %d" % trial)
                self.assertTrue(
                    inst["shape"] is None
                    or inst["shape"] in PART_TYPE_NAMES.values(),
                    "fuzz trial %d" % trial)
        for cut in FUZZ_TRUNC_CASES + (len(raw) // 2, len(raw) - 10):
            with self.assertRaises(RbxmError):
                parse_bytes(raw[:cut])

    def test_noncontiguous_referents(self):
        """A1. Nesouvisle referenty: mapovani skutecny referent->instance,
        PRNT jen na existujici, zadny predpoklad souvislosti."""
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL"])],
            [(5, None), (7, 5), (9, 7)],
            ref_lists=[[5, 7], [9]]))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertEqual(sorted(by_id), [5, 7, 9])
        self.assertIsNone(by_id[5]["parent_id"])
        self.assertEqual(by_id[7]["parent_id"], 5)
        self.assertEqual(by_id[9]["parent_id"], 7)
        self.assertEqual(by_id[7]["name"], "Wheels")

    def test_prnt_subset_rejected(self):
        """A2. PRNT dite mimo referenty INST (i kdyz v rozsahu) = chyba;
        duplicitni dite v PRNT = poskozeny soubor."""
        # Dite 99 neni v INST (referenty jen 0, 1) — mnozina deti
        # neodpovida mnozine referentu: odmitnout.
        data = build_model([(0, "Model", ["Root", "Orphan"])],
                           [(0, None), (99, 0)])
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(data)
        # Duplicitni dite: kids [0, 0] — mnozina nesedi.
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", _inst(0, "Model", [0, 1])),
                  _chunk("PROP", _name_prop(0, ["A", "B"])),
                  _chunk("PRNT", _prnt([0, 0], [None, 0])),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(_header(1, 2) + b"".join(chunks))

    def test_limits_refused_before_alloc(self):
        """B. Limity: soubor nad MAX_FILE_BYTES a chunk nad
        MAX_TOTAL_UNCOMPRESSED se odmitnou pred alokaci."""
        tiny = mini_tree()
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(tiny + b"\x00" * (8 * 1024 * 1024))
        # Obri uncomp_len v hlavicce chunku: odmitnuti bez dekomprese.
        broken = bytearray(mini_tree())
        struct.pack_into("<I", broken, 32 + 8, 300 * 1024 * 1024)
        with self.assertRaises(RbxmError):
            parse_bytes(bytes(broken))

    def test_meta_duplicate_key(self):
        """C1. Duplicitni META klic = poskozeny soubor."""
        body = (_u32(2) + _string("A") + _string("1")
                + _string("A") + _string("2"))
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(build_model(
                [(0, "Model", ["Root"])], [(0, None)],
                extra_chunks=[("META", body)]))

    def test_sstr_shared_unsupported(self):
        """C2. Neprazdna SSTR tabulka = nepodporovano (ne poskozeno)."""
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _u32(1)),
                  _chunk("INST", _inst(0, "Model", [0])),
                  _chunk("PROP", _name_prop(0, ["Root"])),
                  _chunk("PRNT", _prnt([0], [None])),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmUnsupportedError):
            parse_bytes(_header(1, 1) + b"".join(chunks))

    def test_inst_validation(self):
        """C3. Duplicitni INST typ, is_service mimo 0/1, PROP pro neznamy
        typ a duplicitni geometricky PROP = poskozeny soubor."""
        good = build_model([(0, "Model", ["Root"])], [(0, None)])
        # Duplicitni INST typ: pridat druhy INST se stejnym type_id.
        dup = (_u32(0) + _string("Model") + b"\x00" + _u32(1)
               + _encode_referents([5]))
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", _inst(0, "Model", [0])),
                  _chunk("INST", dup),
                  _chunk("PROP", _name_prop(0, ["Root"])),
                  _chunk("PRNT", _prnt([0], [None])),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(_header(2, 2) + b"".join(chunks))
        # is_service = 2.
        bad_svc = (_u32(0) + _string("Model") + b"\x02" + _u32(1)
                   + _encode_referents([0]))
        chunks2 = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                   _chunk("INST", bad_svc),
                   _chunk("PROP", _name_prop(0, ["Root"])),
                   _chunk("PRNT", _prnt([0], [None])),
                   b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                   + b"</roblox>"]
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(_header(1, 1) + b"".join(chunks2))
        # PROP pro neznamy typ.
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(build_model(
                [(0, "Model", ["Root"])], [(0, None)],
                extra_chunks=[("PROP", _name_prop(7, ["X"]))]))
        # Duplicitni geometricky PROP.
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(build_model(
                [(0, "Model", ["Root"])], [(0, None)],
                extra_chunks=[("PROP", _shape_prop(0, [1])),
                              ("PROP", _shape_prop(0, [1]))]))
        self.assertTrue(good)  # zakladni builder porad plati

    def test_prnt_version_unsupported(self):
        """C4. PRNT verze != 0 = nepodporovano (ne poskozeno)."""
        body = b"\x01" + _prnt([0], [None])[1:]
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", _inst(0, "Model", [0])),
                  _chunk("PROP", _name_prop(0, ["Root"])),
                  _chunk("PRNT", body),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmUnsupportedError):
            parse_bytes(_header(1, 1) + b"".join(chunks))

    def test_missing_name_is_not_recognized(self):
        """C5. Chybejici Name PROP: name None + name_status missing;
        takova instance neni rozpoznany objekt (assess -> BLOCKED)."""
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", _inst(0, "Model", [0, 1])),
                  _chunk("PROP", _name_prop(0, ["Wheels"])),
                  _chunk("PRNT", _prnt([0, 1], [None, 0])),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        # Name PROP ma jen 1 jmeno pro 2 instance -> Corrupt (pocet musi
        # sedet); chybejici cela Name PROP -> name None.
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(_header(1, 2) + b"".join(chunks))
        chunks2 = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                   _chunk("INST", _inst(0, "Model", [0])),
                   _chunk("PRNT", _prnt([0], [None])),
                   b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                   + b"</roblox>"]
        model = parse_bytes(_header(1, 1) + b"".join(chunks2))
        self.assertIsNone(model["instances"][0]["name"])
        self.assertEqual(model["instances"][0]["name_status"], "missing")
        self.assertEqual(model["missing_name_count"], 1)
        self.assertEqual(model["unnamed_ids"], [0])

    def test_geometry_roundtrip_synthetic(self):
        """D. Synteticky shape/size/CFrame: kodovani tam a zpet presne;
        provenience u kazde vlastnosti."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR"])],
            [(0, None), (1, 0), (2, 1), (3, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0])),
                ("PROP", _size_prop(1, [(2.7, 2.7, 2.7),
                                        (2.7, 2.7, 2.7)])),
                ("PROP", _cframe_prop(1, "CFrame", [(1.0, 2.0, 3.0),
                                                    (4.0, 5.0, 6.0)],
                                       [0, 0], [ident, ident])),
            ]))
        by_id = {i["id"]: i for i in model["instances"]}
        for iid in (2, 3):
            inst = by_id[iid]
            self.assertEqual(inst["shape"], "Ball")
            self.assertTrue(all(abs(v - 2.7) < 1e-6 for v in inst["size"]))
            self.assertEqual(inst["props"]["shape"]["status"], "read")
            self.assertTrue(inst["props"]["shape"]["trusted"])
            self.assertFalse(inst["props"]["size"]["trusted"])
            self.assertEqual(inst["props"]["CFrame"]["status"], "read")
            self.assertEqual(inst["props"]["CFrame"]["rotation_status"],
                             "matrix")
        self.assertEqual(by_id[2]["position"], (1.0, 2.0, 3.0))
        self.assertEqual(by_id[2]["rotation"], ident)

    def test_cframe_unknown_preset_unread(self):
        """D2. CFrame s neoverenou presetou: pozice prectena, orientace
        unread (provenience), soubor neni odmitnut."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        model = parse_bytes(build_model(
            [(0, "Part", ["P"])], [(0, None)],
            extra_chunks=[
                ("PROP", _cframe_prop(0, "CFrame", [(1.0, 2.0, 3.0)],
                                       [7], [None])),
            ]))
        inst = model["instances"][0]
        self.assertEqual(inst["position"], (1.0, 2.0, 3.0))
        self.assertIsNone(inst["rotation"])
        self.assertEqual(inst["props"]["CFrame"]["rotation_status"],
                         "unread-preset-7")
        self.assertTrue(ident)  # fixture pomocna, matice se nepouzila

    def test_assess_consistent_geometry_blocked_only_by_calibration(self):
        """E1. Synteticka konzistentni 4 kola: GEOMETRY_OK + jediny duvod
        BLOCKED je neoverena kalibrace."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                ("PROP", _cframe_prop(1, "CFrame",
                                       [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                                        (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                                       [0, 0, 0, 0], [ident] * 4)),
            ]))
        geo = assess_wheel_geometry(model["instances"])
        for des in ("FL", "FR", "RL", "RR"):
            self.assertEqual(geo["wheels"][des]["status"], "GEOMETRY_OK")
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertEqual(len(geo["blocked_reasons"]), 1)
        self.assertIn("float_decode_unverified", geo["blocked_reasons"][0])
        self.assertEqual(geo["calibration"]["status"], "NOT_IMPLEMENTED")

    def test_assess_asymmetric_layout_blocked(self):
        """E2. Asymetricke rozmisteni stredu (ne-obdelnik) = BLOCKED
        s duvodem layoutu, ne tichy pruchod."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                ("PROP", _size_prop(1, [(2.0, 2.0, 2.0)] * 4)),
                ("PROP", _cframe_prop(1, "CFrame",
                                       [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                                        (2.0, 0.0, 0.0), (3.0, 0.0, 0.0)],
                                       [0, 0, 0, 0], [ident] * 4)),
            ]))
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertTrue(any("rectangular" in r
                            for r in geo["blocked_reasons"]))

    def test_assess_missing_geometry_blocked(self):
        """E3. Kolo bez geometrie (zadny shape/size/CFrame PROP):
        bad_shape/missing_* + BLOCKED; jmeno samotne nestaci."""
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)]))
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertIn("bad_shape", geo["wheels"]["FL"]["failed_checks"])
        self.assertIn("missing_size", geo["wheels"]["FL"]["failed_checks"])
        self.assertIn("missing_position",
                      geo["wheels"]["FL"]["failed_checks"])

    def test_adversarial_swapped_lanes_blocked(self):
        """E4. Adversarial: prohozene float lane (LSB prvni misto MSB) jsou
        strukturalne validni, ale hodnoty se zmeni (ne ticha geometrie);
        trusted zustava False a assess zustava BLOCKED (kalibrace)."""
        count = 4
        triples = [(2.7, 2.7, 2.7)] * count
        comps = [[t[d] for t in triples] for d in range(3)]
        out = bytearray()
        for comp in comps:
            words = []
            for value in comp:
                bits = struct.unpack("<I", struct.pack("<f", value))[0]
                words.append(_rol32(bits, 1))
            for lane in range(4):  # PROHOZENO: LSB lane prvni
                shift = 8 * lane
                out += bytes((word >> shift) & 0xFF for word in words)
        swapped = _geom_prop(1, "size", 0x0E, bytes(out))
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                ("PROP", swapped),
                ("PROP", _cframe_prop(1, "CFrame",
                                       [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                                        (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                                       [0, 0, 0, 0], [ident] * 4)),
            ]))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertNotEqual(by_id[2]["size"], (2.7, 2.7, 2.7))
        self.assertFalse(by_id[2]["props"]["size"]["trusted"])
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertNotEqual(geo["status"], "OK")
        self.assertTrue(any("float_decode_unverified" in r
                            for r in geo["blocked_reasons"]))

    def test_adversarial_unknown_shape_unread(self):
        """E5. Adversarial: neznama hodnota shape enum (9) u kola = tvar
        unread (None, zadny odhad), kolo UNKNOWN s bad_shape, BLOCKED."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [9, 0, 0, 0])),
                ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                ("PROP", _cframe_prop(1, "CFrame",
                                       [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                                        (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                                       [0, 0, 0, 0], [ident] * 4)),
            ]))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertIsNone(by_id[2]["shape"])
        self.assertEqual(by_id[2]["props"]["shape"]["status"], "unread")
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
        self.assertIn("bad_shape", geo["wheels"]["FL"]["failed_checks"])

    def test_calibration_not_implemented(self):
        """F. Kalibrace studs/m: pripraveno rozhrani, vzdy NOT
        IMPLEMENTED (chybi Studio ground-truth) — neprohlasuje se
        za overenou."""
        cal = calibrate_studs_per_meter()
        self.assertEqual(cal["status"], "NOT_IMPLEMENTED")
        self.assertIsNone(cal["studs_per_meter"])
        cal2 = calibrate_studs_per_meter(known_meters=2.0,
                                         measured_studs=7.0)
        self.assertEqual(cal2["status"], "NOT_IMPLEMENTED")
        self.assertIsNone(cal2["studs_per_meter"])
        self.assertTrue(cal2["inputs_ignored"])


    def test_assess_inf_size_blocked(self):
        """B1-P0: +Inf size nesmi projit jako GEOMETRY_OK (drive prosel)."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        inf = float("inf")
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                ("PROP", _size_prop(1, [(inf, inf, inf),
                                        (2.7, 2.7, 2.7),
                                        (2.7, 2.7, 2.7),
                                        (2.7, 2.7, 2.7)])),
                ("PROP", _cframe_prop(1, "CFrame",
                                       [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                                        (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                                       [0, 0, 0, 0], [ident] * 4)),
            ]))
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
        self.assertIn("nonfinite_size",
                      geo["wheels"]["FL"]["failed_checks"])

    def test_assess_nan_size_label(self):
        """B1-P2: NaN size ma vlastni label, ne matouci nonpositive_size."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        nan = float("nan")
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                ("PROP", _size_prop(1, [(nan, 2.7, 2.7),
                                        (2.7, 2.7, 2.7),
                                        (2.7, 2.7, 2.7),
                                        (2.7, 2.7, 2.7)])),
                ("PROP", _cframe_prop(1, "CFrame",
                                       [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                                        (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                                       [0, 0, 0, 0], [ident] * 4)),
            ]))
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
        self.assertIn("nonfinite_size",
                      geo["wheels"]["FL"]["failed_checks"])
        self.assertNotIn("nonpositive_size",
                         geo["wheels"]["FL"]["failed_checks"])

    def test_assess_inf_nan_position_blocked(self):
        """B1-P0: +Inf/NaN pozice nikdy GEOMETRY_OK (drive prosla)."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        for bad in (float("inf"), float("nan")):
            model = parse_bytes(build_model(
                [(0, "Model", ["Root", "Wheels"]),
                 (1, "Part", ["FL", "FR", "RL", "RR"])],
                [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
                extra_chunks=[
                    ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                    ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                    ("PROP", _cframe_prop(
                        1, "CFrame",
                        [(bad, 1.0, 0.0), (6.0, 1.0, 0.0),
                         (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                        [0, 0, 0, 0], [ident] * 4)),
                ]))
            geo = assess_wheel_geometry(model["instances"])
            self.assertEqual(geo["status"], "BLOCKED", "bad=%r" % (bad,))
            self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
            self.assertIn("nonfinite_position",
                          geo["wheels"]["FL"]["failed_checks"])

    def test_assess_invalid_rotation_blocked(self):
        """B1-P1: skalujici/prevracena matice neni rotace -> BLOCKED."""
        positions = [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                     (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)]
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        for bad_mat in ((2.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 2.0),
                        (-1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)):
            model = parse_bytes(build_model(
                [(0, "Model", ["Root", "Wheels"]),
                 (1, "Part", ["FL", "FR", "RL", "RR"])],
                [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
                extra_chunks=[
                    ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                    ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                    ("PROP", _cframe_prop(1, "CFrame", positions,
                                           [0, 0, 0, 0],
                                           [bad_mat, ident, ident, ident])),
                ]))
            geo = assess_wheel_geometry(model["instances"])
            self.assertEqual(geo["status"], "BLOCKED")
            self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
            self.assertIn("invalid_rotation",
                          geo["wheels"]["FL"]["failed_checks"])
            for des in ("FR", "RL", "RR"):
                self.assertEqual(geo["wheels"][des]["status"],
                                 "GEOMETRY_OK")

    def test_assess_nonfinite_rotation_blocked(self):
        """B1-P0: Inf/NaN v matici -> BLOCKED, nikdy GEOMETRY_OK."""
        positions = [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                     (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)]
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        for bad_val in (float("inf"), float("nan")):
            bad_mat = (bad_val, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
            model = parse_bytes(build_model(
                [(0, "Model", ["Root", "Wheels"]),
                 (1, "Part", ["FL", "FR", "RL", "RR"])],
                [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
                extra_chunks=[
                    ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                    ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                    ("PROP", _cframe_prop(1, "CFrame", positions,
                                           [0, 0, 0, 0],
                                           [bad_mat, ident, ident, ident])),
                ]))
            geo = assess_wheel_geometry(model["instances"])
            self.assertEqual(geo["status"], "BLOCKED")
            self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
            self.assertIn("nonfinite_rotation",
                          geo["wheels"]["FL"]["failed_checks"])

    def test_assess_unread_rotation_blocked(self):
        """B1-P1: kolo s neoverenou CFrame presetou (bez matice) neni
        geometricky OK — orientace se neodhaduje."""
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                ("PROP", _cframe_prop(
                    1, "CFrame",
                    [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                     (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                    [7, 0, 0, 0],
                    [None, (1.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                            0.0, 0.0, 1.0),
                     (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
                     (1.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                      0.0, 0.0, 1.0)])),
            ]))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertIsNone(by_id[2]["rotation"])
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN")
        self.assertIn("unread_rotation",
                      geo["wheels"]["FL"]["failed_checks"])

    def test_forest_two_roots_rejected(self):
        """B1-F2: les o 2 korenech -> hierarchicka chyba pri parsovani
        a BLOCKED v assess (politika roots != 1)."""
        data = build_model([(0, "Model", ["RootA", "RootB"])],
                           [(0, None), (1, None)])
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(data)
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)]))
        instances = [dict(i) for i in model["instances"]]
        instances.append({"id": 99, "class_name": "Model", "name": "Other",
                          "shape": None, "size": None, "position": None,
                          "rotation": None, "props": {}, "parent_id": None})
        geo = assess_wheel_geometry(instances)
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertTrue(any("forest" in r
                            for r in geo["blocked_reasons"]))

    def test_self_loop_rejected(self):
        """B1-F3a: self-parent [(0,0)] je cyklus delky 1 -> chyba."""
        data = build_model([(0, "Model", ["A"])], [(0, 0)])
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(data)


class TestParserLimitsPerformance(unittest.TestCase):
    """B2: regresni testy P1/P2 limitu a vykonu (bez zmeny chovani na
    validnich datech — viz test_valid_rbxm_full_hierarchy vyse)."""

    def test_b2_len_before_bytes(self):
        """P1-1: bytearray/memoryview nad limitem se odmitne; validni
        bytearray/memoryview se parsuje stejne jako bytes."""
        import time
        from src.Inspection.rbxm_parser import MAX_FILE_BYTES
        big = bytearray(MAX_FILE_BYTES + 1)
        t0 = time.perf_counter()
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(big)
        self.assertLess(time.perf_counter() - t0, 5.0)
        good = mini_tree()
        for view in (bytearray(good), memoryview(good)):
            model = parse_bytes(view)
            self.assertEqual(model["num_instances"], 6)

    def test_b2_input_type_check(self):
        """P2-6: str/None/int se odmitnou jako RbxmCorruptError
        (zadny unik TypeError mimo RbxmError)."""
        for bad in ("<roblox!", None, 123, 4.5, [1, 2]):
            with self.assertRaises(RbxmCorruptError):
                parse_bytes(bad)

    def test_b2_parse_rbxm_read_cap(self):
        """P1-2: parse_rbxm odmítne soubor nad limitem (read s cap)."""
        import tempfile
        from src.Inspection.rbxm_parser import MAX_FILE_BYTES
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"\x00" * (MAX_FILE_BYTES + 16))
            path = tmp.name
        try:
            with self.assertRaises(RbxmCorruptError):
                parse_rbxm(path)
        finally:
            os.unlink(path)
        # Validni soubor porad projde a hash se nemeni.
        real = _require_real_copy(self)
        before = sha256_of(real)
        model = parse_rbxm(real)
        self.assertEqual(model["num_instances"], 815)
        self.assertEqual(sha256_of(real), before)

    def test_b2_lz4_block_copy_fast_and_exact(self):
        """P1-3: offset=1 expanze na 1 MiB je rychla (< 2 s) a bitove
        presna (opakuje posledni bajt)."""
        import time
        need = 1024 * 1024 - 2 - 19
        extents = bytearray()
        while True:
            if need > 255:
                extents.append(255)
                need -= 255
            elif need == 255:
                extents += bytes((255, 0))
                break
            else:
                extents.append(need)
                break
        block = b"\x2F" + b"AB" + bytes((1, 0)) + bytes(extents)
        t0 = time.perf_counter()
        out = lz4_decompress(block, 1024 * 1024)
        self.assertLess(time.perf_counter() - t0, 2.0)
        self.assertEqual(out, b"AB" + b"B" * (1024 * 1024 - 2))

    def test_b2_field_value_cap(self):
        """P1-4: per-pole cap (100k) odmitne obri lane/INST/PRNT/Name
        driv, nez se postavi Python seznamy (< 1 s misto desitek s)."""
        import time
        from src.Inspection.rbxm_parser import (
            MAX_FIELD_VALUES, _decode_enum_lanes, _decode_float_lanes,
            _decode_referents)
        over = MAX_FIELD_VALUES + 1
        t0 = time.perf_counter()
        with self.assertRaises(RbxmCorruptError):
            _decode_float_lanes(b"\x00" * (12 * over), over, "probe")
        with self.assertRaises(RbxmCorruptError):
            _decode_referents(b"\x00" * (4 * over), over, "probe")
        with self.assertRaises(RbxmCorruptError):
            _decode_enum_lanes(b"\x00" * (4 * over), over, "probe")
        self.assertLess(time.perf_counter() - t0, 1.0)
        # Cap je nad realnou kopii: 815 instanci porad projde.
        model = parse_rbxm(_require_real_copy(self))
        self.assertEqual(model["num_instances"], 815)
        # Obri INST count v tele se odmitne take pred dekodovanim.
        hdr = (_u32(0) + _string("Part") + b"\x00"
               + _u32(over) + b"\x00" * (4 * over))
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", hdr),
                  _chunk("PROP", _name_prop(0, ["X"] * 0)),
                  _chunk("PRNT", _prnt([], [])),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmError):
            parse_bytes(_header(1, over) + b"".join(chunks))

    def test_b2_ref_to_type_correct(self):
        """P1-5: mapovani ref->type je spravne i pri mnoha typech
        (100 typu x 20 instanci < 5 s, shoda trida/jmeno/pozice)."""
        import time
        specs = [(t, "Part", ["N%d_%d" % (t, k) for k in range(20)])
                 for t in range(100)]
        refs, links = [], []
        cursor = 0
        for t in range(100):
            refs.append(list(range(cursor, cursor + 20)))
            cursor += 20
        links = [(0, None)] + [(r, 0) for r in range(1, 2000)]
        t0 = time.perf_counter()
        model = parse_bytes(build_model(specs, links, ref_lists=refs))
        self.assertLess(time.perf_counter() - t0, 5.0)
        self.assertEqual(len(model["instances"]), 2000)
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertEqual(by_id[1999]["name"], "N99_19")
        self.assertEqual(by_id[1999]["class_name"], "Part")

    def test_b2_assess_deep_chain_fast(self):
        """P2-7: linearni retez 3000 Partu pod Wheels se posoudi rychle
        (< 5 s) se stejnym vysledkem jako pri kratkem retezu."""
        import time
        depth = 3000
        insts = [{"id": 0, "class_name": "Model", "name": "Root",
                   "shape": None, "size": None, "position": None,
                   "rotation": None, "props": {}, "parent_id": None},
                  {"id": 1, "class_name": "Model", "name": "Wheels",
                   "shape": None, "size": None, "position": None,
                   "rotation": None, "props": {}, "parent_id": 0}]
        for i in range(2, depth):
            insts.append({"id": i, "class_name": "Part",
                          "name": "P%d" % i, "shape": None,
                          "size": None, "position": None,
                          "rotation": None, "props": {},
                          "parent_id": i - 1})
        t0 = time.perf_counter()
        result = assess_wheel_geometry(insts)
        self.assertLess(time.perf_counter() - t0, 5.0)
        # Bez kol FL..RR: chybejici kola + BLOCKED (stejne jako pred B2).
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["wheels"]["FL"]["status"], "UNKNOWN")


class TestFuzzF1F8(unittest.TestCase):
    """Faze C: strukturalni + hranicni fuzz dle AUDIT-test-baseline §5
    (F1-F8, seed-rodina 20261119; kazdy test konci aserci invariantu
    z praveho sloupce planu, nikdy jen 'nespadl')."""

    def test_f1_inst_structural(self):
        """F1 (3 mutace + presnost): useknuty referent-seznam, count!=payload,
        prazdny INST s nenulovym poctem, duplicitni referent —
        vzdy RbxmCorruptError, nikdy tichy model se spatnymi pocty."""
        cases = 0
        # count=2, lane-bajty jen pro 1 referent.
        bad_lanes = (_u32(0) + _string("Part") + b"\x00" + _u32(2)
                     + _encode_referents([7]))
        # count=3, zadne lane-bajty.
        bad_empty = _u32(0) + _string("Part") + b"\x00" + _u32(3)
        # Duplicitni referent v jednom INST.
        bad_dup = _inst(0, "Part", [5, 5])
        for bad in (bad_lanes, bad_empty, bad_dup):
            chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                      _chunk("INST", bad),
                      _chunk("PROP", _name_prop(0, ["A", "B"])),
                      _chunk("PRNT", _prnt([5, 6], [None, 5])),
                      b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                      + b"</roblox>"]
            with self.assertRaises(RbxmCorruptError):
                parse_bytes(_header(1, 2) + b"".join(chunks))
            cases += 1
        # Presnost: platny 2-referentovy INST projde s presnymi pocty
        # a kazdy parent je v mnozine id.
        model = parse_bytes(build_model(
            [(0, "Part", ["A", "B"])], [(0, None), (1, 0)]))
        self.assertEqual(len(model["instances"]),
                         model["num_instances"])
        by_id = {i["id"] for i in model["instances"]}
        for inst in model["instances"]:
            if inst["parent_id"] is not None:
                self.assertIn(inst["parent_id"], by_id)
        self.assertEqual(cases, 3)  # 3 strukturalni mutace INST

    def test_f2_prnt_structural(self):
        """F2 (3 pripady): parent ve zdravem rozsahu, ale mimo referenty
        INST (mezera) = RbxmHierarchyError; PRNT count!=payload =
        RbxmCorruptError; nikdy tichy model s visicim parentem."""
        # Referenty [0, 1]; parent 5 je v rozsahu hlavicky (2 instance),
        # ale neni to znamy referent.
        data = build_model([(0, "Model", ["Root", "Kid"])],
                           [(0, None), (1, 5)],
                           ref_lists=[[0, 1]])
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(data)
        # PRNT: deklarovan count=2, payload jen pro 1 dite+1 parenta.
        full_one = _prnt([0], [None])
        short = full_one[0:1] + _u32(2) + full_one[5:]
        chunks = [_chunk("META", _meta()), _chunk("SSTR", _sstr()),
                  _chunk("INST", _inst(0, "Model", [0, 1])),
                  _chunk("PROP", _name_prop(0, ["A", "B"])),
                  _chunk("PRNT", short),
                  b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                  + b"</roblox>"]
        with self.assertRaises(RbxmCorruptError):
            parse_bytes(_header(1, 2) + b"".join(chunks))
        # Presnost: stejny strom se spravnym parentem projde.
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Kid"])], [(0, None), (1, 0)],
            ref_lists=[[0, 1]]))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertEqual(by_id[1]["parent_id"], 0)

    def test_f3_length_fields_edge(self):
        """F3 (5 pripadu): uncomp_len/comp_len na hrane a ramecek +-1 B —
        odmitnuti pred alokaci (rychle), zadna alokace >= limitu."""
        import time
        from src.Inspection.rbxm_parser import MAX_UNCOMPRESSED_BYTES
        big = MAX_UNCOMPRESSED_BYTES
        # uncomp_len = limit + 1: odmitnuto bez dekomprese.
        broken = bytearray(mini_tree())
        struct.pack_into("<I", broken, 32 + 8, big + 1)
        t0 = time.perf_counter()
        with self.assertRaises(RbxmError):
            parse_bytes(bytes(broken))
        self.assertLess(time.perf_counter() - t0, 5.0)
        # uncomp_len presne na limitu, ale soubor drobny: odmitnuto
        # pred alokaci (zadnych 256 MiB v pameti, rychle).
        broken2 = bytearray(mini_tree())
        struct.pack_into("<I", broken2, 32 + 8, big)
        t0 = time.perf_counter()
        with self.assertRaises(RbxmError):
            parse_bytes(bytes(broken2))
        self.assertLess(time.perf_counter() - t0, 5.0)
        # comp_len = limit + 1: stejne odmitnuti.
        broken3 = bytearray(mini_tree())
        struct.pack_into("<I", broken3, 32 + 4, big + 1)
        with self.assertRaises(RbxmError):
            parse_bytes(bytes(broken3))
        # Ramecek -1 B (useknute telo END) a +1 B (vlozeny bajt
        # do prvniho chunku): vzdy RbxmError, nikdy tichy posun.
        good = mini_tree()
        with self.assertRaises(RbxmError):
            parse_bytes(good[:-10] + good[-9:])
        with self.assertRaises(RbxmError):
            parse_bytes(good[:40] + b"\x00" + good[40:])

    def test_f4_aggregate_bomb_scaled(self):
        """F4 (2 soubory): N legalnich chunku, jejichz SOUCET presahne
        agregatni limit = RbxmCorruptError; limit je pro rychlost
        skalovan monkeypatchi (4 KiB), logika souctu je stejna."""
        import time
        from src.Inspection import rbxm_parser as mod
        base = mini_tree()
        pad = b"Q" * 1024
        many = base[:-len(b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                     + b"</roblox>")]
        tail = (b"END\x00" + _u32(0) + _u32(9) + b"\x00" * 4
                + b"</roblox>")
        few = many + _chunk("XXXX", pad) * 2 + tail
        bomb = many + _chunk("XXXX", pad) * 6 + tail
        old = mod.MAX_TOTAL_UNCOMPRESSED
        mod.MAX_TOTAL_UNCOMPRESSED = 4096
        try:
            # Pod limitem: presny census, presne pocty (presnost).
            t0 = time.perf_counter()
            model = parse_bytes(few)
            self.assertLess(time.perf_counter() - t0, 5.0)
            self.assertEqual(len(model["instances"]), 6)
            self.assertEqual(model["skipped_chunks"].count("XXXX"), 2)
            # Nad limitem: agregatni odmitnuti pred alokaci (rychle).
            t0 = time.perf_counter()
            with self.assertRaises(RbxmCorruptError) as ctx:
                parse_bytes(bomb)
            self.assertLess(time.perf_counter() - t0, 5.0)
            self.assertIn("celkova dekomprese", str(ctx.exception))
        finally:
            mod.MAX_TOTAL_UNCOMPRESSED = old

    def test_f5_nonfinite_matrix(self):
        """F5 (14 kombinaci): -Inf/NaN v kazde slozce size/pozice/matice
        + neznamy shape-enum — parser znaci trusted=False, assess hlasi
        BLOCKED s nonfinite_* labelem; zdrava kola zustavaji
        GEOMETRY_OK; zjednotlive -Inf chybi v B1."""
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        bads = (float("-inf"), float("nan"))
        combos = 0
        for bad in bads:
            for slot in ("sx", "sy", "sz", "px", "py", "pz", "mat"):
                sizes = [(2.7, 2.7, 2.7)] * 4
                poss = [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                        (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)]
                mats = [ident] * 4
                if slot == "sx":
                    sizes[0] = (bad, 2.7, 2.7)
                elif slot == "sy":
                    sizes[0] = (2.7, bad, 2.7)
                elif slot == "sz":
                    sizes[0] = (2.7, 2.7, bad)
                elif slot == "px":
                    poss[0] = (bad, 1.0, 0.0)
                elif slot == "py":
                    poss[0] = (0.0, bad, 0.0)
                elif slot == "pz":
                    poss[0] = (0.0, 1.0, bad)
                else:
                    mats[0] = (bad, 0.0, 0.0, 0.0, 1.0, 0.0,
                               0.0, 0.0, 1.0)
                model = parse_bytes(build_model(
                    [(0, "Model", ["Root", "Wheels"]),
                     (1, "Part", ["FL", "FR", "RL", "RR"])],
                    [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
                    extra_chunks=[
                        ("PROP", _shape_prop(1, [0, 0, 0, 0])),
                        ("PROP", _size_prop(1, sizes)),
                        ("PROP", _cframe_prop(1, "CFrame", poss,
                                               [0, 0, 0, 0], mats)),
                    ]))
                by_id = {i["id"]: i for i in model["instances"]}
                # Parser: floaty vzdy trusted=False (i zdrave).
                self.assertFalse(by_id[2]["props"]["size"]["trusted"])
                self.assertFalse(by_id[2]["props"]["CFrame"]["trusted"])
                geo = assess_wheel_geometry(model["instances"])
                self.assertEqual(geo["status"], "BLOCKED",
                                 "bad=%r slot=%s" % (bad, slot))
                self.assertEqual(geo["wheels"]["FL"]["status"], "UNKNOWN",
                                 "bad=%r slot=%s" % (bad, slot))
                label = ("nonfinite_size" if slot[0] == "s"
                         else "nonfinite_position" if slot[0] == "p"
                         else "nonfinite_rotation")
                self.assertIn(label,
                              geo["wheels"]["FL"]["failed_checks"])
                for des in ("FR", "RL", "RR"):
                    self.assertEqual(geo["wheels"][des]["status"],
                                     "GEOMETRY_OK",
                                     "bad=%r slot=%s" % (bad, slot))
                combos += 1
        self.assertEqual(combos, 14)  # 2 hodnoty x 7 pozic
        # Neznama hodnota shape-enum: tvar None + unread, assess BLOCKED
        # s bad_shape (nikdy odhad).
        model = parse_bytes(build_model(
            [(0, "Model", ["Root", "Wheels"]),
             (1, "Part", ["FL", "FR", "RL", "RR"])],
            [(0, None), (1, 0), (2, 1), (3, 1), (4, 1), (5, 1)],
            extra_chunks=[
                ("PROP", _shape_prop(1, [7, 0, 0, 0])),
                ("PROP", _size_prop(1, [(2.7, 2.7, 2.7)] * 4)),
                ("PROP", _cframe_prop(
                    1, "CFrame",
                    [(0.0, 1.0, 0.0), (6.0, 1.0, 0.0),
                     (0.0, 1.0, 10.0), (6.0, 1.0, 10.0)],
                    [0, 0, 0, 0], [ident] * 4)),
            ]))
        by_id = {i["id"]: i for i in model["instances"]}
        self.assertIsNone(by_id[2]["shape"])
        self.assertEqual(by_id[2]["props"]["shape"]["status"], "unread")
        geo = assess_wheel_geometry(model["instances"])
        self.assertEqual(geo["status"], "BLOCKED")
        self.assertIn("bad_shape", geo["wheels"]["FL"]["failed_checks"])

    def test_f6_cframe_preset_sweep(self):
        """F6 (11 id): CFrame orientacni id 0-8 + 9/255 — id 0 matice,
        id 2 identita, vse ostatni unread-preset-N; pozice vzdy presne."""
        import math
        ident = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        tried = 0
        for oid in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 255):
            mat = [ident if oid == 0 else None]
            model = parse_bytes(build_model(
                [(0, "Part", ["P"])], [(0, None)],
                extra_chunks=[("PROP", _cframe_prop(
                    0, "CFrame", [(1.0, 2.0, 3.0)], [oid], mat))]))
            inst = model["instances"][0]
            self.assertEqual(inst["position"], (1.0, 2.0, 3.0),
                             "orient=%d" % oid)
            entry = inst["props"]["CFrame"]
            self.assertEqual(entry["status"], "read")
            self.assertFalse(entry["trusted"])
            if oid == 0:
                self.assertEqual(entry["rotation_status"], "matrix")
                self.assertTrue(all(math.isclose(a, b)
                                    for a, b in zip(inst["rotation"],
                                                    ident)))
            elif oid == 2:
                self.assertEqual(entry["rotation_status"],
                                 "identity-preset (tabulka neoverena)")
                self.assertEqual(inst["rotation"], "identity")
            else:
                self.assertEqual(entry["rotation_status"],
                                 "unread-preset-%d" % oid)
                self.assertIsNone(inst["rotation"])
            tried += 1
        self.assertEqual(tried, 11)

    def test_f7_long_cycles(self):
        """F7 (3 pripady): cyklus delky 3 a delky 5 = RbxmHierarchyError;
        platny retez delky 5 projde s presnymi parenty (presnost
        detektoru, zadny falesny poplach)."""
        # 3-cyklus A->B->C->A.
        data3 = build_model([(0, "Model", ["A", "B", "C"])],
                            [(0, 1), (1, 2), (2, 0)])
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(data3)
        # 5-cyklus.
        names5 = ["N%d" % k for k in range(5)]
        links5 = [(k, (k + 1) % 5) for k in range(5)]
        with self.assertRaises(RbxmHierarchyError):
            parse_bytes(build_model([(0, "Model", names5)], links5))
        # Presnost: retez 5 bez cyklu projde, parenti presne.
        chain = [(0, None)] + [(k, k - 1) for k in range(1, 5)]
        model = parse_bytes(build_model([(0, "Model", names5)], chain))
        by_id = {i["id"]: i for i in model["instances"]}
        for k in range(1, 5):
            self.assertEqual(by_id[k]["parent_id"], k - 1)
        self.assertIsNone(by_id[0]["parent_id"])

    def test_f8_byte_fuzz_1000(self):
        """F8: 1000 byte-mutaci realne kopie (seed 20261119+8, 1-3 B)
        + 7 trunkaci — invariant: jen RbxmError, nebo platny model
        (815 instanci, platni parenti, tvary ze zname mnoziny);
        soubor zustava hashove netknuty (read-only)."""
        import random
        real = _require_real_copy(self)
        rng = random.Random(FUZZ_SEED + 8)
        with open(real, "rb") as handle:
            raw = handle.read()
        accepted = 0
        trials = 1000
        for trial in range(trials):
            blob = bytearray(raw)
            for _ in range(rng.randint(1, 3)):
                blob[rng.randrange(len(blob))] = rng.randrange(256)
            try:
                model = parse_bytes(bytes(blob))
            except RbxmError:
                continue
            accepted += 1
            self.assertEqual(model["num_instances"], 815,
                             "fuzz trial %d" % trial)
            self.assertEqual(len(model["instances"]), 815)
            by_id = {i["id"] for i in model["instances"]}
            for inst in model["instances"]:
                parent = inst["parent_id"]
                if parent is not None:
                    self.assertIn(parent, by_id, "fuzz trial %d" % trial)
                self.assertTrue(
                    inst["shape"] is None
                    or inst["shape"] in PART_TYPE_NAMES.values(),
                    "fuzz trial %d" % trial)
        for cut in (1, 32, 1000, len(raw) // 2, len(raw) - 10,
                    len(raw) - 1, 33):
            with self.assertRaises(RbxmError):
                parse_bytes(raw[:cut])
        self.assertEqual(sha256_of(WORK_COPY), EXPECTED_SHA256)
        self.assertLessEqual(accepted, trials)


if __name__ == "__main__":
    unittest.main()

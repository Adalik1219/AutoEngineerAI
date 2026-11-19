"""RBXM chunk reader + INST + PRNT (M2, milnik C05-A/B).

Cte binarni format Roblox modelu (verze 0) ciste-stdlib, pouze pro cteni.
Rozsah C05-A/B (VEDOME NEDOKONCENO, viz dolu):
  - hlavicka souboru (magic, signatura, verze, pocty, reserved),
  - ramecky chunku (jmeno, delky, hranice, LZ4 dekomprese),
  - SSTR (jen pocet sdilenych retezcu; obsah je pro tuto fazi nepruhledny),
  - META (slovnik klic/hodnota),
  - INST (trida + referenty instanci),
  - PRNT (vazby dite -> rodic),
  - PROP pouze pro retezcovou vlastnost "Name" (identita instance).
Vse ostatni (Shape, Size, CFrame, Vector3, floaty, ...) se NEINTERPRETUJE:
kazda instance dostane shape=None a model nese geometry={"status":
"BLOCKED", ...}. Geometrie UNKNOWN/BLOCKED, nikdy odhad (C05-C/D).

Bezpecnost: poskozena hlavicka, spatna delka chunku, poskozena LZ4 data,
neznama referencni struktura, neplatny parent, duplicitni ID nebo cyklus
vedou k RbxmError (bezpecne odmitnuti / BLOCKED), nikdy k tichnemu pruchodu.
Nezname chunky a ne-Name PROP se bezpecne preskakuji a eviduji v censu —
neni to tichy pruchod, volajici vidi, co se neinterpretovalo.

Pravidla: Python 3 stdlib only, komentare/dokumentace cesky,
identifikatory anglicky. Soubor se nikdy neotevira k zapisu.
"""

from __future__ import annotations

import struct


# Ocekavana hlavicka (overeno sondou, reports/RBXM-SPIKE.md §3).
MAGIC = b"<roblox!"
SIGNATURE = bytes((0x89, 0xFF, 0x0D, 0x0A, 0x1A, 0x0A))
VERSION = 0
HEADER_LEN = 32
CHUNK_HEADER_LEN = 16
END_BODY = b"</roblox>"

# Bezpecnostni stropy (odmitnout absurdni hodnoty driv, nez se alokuje pamet).
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_INSTANCES = 10_000_000
MAX_CHUNKS = 100_000

# Hodnota referentu -1 = koren (zadny rodic).
NULL_PARENT = -1


class RbxmError(Exception):
    """Zakladni chyba RBXM parseru: bezpecne odmitnuti / BLOCKED."""


class RbxmCorruptError(RbxmError):
    """Poskozeny soubor nebo nepodporovana struktura (hlavicka, chunk,
    LZ4, INST/SSTR/META, duplicitni ID, chybejici Name)."""


class RbxmHierarchyError(RbxmError):
    """Semanticky spatna hierarchie (neplatny parent, cyklus). Volajici
    (napr. wheel_detect) to mapuje na BLOCKED, nikdy na validni vysledek."""


def _u32(data, pos):
    """Precte u32 LE s kontrolou hranic; mimo hranice = poskozeny soubor."""
    if pos < 0 or pos + 4 > len(data):
        raise RbxmCorruptError(
            "cteni u32 mimo hranice (pos=%d, len=%d)" % (pos, len(data)))
    return struct.unpack("<I", data[pos:pos + 4])[0]


def _read_string(data, pos):
    """Precte retezec (u32 delka + UTF-8 bajty) s kontrolou hranic."""
    length = _u32(data, pos)
    pos += 4
    if pos + length > len(data):
        raise RbxmCorruptError(
            "retezec presahuje hranice (delka=%d, zbyva=%d)"
            % (length, len(data) - pos))
    try:
        text = bytes(data[pos:pos + length]).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RbxmCorruptError("neplatne UTF-8 v retezci: %s" % exc)
    return text, pos + length


def _zigzag_decode(value):
    """Zigzag dekodovani nezáporneho intu (mapuje i -1 pro NULL_PARENT)."""
    return (value >> 1) ^ -(value & 1)


def lz4_decompress(block, expected_len):
    """Minimalni LZ4-block dekompresor (token/nibbles, literaly, match-copy).

    Striktni: prekroceni ocekavane delky, zkraceny vstup, nulovy nebo
    neplatny offset, nedosazeni presne delky a prebytecny vstup vedou
    k RbxmCorruptError. Prekryvajici se match-copy je legalni a kopiruje
    se po bajtech.
    """
    if expected_len < 0 or expected_len > MAX_UNCOMPRESSED_BYTES:
        raise RbxmCorruptError(
            "absurdni ocekavana delka LZ4: %d" % expected_len)
    out = bytearray()
    pos = 0
    size = len(block)
    while True:
        if pos >= size:
            raise RbxmCorruptError("LZ4: chybi token (uskrnuty vstup)")
        token = block[pos]
        pos += 1
        lit_len = token >> 4
        if lit_len == 15:
            while True:
                if pos >= size:
                    raise RbxmCorruptError("LZ4: useknuta delka literalu")
                byte = block[pos]
                pos += 1
                lit_len += byte
                if byte != 255:
                    break
        if pos + lit_len > size:
            raise RbxmCorruptError("LZ4: literaly presahuji vstup")
        out += block[pos:pos + lit_len]
        pos += lit_len
        if len(out) > expected_len:
            raise RbxmCorruptError("LZ4: vystup presahl ocekavanou delku")
        if len(out) == expected_len:
            break
        if pos + 2 > size:
            raise RbxmCorruptError("LZ4: chybi match offset (uskrnuty vstup)")
        offset = block[pos] | (block[pos + 1] << 8)
        pos += 2
        if offset == 0 or offset > len(out):
            raise RbxmCorruptError(
                "LZ4: neplatny offset %d pri delce vystupu %d"
                % (offset, len(out)))
        match_len = token & 15
        if match_len == 15:
            while True:
                if pos >= size:
                    raise RbxmCorruptError("LZ4: useknuta delka matche")
                byte = block[pos]
                pos += 1
                match_len += byte
                if byte != 255:
                    break
        match_len += 4
        for _ in range(match_len):
            out.append(out[len(out) - offset])
            if len(out) > expected_len:
                raise RbxmCorruptError(
                    "LZ4: match presahl ocekavanou delku")
        if len(out) == expected_len:
            break
    if pos != size:
        raise RbxmCorruptError(
            "LZ4: prebytecna data za koncem bloku (%d B)" % (size - pos))
    return bytes(out)


def _decode_referents(segment, count, what):
    """Dekoduje pole referentu: 4 prokladane lane (MSB prvni), zigzag,
    delta-akumulace. Vraci list absolutnich referentu.

    Format overen na pracovni kopii: INST dava presne 0..814.
    """
    if len(segment) != 4 * count:
        raise RbxmCorruptError(
            "%s: spatna delka pole referentu (%d != 4*%d)"
            % (what, len(segment), count))
    lanes = [segment[i * count:(i + 1) * count] for i in range(4)]
    values = []
    acc = 0
    for i in range(count):
        raw = (lanes[3][i] | (lanes[2][i] << 8)
               | (lanes[1][i] << 16) | (lanes[0][i] << 24))
        acc += _zigzag_decode(raw)
        values.append(acc)
    return values


def _parse_header(data):
    """Overi a vrati (num_types, num_instances). Cokoli jineho = odmitnout."""
    if len(data) < HEADER_LEN:
        raise RbxmCorruptError(
            "soubor kratsi nez hlavicka (%d B)" % len(data))
    if data[0:8] != MAGIC:
        raise RbxmCorruptError("spatne magic: %r" % data[0:8])
    if data[8:14] != SIGNATURE:
        raise RbxmCorruptError("spatna signatura: %r" % data[8:14])
    (version,) = struct.unpack("<H", data[14:16])
    if version != VERSION:
        raise RbxmCorruptError(
            "nepodporovana verze: %d (ocekavana %d)" % (version, VERSION))
    num_types = _u32(data, 16)
    num_instances = _u32(data, 20)
    if data[24:32] != b"\x00" * 8:
        raise RbxmCorruptError("nenulove reserved v hlavicce")
    if num_types > MAX_INSTANCES or num_instances > MAX_INSTANCES:
        raise RbxmCorruptError(
            "absurdni pocty v hlavicce (typy=%d, instance=%d)"
            % (num_types, num_instances))
    return num_types, num_instances


def _read_chunks(data):
    """Precte ramecky chunku; vrati list (jmeno, telo) vcetne END.

    Kontroluje hranice, delky a presny konec na END (zadna data navic).
    Nezname chunky se NEZAHOZUJI potichu: telo se dekomprimuje (kontrola
    integrity) a chunk se oznaci jako preskoceny v censu.
    """
    pos = HEADER_LEN
    chunks = []
    while True:
        if pos + CHUNK_HEADER_LEN > len(data):
            raise RbxmCorruptError(
                "useknuta hlavicka chunku na offsetu %d" % pos)
        name = bytes(data[pos:pos + 4])
        comp_len = _u32(data, pos + 4)
        uncomp_len = _u32(data, pos + 8)
        if data[pos + 12:pos + 16] != b"\x00" * 4:
            raise RbxmCorruptError(
                "nenulove reserved v chunku %r" % name)
        if (uncomp_len > MAX_UNCOMPRESSED_BYTES
                or comp_len > MAX_UNCOMPRESSED_BYTES):
            raise RbxmCorruptError(
                "absurdni delka chunku %r (%d/%d)" % (name, comp_len,
                                                     uncomp_len))
        body_start = pos + CHUNK_HEADER_LEN
        if comp_len == 0:
            stored = uncomp_len
        else:
            stored = comp_len
        if body_start + stored > len(data):
            raise RbxmCorruptError(
                "chunk %r presahuje konec souboru" % name)
        raw_body = bytes(data[body_start:body_start + stored])
        if comp_len == 0:
            body = raw_body
        else:
            body = lz4_decompress(raw_body, uncomp_len)
        chunks.append((name, body))
        pos = body_start + stored
        if len(chunks) > MAX_CHUNKS:
            raise RbxmCorruptError("prilis mnoho chunku (asi smycka)")
        if name == b"END\x00":
            break
    if pos != len(data):
        raise RbxmCorruptError(
            "data za END chunkem (%d B navic)" % (len(data) - pos))
    return chunks


def _parse_meta(body):
    """META: u32 pocet + dvojice retezcu klic/hodnota."""
    count = _u32(body, 0)
    pos = 4
    meta = {}
    for _ in range(count):
        if pos >= len(body):
            raise RbxmCorruptError("META: useknuty zaznam")
        key, pos = _read_string(body, pos)
        value, pos = _read_string(body, pos)
        meta[key] = value
    if pos != len(body):
        raise RbxmCorruptError("META: prebytecna data (%d B)" % (len(body)
                                                                 - pos))
    return meta


def _parse_sstr(body):
    """SSTR: precte jen pocet sdilenych retezcu. Zbytek tela je pro C05
    nepruhledny (neinterpretuje se). Nenulova tabulka = bezpecne odmitnuti,
    protoze inline-Name by pak nemusela byt uplna."""
    if len(body) < 4:
        raise RbxmCorruptError("SSTR: telo kratsi nez 4 B")
    shared = _u32(body, 0)
    if shared != 0:
        raise RbxmCorruptError(
            "SSTR: sdilena tabulka (%d) neni v C05-A/B podporovana; "
            "jmena by nemusela byt uplna" % shared)
    return {"shared_strings": 0, "opaque_bytes": len(body) - 4}


def _parse_inst(body, seen_ids):
    """INST: typ + referenty. Duplicitni ID napric typy = poskozeny soubor."""
    if len(body) < 4:
        raise RbxmCorruptError("INST: telo kratsi nez type_id")
    (type_id,) = struct.unpack("<i", body[0:4])
    name, pos = _read_string(body, 4)
    if not name:
        raise RbxmCorruptError("INST: prazdne jmeno tridy")
    if pos >= len(body):
        raise RbxmCorruptError("INST %s: chybi is_service" % name)
    pos += 1  # is_service (nevyuzito, jen kontrola pritomnosti)
    count = _u32(body, pos)
    pos += 4
    if count > MAX_INSTANCES:
        raise RbxmCorruptError("INST %s: absurdni pocet %d" % (name, count))
    referents = _decode_referents(body[pos:], count, "INST %s" % name)
    for ref in referents:
        if ref < 0:
            raise RbxmCorruptError(
                "INST %s: zaporny referent %d" % (name, ref))
        if ref in seen_ids:
            raise RbxmCorruptError("duplicitni instance id: %d" % ref)
        seen_ids.add(ref)
    return {"type_id": type_id, "class_name": name, "referents": referents}


def _parse_name_prop(body, expected_count):
    """Name PROP (typ string 0x01): inline retezce, pocet musi sedet."""
    if len(body) < 4:
        raise RbxmCorruptError("PROP/Name: telo kratsi nez type_id")
    (type_id,) = struct.unpack("<i", body[0:4])
    prop_name, pos = _read_string(body, 4)
    if pos >= len(body):
        raise RbxmCorruptError("PROP/Name: chybi typ hodnoty")
    value_type = body[pos]
    pos += 1
    if prop_name != "Name" or value_type != 0x01:
        raise RbxmCorruptError("interni chyba: spatny PROP pro Name")
    names = []
    cursor = pos
    while cursor < len(body):
        text, cursor = _read_string(body, cursor)
        names.append(text)
    if len(names) != expected_count:
        raise RbxmCorruptError(
            "PROP/Name (typ %d): pocet jmen %d != pocet instanci %d"
            % (type_id, len(names), expected_count))
    return type_id, names


def _check_hierarchy(parent_of):
    """Overi parent mapu: zadne cykly (iterativni DFS s barvami, O(n))."""
    color = {}  # id -> 1 rozpracovany, 2 hotovy

    def walk(start):
        node = start
        while True:
            state = color.get(node)
            if state == 2:
                for n in path:
                    color[n] = 2
                return
            if state == 1:
                raise RbxmHierarchyError(
                    "cyklus v parent hierarchii u instance %r" % node)
            color[node] = 1
            path.append(node)
            parent = parent_of.get(node)
            if parent is None:
                for n in path:
                    color[n] = 2
                return
            node = parent

    for start_id in parent_of:
        if color.get(start_id) is None:
            path = []
            walk(start_id)


def parse_bytes(data):
    """Parsuje RBXM data z pameti; vrati dict modelu (viz parse_rbxm)."""
    data = bytes(data)
    num_types, num_instances = _parse_header(data)
    chunks = _read_chunks(data)

    census = {}
    skipped_chunks = []
    meta = {}
    sstr_info = None
    inst_list = []
    seen_ids = set()
    name_prop_bodies = []
    skipped_props = []
    prnt_body = None
    meta_seen = sstr_seen = prnt_seen = 0

    for name, body in chunks:
        census[name] = census.get(name, 0) + 1
        if name == b"META":
            meta_seen += 1
            if meta_seen > 1:
                raise RbxmCorruptError("duplicitni META chunk")
            meta = _parse_meta(body)
        elif name == b"SSTR":
            sstr_seen += 1
            if sstr_seen > 1:
                raise RbxmCorruptError("duplicitni SSTR chunk")
            sstr_info = _parse_sstr(body)
        elif name == b"INST":
            inst_list.append(_parse_inst(body, seen_ids))
        elif name == b"PROP":
            if len(body) < 8:
                raise RbxmCorruptError("PROP: telo kratsi nez 8 B")
            prop_name, name_end = _read_string(body, 4)
            if name_end >= len(body):
                raise RbxmCorruptError("PROP %r: chybi typ hodnoty"
                                       % prop_name)
            value_type = body[name_end]
            (prop_type_id,) = struct.unpack("<i", body[0:4])
            if prop_name == "Name":
                if value_type != 0x01:
                    raise RbxmCorruptError(
                        "PROP/Name typu %d ma ne-retezcovy typ 0x%02x; "
                        "identita by nebyla uplna" % (prop_type_id,
                                                      value_type))
                name_prop_bodies.append(body)
            else:
                skipped_props.append({
                    "type_id": prop_type_id,
                    "prop_name": prop_name,
                    "value_type": "0x%02x" % value_type,
                })
        elif name == b"PRNT":
            prnt_seen += 1
            if prnt_seen > 1:
                raise RbxmCorruptError("duplicitni PRNT chunk")
            prnt_body = body
        elif name == b"END\x00":
            if body != END_BODY:
                raise RbxmCorruptError("spatne telo END chunku: %r" % body)
        else:
            skipped_chunks.append(name.decode("ascii", errors="replace"))

    if len(inst_list) != num_types:
        raise RbxmCorruptError(
            "pocet INST chunku %d != num_types %d"
            % (len(inst_list), num_types))
    if len(seen_ids) != num_instances:
        raise RbxmCorruptError(
            "pocet referentu %d != num_instances %d"
            % (len(seen_ids), num_instances))
    if min(seen_ids or [0]) < 0 or max(seen_ids or [0]) >= num_instances:
        raise RbxmCorruptError("referenty mimo rozsah 0..%d"
                               % (num_instances - 1))
    if prnt_seen != 1:
        raise RbxmCorruptError("chybi prave jeden PRNT chunk")
    if sstr_info is None:
        sstr_info = {"shared_strings": 0, "opaque_bytes": 0}
    if prnt_body is None:
        raise RbxmCorruptError("chybi PRNT telo (interni chyba)")

    # Name PROP se vyhodnocuji az po vsech INST (poradi chunku neni dane).
    name_by_type = {}
    for body in name_prop_bodies:
        (prop_type_id,) = struct.unpack("<i", body[0:4])
        type_id, names = _parse_name_prop(
            body, _type_count(inst_list, prop_type_id))
        if type_id in name_by_type:
            raise RbxmCorruptError(
                "duplicitni PROP/Name pro typ %d" % type_id)
        name_by_type[type_id] = names

    if len(prnt_body) < 5:
        raise RbxmCorruptError("PRNT: telo kratsi nez 5 B")
    if prnt_body[0] != 0:
        raise RbxmCorruptError(
            "PRNT: nepodporovana verze %d" % prnt_body[0])
    prnt_count = _u32(prnt_body, 1)
    if prnt_count != num_instances:
        raise RbxmCorruptError(
            "PRNT: pocet %d != num_instances %d" % (prnt_count,
                                                   num_instances))
    payload = prnt_body[5:]
    if len(payload) != 8 * prnt_count:
        raise RbxmCorruptError("PRNT: spatna delka dat")
    kids = _decode_referents(payload[:4 * prnt_count], prnt_count, "PRNT kids")
    parents = _decode_referents(payload[4 * prnt_count:], prnt_count,
                                "PRNT parents")
    if sorted(kids) != list(range(num_instances)):
        raise RbxmCorruptError("PRNT: dite neodpovida 0..%d"
                               % (num_instances - 1))
    parent_of = {}
    for child, parent in zip(kids, parents):
        if parent != NULL_PARENT and not (0 <= parent < num_instances):
            raise RbxmHierarchyError(
                "neplatny parent id %r u instance %r" % (parent, child))
        parent_of[child] = None if parent == NULL_PARENT else parent
    _check_hierarchy(parent_of)

    class_by_id = {}
    for entry in inst_list:
        for ref in entry["referents"]:
            class_by_id[ref] = entry["class_name"]
    names_full = {}
    for entry in inst_list:
        names = name_by_type.get(entry["type_id"])
        if names is None:
            continue  # jmeno chybi -> None (evidovano nize)
        for ref, text in zip(entry["referents"], names):
            names_full[ref] = text

    instances = []
    for ref in range(num_instances):
        instances.append({
            "id": ref,
            "class_name": class_by_id[ref],
            "name": names_full.get(ref),
            # Tvar/rozmery/geometrie: PROP se v C05 neinterpretuje.
            "shape": None,
            "parent_id": parent_of[ref],
        })

    missing_names = sum(1 for i in instances if i["name"] is None)
    return {
        "num_types": num_types,
        "num_instances": num_instances,
        "meta": meta,
        "sstr": sstr_info,
        "instances": instances,
        "chunk_census": {k.decode("ascii", errors="replace"): v
                         for k, v in census.items()},
        "skipped_chunks": skipped_chunks,
        "skipped_props": skipped_props,
        "missing_name_count": missing_names,
        "geometry": {
            "status": "BLOCKED",
            "reason": ("C05-A/B: hodnoty PROP (Shape/Size/CFrame/...) se "
                       "neinterpretuji (plan C05-C/D); tvar a geometrie "
                       "nejsou k dispozici, nikdy se neodhaduji."),
        },
    }


def _type_count(inst_list, type_id):
    """Pocet instanci typu pro kontrolu PROP/Name (0 = neznamy typ)."""
    for entry in inst_list:
        if entry["type_id"] == type_id:
            return len(entry["referents"])
    return 0


def parse_rbxm(path):
    """Parsuje RBXM soubor, pouze pro cteni (open 'rb').

    Soubor nikdy neotevira k zapisu; pred/po kontrolu hashe dela volajici
    (testy, G-01 brana).
    """
    with open(path, "rb") as handle:
        data = handle.read()
    return parse_bytes(data)

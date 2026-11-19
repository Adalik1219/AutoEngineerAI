"""RBXM chunk reader + INST + PRNT + geometrie (M2, milnik C05-A/B/C/D).

Cte binarni format Roblox modelu (verze 0) ciste-stdlib, pouze pro cteni.
Rozsah C05 (VEDOME NECOMPLETNI, viz dolu):
  - hlavicka souboru (magic, signatura, verze, pocty, reserved),
  - ramecky chunku (jmeno, delky, hranice, LZ4 dekomprese),
  - SSTR (jen prazdna sdilena tabulka; neprazdna = nepodporovano),
  - META (slovnik klic/hodnota, duplicitni klic = poskozeny soubor),
  - INST (trida + referenty instanci; referenty jsou libovolna
    nezaporna ID bez predpokladu souvislosti),
  - PRNT (vazby dite -> rodic; dite musi byt znamy referent,
    rodic znamy referent nebo koren; duplicity a cykly = chyba),
  - PROP pouze: Name (string, identita), shape (enum PartType),
    size (Vector3), CFrame / CFrame0 / PivotOffset (orientacni bloky
    + pozicni lane).
Vse ostatni (booly, inty, floaty jednotlivych vlastnosti, barvy, UDim,
referencni vlastnosti, ...) se NEINTERPRETUJE a je evidovano jako
neprectene (skipped_props) — neni to tichy pruchod, volajici vidi,
co se neinterpretovalo.

Kodovani lane (overeno na pracovni kopii, reports/RBXM-SPIKE.md §C05-D):
  - referenty INST/PRNT: 4 prokladane lane, MSB lane prvni, zigzag,
    delta-akumulace,
  - enum/int PROP: 4 lane, LSB lane prvni, bez zigzagu a bez delt,
  - floaty (Vector3 size, pozice CFrame): component-major, 4 lane
    na slozku, MSB lane prvni, u32 transformovano ror1
    (bits = (w >> 1) | ((w & 1) << 31)),
  - CFrame: nejprve orientacni bloky instanci (u8 id + pripadne
    9x f32 LE matice), pak pozice jako float lane vyse;
    id 0 = vlastni matice, id 2 = identita (preset, bez dat),
    jine id = neoverena preseta -> orientace neprectena (unread).

Provenience: kazda geometricka vlastnost instance nese zaznam
(status read/missing/unread, jak dekodovano, trusted True/False).
Floaty (size, pozice, matice) jsou vzdy trusted=False — bez Studio
ground-truth je kalibrace studs/m NOT IMPLEMENTED (viz
calibrate_studs_per_meter). Tvar (enum) je trusted=True (krizove
overeno: kola = Ball dle auditu).

Bezpecnost: poskozena hlavicka, spatna delka chunku, poskozena LZ4 data,
prekroceni limitu (velikost souboru / celkova dekomprese / pocty),
neznama referencni struktura, neplatny parent, duplicitni ID nebo cyklus
vedou k RbxmError (bezpecne odmitnuti / BLOCKED), nikdy k tichnemu
pruchodu. Dobre formovany, ale nepodporovany obsah (SSTR tabulka,
jina verze, verze PRNT) vede k RbxmUnsupportedError (podtrida
RbxmError): rozliseni poskozeny vs nepodporovany soubor.

Pravidla: Python 3 stdlib only, komentare/dokumentace cesky,
identifikatory anglicky. Soubor se nikdy neotevira k zapisu.
"""

from __future__ import annotations

import math
import os
import struct


# Ocekavana hlavicka (overeno sondou, reports/RBXM-SPIKE.md §3).
MAGIC = b"<roblox!"
SIGNATURE = bytes((0x89, 0xFF, 0x0D, 0x0A, 0x1A, 0x0A))
VERSION = 0
HEADER_LEN = 32
CHUNK_HEADER_LEN = 16
END_BODY = b"</roblox>"

# Bezpecnostni stropy (odmitnout absurdni hodnoty driv, nez se alokuje pamet).
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 256 * 1024 * 1024
MAX_INSTANCES = 10_000_000
MAX_CHUNKS = 100_000
MAX_META_ENTRIES = 100_000
# Per-pole cap poctu hodnot (P1-4): realna kopie ma 815 instanci; cokoli
# nad 10^5 v jednom poli je mimo formatovy ucel. Vynucuje se PRED stavbou
# Python seznamu (1 vstupni bajt -> ~30B objekt by jinak dal GB/minuty
# uvnitr povolenych limitu). Plati pro referenty, enum/int lane, float
# lane, CFrame pole, Name pocty i PRNT.
MAX_FIELD_VALUES = 100_000

# Hodnota referentu -1 = koren (zadny rodic).
NULL_PARENT = -1

# Orientacni id v CFrame blocich (overeno na kopii: PivotOffset vsude 2
# bez maticovych dat; 0 = vlastni 9x f32 matice; jine = neovereno).
ORIENT_CUSTOM = 0
ORIENT_IDENTITY = 2
IDENTITY_ROTATION = (1.0, 0.0, 0.0,
                     0.0, 1.0, 0.0,
                     0.0, 0.0, 1.0)

# Enum PartType (overeno: kola = 0 = Ball dle auditu; 1 = Block,
# 2 = Cylinder; jina hodnota = neprecteno, nikdy odhad).
PART_TYPE_NAMES = {0: "Ball", 1: "Block", 2: "Cylinder"}

# Oznaceni kol pro geometricke posouzeni (zrcadli wheel_detect.py,
# ktery se NEMENI; identitni pravidlo (a)+(b)+(c) plati doslovne).
WHEEL_DESIGNATIONS = ("FL", "FR", "RL", "RR")
WHEELS_MODEL_NAME = "Wheels"
WHEEL_SHAPE = "Ball"


class RbxmError(Exception):
    """Zakladni chyba RBXM parseru: bezpecne odmitnuti / BLOCKED."""


class RbxmCorruptError(RbxmError):
    """Poskozeny soubor nebo porusena struktura (hlavicka, chunk,
    LZ4, INST/SSTR/META/PRNT, duplicitni ID, limity)."""


class RbxmUnsupportedError(RbxmError):
    """Dobre formovany, ale nepodporovany obsah (jina verze souboru,
    neprazdna SSTR tabulka, verze PRNT). Neni to poskozeny soubor,
    jen ho tato verze parseru neumi cist."""


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


def _ror1(word):
    """Rotace u32 o 1 bit vpravo (inverze k zapisu floatu v RBXM)."""
    return ((word >> 1) | ((word & 1) << 31)) & 0xFFFFFFFF


def lz4_decompress(block, expected_len):
    """Minimalni LZ4-block dekompresor (token/nibbles, literaly, match-copy).

    Striktni: prekroceni ocekavane delky, zkraceny vstup, nulovy nebo
    neplatny offset, nedosazeni presne delky a prebytecny vstup vedou
    k RbxmCorruptError. Prekryvajici se match-copy je legalni a kopiruje
    se po blocich (slice `out[a:b]` se vyhodnoti najednou, takze prekryv
    je bezpecny; pri offsetu mensim nez delka matche se zdrojove okno
    s kazdym blokem prodluzuje, takze vysledek je stejny jako kopie
    po bajtech). Jedna kontrola delky na konci misto testu za kazdy bajt.
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
        if len(out) + match_len > expected_len:
            raise RbxmCorruptError(
                "LZ4: match presahl ocekavanou delku")
        # Blokove kopie: jeden slice se vyhodnoti naraz (prekryv OK).
        # Okno [start, ...) roste s kazdym blokem (zdvojovani), takze
        # i offset < match_len da stejna data jako kopie po bajtech
        # v O(log n) blocich misto O(n) iteraci.
        start = len(out) - offset
        while match_len > 0:
            avail = len(out) - start
            take = match_len if match_len < avail else avail
            out += out[start:start + take]
            match_len -= take
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
    if count > MAX_FIELD_VALUES:
        raise RbxmCorruptError(
            "%s: absurdni pocet referentu %d (cap %d); bezpecne odmitnuto"
            % (what, count, MAX_FIELD_VALUES))
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


def _decode_enum_lanes(data, count, what):
    """Dekoduje enum/int PROP: 4 lane, LSB lane prvni, bez zigzagu a delt."""
    if count > MAX_FIELD_VALUES:
        raise RbxmCorruptError(
            "%s: absurdni pocet enum hodnot %d (cap %d); bezpecne odmitnuto"
            % (what, count, MAX_FIELD_VALUES))
    if len(data) != 4 * count:
        raise RbxmCorruptError(
            "%s: spatna delka enum pole (%d != 4*%d)"
            % (what, len(data), count))
    lanes = [data[i * count:(i + 1) * count] for i in range(4)]
    return [lanes[0][i] | (lanes[1][i] << 8)
            | (lanes[2][i] << 16) | (lanes[3][i] << 24)
            for i in range(count)]


def _decode_float_lanes(data, count, what):
    """Dekoduje 3x float (Vector3 / pozice CFrame): component-major,
    4 lane na slozku, MSB lane prvni, u32 transformovano ror1.

    Vraci [xs, ys, zs] (kazdy list delky count). Overeno: size kol
    (2.7, 2.7, 2.7) a symetricke pozice FL/FR/RL/RR.
    """
    if count > MAX_FIELD_VALUES:
        raise RbxmCorruptError(
            "%s: absurdni pocet float hodnot %d (cap %d); bezpecne odmitnuto"
            % (what, count, MAX_FIELD_VALUES))
    if len(data) != 12 * count:
        raise RbxmCorruptError(
            "%s: spatna delka float pole (%d != 12*%d)"
            % (what, len(data), count))
    comps = []
    for comp in range(3):
        values = []
        for i in range(count):
            word = ((data[(4 * comp) * count + i] << 24)
                    | (data[(4 * comp + 1) * count + i] << 16)
                    | (data[(4 * comp + 2) * count + i] << 8)
                    | data[(4 * comp + 3) * count + i])
            values.append(struct.unpack(
                "<f", struct.pack("<I", _ror1(word)))[0])
        comps.append(values)
    return comps


def _parse_cframe_array(data, count, what):
    """Dekoduje CFrame/CFrame0/PivotOffset PROP.

    Nejprve orientacni bloky instanci (u8 id + pripadne 9x f32 LE
    matice; id 0 = vlastni matice, id 2 = identita bez dat, jine id =
    neoverena preseta -> matice None = orientace neprectena), pak
    pozice jako float lane (_decode_float_lanes).

    Vraci (ids, matrices, [xs, ys, zs]). Neoverena preseta neni chyba
    souboru, jen neprectena orientace (provenience).
    """
    ids = []
    matrices = []
    pos = 0
    if count > MAX_FIELD_VALUES:
        raise RbxmCorruptError(
            "%s: absurdni pocet %d (cap %d); bezpecne odmitnuto"
            % (what, count, MAX_FIELD_VALUES))
    for _ in range(count):
        if pos >= len(data):
            raise RbxmCorruptError(
                "%s: useknuty orientacni blok (%d/%d instanci)"
                % (what, len(ids), count))
        orient_id = data[pos]
        pos += 1
        ids.append(orient_id)
        if orient_id == ORIENT_CUSTOM:
            if pos + 36 > len(data):
                raise RbxmCorruptError(
                    "%s: useknuta matice CFrame u instance %d"
                    % (what, len(ids) - 1))
            matrices.append(struct.unpack("<9f", data[pos:pos + 36]))
            pos += 36
        elif orient_id == ORIENT_IDENTITY:
            matrices.append(IDENTITY_ROTATION)
        else:
            matrices.append(None)
    positions = _decode_float_lanes(data[pos:], count, what)
    return ids, matrices, positions


def _parse_header(data):
    """Overi a vrati (num_types, num_instances). Cokoli jineho = odmitnout.

    Jina verze souboru neni poskozeni, ale nepodporovany obsah.
    """
    if len(data) < HEADER_LEN:
        raise RbxmCorruptError(
            "soubor kratsi nez hlavicka (%d B)" % len(data))
    if data[0:8] != MAGIC:
        raise RbxmCorruptError("spatne magic: %r" % data[0:8])
    if data[8:14] != SIGNATURE:
        raise RbxmCorruptError("spatna signatura: %r" % data[8:14])
    (version,) = struct.unpack("<H", data[14:16])
    if version != VERSION:
        raise RbxmUnsupportedError(
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
    Celkova dekomprese se hlida PRUBEZNE pred kazdou alokaci
    (MAX_TOTAL_UNCOMPRESSED). Nezname chunky se NEZAHOZUJI potichu:
    telo se dekomprimuje (kontrola integrity) a chunk se oznaci jako
    preskoceny v censu.
    """
    pos = HEADER_LEN
    chunks = []
    total_uncompressed = 0
    while True:
        if len(chunks) >= MAX_CHUNKS:
            raise RbxmCorruptError("prilis mnoho chunku (asi smycka)")
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
        if total_uncompressed + uncomp_len > MAX_TOTAL_UNCOMPRESSED:
            raise RbxmCorruptError(
                "celkova dekomprese presahuje limit (%d B)"
                % MAX_TOTAL_UNCOMPRESSED)
        raw_body = bytes(data[body_start:body_start + stored])
        if comp_len == 0:
            body = raw_body
        else:
            body = lz4_decompress(raw_body, uncomp_len)
        total_uncompressed += uncomp_len
        chunks.append((name, body))
        pos = body_start + stored
        if name == b"END\x00":
            break
    if pos != len(data):
        raise RbxmCorruptError(
            "data za END chunkem (%d B navic)" % (len(data) - pos))
    return chunks


def _parse_meta(body):
    """META: u32 pocet + dvojice retezcu klic/hodnota.

    Duplicitni klic = poskozeny soubor (tiche prepsani by ztratilo data).
    """
    count = _u32(body, 0)
    if count > MAX_META_ENTRIES:
        raise RbxmCorruptError(
            "absurdni pocet META zaznamu: %d" % count)
    pos = 4
    meta = {}
    for _ in range(count):
        if pos >= len(body):
            raise RbxmCorruptError("META: useknuty zaznam")
        key, pos = _read_string(body, pos)
        value, pos = _read_string(body, pos)
        if key in meta:
            raise RbxmCorruptError(
                "META: duplicitni klic %r" % key)
        meta[key] = value
    if pos != len(body):
        raise RbxmCorruptError("META: prebytecna data (%d B)" % (len(body)
                                                                 - pos))
    return meta


def _parse_sstr(body):
    """SSTR: precte jen pocet sdilenych retezcu. Neprazdna tabulka neni
    poskozeni, ale nepodporovany obsah (inline-Name by pak nemusela
    byt uplna) -> RbxmUnsupportedError."""
    if len(body) < 4:
        raise RbxmCorruptError("SSTR: telo kratsi nez 4 B")
    shared = _u32(body, 0)
    if shared != 0:
        raise RbxmUnsupportedError(
            "SSTR: sdilena tabulka (%d) neni podporovana; "
            "jmena by nemusela byt uplna" % shared)
    return {"shared_strings": 0, "opaque_bytes": len(body) - 4}


def _parse_inst(body, seen_ids, seen_type_ids):
    """INST: typ + referenty. Duplicitni ID nebo typ = poskozeny soubor."""
    if len(body) < 4:
        raise RbxmCorruptError("INST: telo kratsi nez type_id")
    (type_id,) = struct.unpack("<i", body[0:4])
    if type_id in seen_type_ids:
        raise RbxmCorruptError("duplicitni INST typ: %d" % type_id)
    name, pos = _read_string(body, 4)
    if not name:
        raise RbxmCorruptError("INST: prazdne jmeno tridy")
    if pos >= len(body):
        raise RbxmCorruptError("INST %s: chybi is_service" % name)
    is_service = body[pos]
    if is_service not in (0, 1):
        raise RbxmCorruptError(
            "INST %s: neplatne is_service=%d (ocekavano 0/1)"
            % (name, is_service))
    pos += 1
    count = _u32(body, pos)
    pos += 4
    if count > MAX_FIELD_VALUES:
        raise RbxmCorruptError("INST %s: absurdni pocet %d (cap %d)"
                               % (name, count, MAX_FIELD_VALUES))
    referents = _decode_referents(body[pos:], count, "INST %s" % name)
    for ref in referents:
        if ref < 0:
            raise RbxmCorruptError(
                "INST %s: zaporny referent %d" % (name, ref))
        if ref in seen_ids:
            raise RbxmCorruptError("duplicitni instance id: %d" % ref)
        seen_ids.add(ref)
    seen_type_ids.add(type_id)
    return {"type_id": type_id, "class_name": name,
            "is_service": is_service, "referents": referents}


def _parse_name_prop(body, expected_count):
    """Name PROP (typ string 0x01): inline retezce, pocet musi sedet."""
    if len(body) < 4:
        raise RbxmCorruptError("PROP/Name: telo kratsi nez type_id")
    (type_id,) = struct.unpack("<i", body[0:4])
    prop_name, pos = _read_string(body, 4)
    if pos >= len(body):
        raise RbxmCorruptError("PROP/Name: chybi typ hodnoty")
    if expected_count > MAX_FIELD_VALUES:
        raise RbxmCorruptError(
            "PROP/Name: absurdni pocet jmen %d (cap %d); bezpecne odmitnuto"
            % (expected_count, MAX_FIELD_VALUES))
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


def _ancestor_chain(instance_id, parent_of):
    """Retez predku od primeho rodice ke koreni (pro geometricke posouzeni).

    Pri cyklu nebo chybejicim rodici vyhodi RbxmHierarchyError — volajici
    to mapuje na BLOCKED, nikdy na validni vysledek.
    """
    chain = []
    seen = {instance_id}
    parent = parent_of.get(instance_id)
    while parent is not None:
        if parent in seen:
            raise RbxmHierarchyError(
                "cyklus v parent hierarchii u instance %r" % instance_id)
        if parent not in parent_of:
            raise RbxmHierarchyError(
                "neplatny parent id %r u instance %r" % (parent,
                                                         instance_id))
        seen.add(parent)
        chain.append(parent)
        parent = parent_of.get(parent)
    return chain


def _clusters(values):
    """Shluky hodnot s toleranci 0.06 (pro obdelnik kol)."""
    groups = []
    for value in sorted(values):
        if groups and abs(value - groups[-1][-1]) <= 0.06:
            groups[-1].append(value)
        else:
            groups.append([value])
    return groups


def parse_bytes(data):
    """Parsuje RBXM data z pameti; vrati dict modelu (viz parse_rbxm)."""
    # P2-6: odmitnout ne-bytes vstup jako RbxmCorruptError (misto uniku
    # TypeError z bytes(str) / bytes(None)); P1-1: delku kontrolovat PRED
    # kopii — len() kopii nepotrebuje, bytes(bytearray/memoryview) ano.
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise RbxmCorruptError(
            "ocekavan bytes/bytearray/memoryview, ne %s; bezpecne odmitnuto"
            % type(data).__name__)
    if len(data) > MAX_FILE_BYTES:
        raise RbxmCorruptError(
            "soubor presahuje limit (%d > %d B); bezpecne odmitnuto"
            % (len(data), MAX_FILE_BYTES))
    data = bytes(data)
    num_types, num_instances = _parse_header(data)
    chunks = _read_chunks(data)

    census = {}
    skipped_chunks = []
    meta = {}
    sstr_info = None
    inst_list = []
    seen_ids = set()
    seen_type_ids = set()
    name_prop_bodies = []
    geom_prop_bodies = []
    skipped_props = []
    decoded_prop_keys = set()
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
            inst_list.append(_parse_inst(body, seen_ids, seen_type_ids))
        elif name == b"PROP":
            if len(body) < 8:
                raise RbxmCorruptError("PROP: telo kratsi nez 8 B")
            prop_name, name_end = _read_string(body, 4)
            if name_end >= len(body):
                raise RbxmCorruptError("PROP %r: chybi typ hodnoty"
                                       % prop_name)
            value_type = body[name_end]
            if prop_name == "Name":
                if value_type != 0x01:
                    (prop_type_id,) = struct.unpack("<i", body[0:4])
                    raise RbxmCorruptError(
                        "PROP/Name typu %d ma ne-retezcovy typ 0x%02x; "
                        "identita by nebyla uplna" % (prop_type_id,
                                                      value_type))
                name_prop_bodies.append(body)
            elif prop_name in ("shape", "size", "CFrame", "CFrame0",
                               "PivotOffset"):
                geom_prop_bodies.append(body)
            else:
                (prop_type_id,) = struct.unpack("<i", body[0:4])
                skipped_props.append({
                    "type_id": prop_type_id,
                    "prop_name": prop_name,
                    "value_type": "0x%02x" % value_type,
                    "status": "unread",
                    "reason": ("typ vlastnosti se v M2 neinterpretuje; "
                               "hodnoty nejsou k dispozici"),
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
    if prnt_seen != 1:
        raise RbxmCorruptError("chybi prave jeden PRNT chunk")
    if sstr_info is None:
        sstr_info = {"shared_strings": 0, "opaque_bytes": 0}
    if prnt_body is None:
        raise RbxmCorruptError("chybi PRNT telo (interni chyba)")

    type_by_id = {entry["type_id"]: entry for entry in inst_list}
    ref_pos = {}
    for entry in inst_list:
        ref_pos[entry["type_id"]] = {ref: i
                                     for i, ref in
                                     enumerate(entry["referents"])}

    def _type_count(type_id):
        """Pocet instanci typu (0 = neznamy typ)."""
        entry = type_by_id.get(type_id)
        if entry is None:
            return 0
        return len(entry["referents"])

    # Name PROP se vyhodnocuji az po vsech INST (poradi chunku neni dane).
    # Chybejici jmeno nikdy neznamena rozpoznany objekt (name_status).
    name_by_type = {}
    for body in name_prop_bodies:
        (prop_type_id,) = struct.unpack("<i", body[0:4])
        if prop_type_id not in type_by_id:
            raise RbxmCorruptError(
                "PROP/Name pro neznamy typ %d" % prop_type_id)
        type_id, names = _parse_name_prop(
            body, _type_count(prop_type_id))
        if type_id in name_by_type:
            raise RbxmCorruptError(
                "duplicitni PROP/Name pro typ %d" % type_id)
        name_by_type[type_id] = names

    # Geometricke PROP se vyhodnocuji stejne az po INST (pocet musi sedet
    # s poctem instanci typu; poradi chunku neni dane).
    shape_by_type = {}
    size_by_type = {}
    cframe_by_type = {}
    for body in geom_prop_bodies:
        (prop_type_id,) = struct.unpack("<i", body[0:4])
        prop_name, name_end = _read_string(body, 4)
        value_type = body[name_end]
        payload = body[name_end + 1:]
        if prop_type_id not in type_by_id:
            raise RbxmCorruptError(
                "PROP/%s pro neznamy typ %d" % (prop_name, prop_type_id))
        key = (prop_type_id, prop_name)
        if key in decoded_prop_keys:
            raise RbxmCorruptError(
                "duplicitni PROP/%s pro typ %d" % (prop_name,
                                                  prop_type_id))
        decoded_prop_keys.add(key)
        count = _type_count(prop_type_id)
        if prop_name == "shape" and value_type == 0x12:
            shape_by_type[prop_type_id] = _decode_enum_lanes(
                payload, count, "PROP/shape typu %d" % prop_type_id)
        elif prop_name == "size" and value_type == 0x0E:
            comps = _decode_float_lanes(
                payload, count, "PROP/size typu %d" % prop_type_id)
            size_by_type[prop_type_id] = list(zip(comps[0], comps[1],
                                                 comps[2]))
        elif prop_name in ("CFrame", "CFrame0", "PivotOffset") \
                and value_type == 0x10:
            ids, matrices, comps = _parse_cframe_array(
                payload, count,
                "PROP/%s typu %d" % (prop_name, prop_type_id))
            cframe_by_type[key] = {
                "ids": ids,
                "matrices": matrices,
                "positions": list(zip(comps[0], comps[1], comps[2])),
            }
        else:
            skipped_props.append({
                "type_id": prop_type_id,
                "prop_name": prop_name,
                "value_type": "0x%02x" % value_type,
                "status": "unread",
                "reason": ("kombinace jmeno/typ se v M2 neinterpretuje; "
                           "hodnoty nejsou k dispozici"),
            })

    if len(prnt_body) < 5:
        raise RbxmCorruptError("PRNT: telo kratsi nez 5 B")
    if prnt_body[0] != 0:
        raise RbxmUnsupportedError(
            "PRNT: nepodporovana verze %d" % prnt_body[0])
    prnt_count = _u32(prnt_body, 1)
    if prnt_count > MAX_FIELD_VALUES:
        raise RbxmCorruptError(
            "PRNT: absurdni pocet %d (cap %d); bezpecne odmitnuto"
            % (prnt_count, MAX_FIELD_VALUES))
    if prnt_count != num_instances:
        raise RbxmCorruptError(
            "PRNT: pocet %d != num_instances %d" % (prnt_count,
                                                    num_instances))
    payload = prnt_body[5:]
    if len(payload) != 8 * prnt_count:
        raise RbxmCorruptError("PRNT: spatna delka dat")
    kids = _decode_referents(payload[:4 * prnt_count], prnt_count,
                             "PRNT kids")
    parents = _decode_referents(payload[4 * prnt_count:], prnt_count,
                                "PRNT parents")
    # Zadne predpoklady souvislosti: mnozina deti se musi rovnat mnozine
    # referentu (poradi ani rozsah 0..n se nepredpoklada); duplicity deti
    # a rodice mimo referenty jsou chyba.
    if len(set(kids)) != len(kids):
        raise RbxmCorruptError("PRNT: duplicitni dite v parent vazbach")
    if set(kids) != seen_ids:
        raise RbxmCorruptError(
            "PRNT: mnozina deti neodpovida mnozine referentu INST")
    parent_of = {}
    for child, parent in zip(kids, parents):
        if parent != NULL_PARENT and parent not in seen_ids:
            raise RbxmHierarchyError(
                "neplatny parent id %r u instance %r" % (parent, child))
        parent_of[child] = None if parent == NULL_PARENT else parent
    _check_hierarchy(parent_of)
    roots = [rid for rid, parent in parent_of.items() if parent is None]
    if len(roots) != 1:
        raise RbxmHierarchyError(
            "les: ocekavan prave 1 koren, nalezeno %d" % len(roots))

    class_by_id = {}
    ref_to_type = {}
    for entry in inst_list:
        for ref in entry["referents"]:
            class_by_id[ref] = entry["class_name"]
            # P1-5: mapa ref->type postavena jednou (O(n)); drivejsi
            # next(... if ref in ref_pos[...]) za kazdou instanci bylo
            # O(num_types x num_instances).
            ref_to_type[ref] = entry["type_id"]
    names_full = {}
    for entry in inst_list:
        names = name_by_type.get(entry["type_id"])
        if names is None:
            continue  # jmeno chybi -> None (evidovano nize)
        for ref, text in zip(entry["referents"], names):
            names_full[ref] = text

    float_reason = ("floaty bez Studio ground-truth; kalibrace studs/m "
                    "NOT IMPLEMENTED (viz calibrate_studs_per_meter)")
    instances = []
    for ref in sorted(seen_ids):
        class_name = class_by_id[ref]
        try:
            type_id = ref_to_type[ref]
        except KeyError:
            raise RbxmCorruptError(
                "chybejici typ pro referent %r (interni chyba)" % (ref,))
        pos_in_type = ref_pos[type_id][ref]
        name = names_full.get(ref)
        props = {}

        shape_values = shape_by_type.get(type_id)
        if shape_values is not None:
            raw = shape_values[pos_in_type]
            shape_name = PART_TYPE_NAMES.get(raw)
            if shape_name is not None:
                props["shape"] = {
                    "status": "read", "trusted": True,
                    "how": ("PROP shape enum u32 lane LSB-prvni; "
                            "mapovano PartType Ball/Block/Cylinder"),
                    "value": shape_name,
                }
                shape = shape_name
            else:
                props["shape"] = {
                    "status": "unread", "trusted": False,
                    "how": "PROP shape enum u32 lane LSB-prvni",
                    "reason": ("neznama hodnota enum %d; tvar se neodhaduje"
                               % raw),
                    "value": None,
                }
                shape = None
        elif class_name == "Part":
            props["shape"] = {
                "status": "missing", "trusted": False,
                "reason": "trida Part bez PROP shape; tvar se neodvozuje",
                "value": None,
            }
            shape = None
        else:
            shape = None

        size_values = size_by_type.get(type_id)
        if size_values is not None:
            size = tuple(size_values[pos_in_type])
            props["size"] = {
                "status": "read", "trusted": False,
                "how": ("PROP size Vector3: component-major, 4 lane "
                        "MSB-prvni, u32 ror1"),
                "reason": float_reason,
                "value": size,
            }
        elif class_name in ("Part", "UnionOperation", "VehicleSeat"):
            props["size"] = {
                "status": "missing", "trusted": False,
                "reason": "trida %s bez PROP size; rozmer se neodvozuje"
                          % class_name,
                "value": None,
            }
            size = None
        else:
            size = None

        cframe = cframe_by_type.get((type_id, "CFrame"))
        if cframe is not None:
            position = tuple(cframe["positions"][pos_in_type])
            matrix = cframe["matrices"][pos_in_type]
            orient_id = cframe["ids"][pos_in_type]
            if matrix is None:
                rotation = None
                rotation_status = "unread-preset-%d" % orient_id
            elif orient_id == ORIENT_IDENTITY:
                rotation = "identity"
                rotation_status = "identity-preset (tabulka neoverena)"
            else:
                rotation = tuple(matrix)
                rotation_status = "matrix"
            props["CFrame"] = {
                "status": "read", "trusted": False,
                "how": ("PROP CFrame: orientacni bloky [u8 id + 9x f32 LE] "
                        "pak pozice float lane (viz size)"),
                "reason": float_reason,
                "value": {"position": position, "rotation": rotation},
                "rotation_status": rotation_status,
            }
        elif class_name in ("Part", "UnionOperation", "VehicleSeat",
                            "Attachment"):
            props["CFrame"] = {
                "status": "missing", "trusted": False,
                "reason": ("trida %s bez PROP CFrame; stred a natoceni "
                           "se neodvozuji" % class_name),
                "value": None,
            }
            position = None
            rotation = None
        else:
            position = None
            rotation = None

        for extra in ("CFrame0", "PivotOffset"):
            extra_data = cframe_by_type.get((type_id, extra))
            if extra_data is None:
                continue
            matrix = extra_data["matrices"][pos_in_type]
            orient_id = extra_data["ids"][pos_in_type]
            if matrix is None:
                extra_rotation = None
                extra_status = "unread-preset-%d" % orient_id
            elif orient_id == ORIENT_IDENTITY:
                extra_rotation = "identity"
                extra_status = "identity-preset (tabulka neoverena)"
            else:
                extra_rotation = tuple(matrix)
                extra_status = "matrix"
            props[extra] = {
                "status": "read", "trusted": False,
                "how": "PROP %s: stejne kodovani jako CFrame" % extra,
                "reason": float_reason,
                "value": {
                    "position": tuple(
                        extra_data["positions"][pos_in_type]),
                    "rotation": extra_rotation,
                },
                "rotation_status": extra_status,
            }

        instances.append({
            "id": ref,
            "class_name": class_name,
            "name": name,
            "name_status": "present" if name is not None else "missing",
            # Tvar/rozmery/geometrie: prectene hodnoty s provenienci
            # v props; chybejici jmeno nikdy neznamena rozpoznany objekt.
            "shape": shape,
            "size": size,
            "position": position,
            "rotation": rotation,
            "props": props,
            "parent_id": parent_of[ref],
        })

    unnamed_ids = sorted(i["id"] for i in instances if i["name"] is None)
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
        "missing_name_count": len(unnamed_ids),
        "unnamed_ids": unnamed_ids,
        "limits": {
            "max_file_bytes": MAX_FILE_BYTES,
            "max_total_uncompressed_bytes": MAX_TOTAL_UNCOMPRESSED,
            "max_chunks": MAX_CHUNKS,
            "max_instances": MAX_INSTANCES,
        },
        "geometry": {
            "status": "PARTIAL",
            "note": ("shape/size/CFrame precteny s provenienci u kazde "
                     "vlastnosti; floaty (size, pozice, matice) jsou "
                     "strukturalne overeny, ale bez Studio ground-truth "
                     "nedurveryhodne ke kalibraci; geometrie se NIKDY "
                     "neodvozuje z nazvu"),
            "calibration": {
                "studs_per_meter": None,
                "unit": "studs/m",
                "status": "NOT_IMPLEMENTED",
                "reason": ("chybi Studio ground-truth (kalibracni dil zname "
                           "velikosti odecteny ve Studiu); meritko nelze "
                           "prohlasit za overene"),
            },
        },
    }


def parse_rbxm(path):
    """Parsuje RBXM soubor, pouze pro cteni (open 'rb').

    Velikost se kontroluje pred nactenim (MAX_FILE_BYTES) i pri cteni
    (read s limitem MAX_FILE_BYTES+1, takze soubor narostly mezi getsize
    a read (TOCTOU) se odmitne po alokaci nejvyse ~8 MiB, ne celem GB);
    soubor se nikdy neotevira k zapisu; pred/po kontrolu hashe dela
    volajici (testy, G-01 brana).
    """
    # Rychla cesta (poradni, ne bezpecnostni kontrola): getsize muze byt
    # v okamziku read uz neplatne (TOCTOU).
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            raise RbxmCorruptError(
                "soubor %r presahuje limit %d B; bezpecne odmitnuto"
                % (path, MAX_FILE_BYTES))
    except OSError:
        pass
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        # AUDIT2-parser-security: souborove selhani (chybejici soubor,
        # prava, adresar) patri do RbxmError kontraktu, nikdy ven.
        raise RbxmCorruptError(
            "soubor %r nelze precist: %s; bezpecne odmitnuto"
            % (path, exc)) from exc
    if len(data) > MAX_FILE_BYTES:
        raise RbxmCorruptError(
            "soubor %r presahuje limit %d B; bezpecne odmitnuto"
            % (path, MAX_FILE_BYTES))
    return parse_bytes(data)


def _is_rotation_matrix(matrix, tol=1e-3):
    """Ortonormalita 3x3 matice v toleranci (radky jednotkove, kolme,
    determinant +1). Neortonomalni/skalicí matice neni rotace."""
    rows = (matrix[0:3], matrix[3:6], matrix[6:9])
    for a in range(3):
        if abs(sum(v * v for v in rows[a]) - 1.0) > tol:
            return False
        for b in range(a + 1, 3):
            if abs(sum(x * y for x, y in zip(rows[a], rows[b]))) > tol:
                return False
    a, b, c, d, e, f, g, h, i = matrix
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return abs(det - 1.0) <= tol


def assess_wheel_geometry(instances):
    """Posouzeni kol skutecnou geometrii (stredy, rozmery).

    Zrcadli identitni pravidlo wheel_detect.py (a) v Model:Wheels +
    (b) FL/FR/RL/RR + (c) tvar Ball — wheel_detect.py se NEMENI, tato
    funkce pridava geometrickou vrstvu: sphericitu, shodu rozmeru,
    obdelnikove rozmisteni stredu a evidenci floatu.

    Vraci dict: {wheels, unidentified, blocked, blocked_reasons,
    status, calibration}. V M2 je vysledek vzdy BLOCKED: bud pro
    geometrickou nejednoznacnost (chybejici/neplatna data, asymetrie),
    nebo — i pri plne konzistentni geometrii — pro neoverenou
    kalibraci (floaty bez Studio ground-truth, NOT IMPLEMENTED).
    OK vyzaduje M3 (Studio ground-truth + overena kalibrace).
    """
    result = {"wheels": {}, "unidentified": [],
              "blocked": False, "blocked_reasons": [], "status": "OK",
              "calibration": {
                  "studs_per_meter": None,
                  "unit": "studs/m",
                  "status": "NOT_IMPLEMENTED",
                  "reason": ("bez Studio ground-truth nelze overit "
                             "dekodovani floatu ani meritko"),
              }}

    def block(reason):
        if reason not in result["blocked_reasons"]:
            result["blocked_reasons"].append(reason)
        result["blocked"] = True
        result["status"] = "BLOCKED"

    index = {}
    for inst in instances:
        iid = inst.get("id")
        if iid in index:
            block("duplicate instance id: %r" % (iid,))
            return result
        index[iid] = inst

    wheels_models = [i for i in instances
                     if i.get("class_name") == "Model"
                     and i.get("name") == WHEELS_MODEL_NAME]
    if not wheels_models:
        block("missing Model:Wheels")
        return result
    if len(wheels_models) > 1:
        block("ambiguous Model:Wheels: found %d" % len(wheels_models))
        return result
    wheels_id = wheels_models[0].get("id")

    # Les (vice korenu) neni strom M2 drahy kol: explicitni politika
    # BLOCKED (format-audit §3/F2), nikdy tichy pruchod.
    roots = [i.get("id") for i in instances if i.get("parent_id") is None]
    if len(roots) != 1:
        block("forest: ocekavan prave 1 koren, nalezeno %d" % len(roots))
        return result

    parent_of = {i.get("id"): i.get("parent_id") for i in instances}

    # P2-7: memoizovane retezy predku (amortizovane O(n) misto O(d^2)).
    # Semantika stejna jako _ancestor_chain: cyklus / neplatny parent
    # -> RbxmHierarchyError pro danou instanci. Sufixy sdilene mezi Party
    # se pocitaji jednou (kazdy uzel se navstivi nejvyse jednou).
    chain_memo = {}

    def cached_inside(target_id, start_id):
        """Je target_id v retezu predku start_id? Memoizovane, sdili sufixy."""
        if start_id in chain_memo:
            return target_id in chain_memo[start_id]
        chain = []
        seen = {start_id}
        parent = parent_of.get(start_id)
        prefix = []  # nove navstivene uzly od start_id vzhuru
        while parent is not None:
            if parent in seen:
                raise RbxmHierarchyError(
                    "cyklus v parent hierarchii u instance %r" % start_id)
            if parent not in parent_of:
                raise RbxmHierarchyError(
                    "neplatny parent id %r u instance %r" % (parent,
                                                             start_id))
            if parent in chain_memo:
                chain.append(parent)
                chain.extend(chain_memo[parent])
                break
            seen.add(parent)
            chain.append(parent)
            prefix.append(parent)
            parent = parent_of.get(parent)
        chain_memo[start_id] = chain
        # Sufixy nove projdenych uzlu si pamatujeme take (sdileni prace).
        # Retez je striktni (bez sebe sama): predci uzlu prefix[idx]
        # = chain[idx+1:].
        for idx, node in enumerate(prefix):
            if node not in chain_memo:
                chain_memo[node] = chain[idx + 1:]
        return target_id in chain

    parts_in_wheels = []
    for inst in instances:
        if inst.get("id") == wheels_id:
            continue
        if inst.get("class_name") != "Part":
            continue
        try:
            inside = cached_inside(wheels_id, inst.get("id"))
        except RbxmHierarchyError as exc:
            result["unidentified"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "failed_checks": ["hierarchy"],
            })
            block(str(exc))
            continue
        if inside:
            parts_in_wheels.append(inst)

    by_name = {}
    for inst in parts_in_wheels:
        by_name.setdefault(inst.get("name"), []).append(inst)

    for des in WHEEL_DESIGNATIONS:
        cands = by_name.get(des, [])
        if len(cands) != 1:
            result["wheels"][des] = {
                "status": "UNKNOWN",
                "instance_id": None,
                "failed_checks": ["missing_wheel" if not cands
                                  else "duplicate_designation"],
            }
            block("wheel %s: ocekavano 1, nalezeno %d"
                  % (des, len(cands)))
            continue
        inst = cands[0]
        failed = []
        props = inst.get("props", {})
        if inst.get("shape") != WHEEL_SHAPE:
            failed.append("bad_shape")
        size = inst.get("size")
        size_entry = props.get("size", {})
        if size is None or size_entry.get("status") != "read":
            failed.append("missing_size")
            size = None
        elif not all(isinstance(v, float) for v in size):
            failed.append("bad_size")
            size = None
        elif not all(math.isfinite(v) for v in size):
            # Inf/NaN neni "nonpositive_size" ani koule — vlastni label,
            # nikdy GEOMETRY_OK (P0: inf driv prosel jako GEOMETRY_OK).
            failed.append("nonfinite_size")
            size = None
        elif not all(v > 0 for v in size):
            failed.append("nonpositive_size")
            size = None
        elif max(size) - min(size) > 0.01 * max(size):
            failed.append("nonspherical")
        position = inst.get("position")
        pos_entry = props.get("CFrame", {})
        if position is None or pos_entry.get("status") != "read":
            failed.append("missing_position")
            position = None
        elif not (isinstance(position, (tuple, list))
                  and len(position) == 3
                  and all(isinstance(v, float) for v in position)):
            failed.append("bad_position")
            position = None
        elif not all(math.isfinite(v) for v in position):
            # Inf/NaN pozice driv prosla per-kolo verdiktem (P0).
            failed.append("nonfinite_position")
            position = None
        rotation = inst.get("rotation")
        if pos_entry.get("status") == "read":
            if rotation is None:
                # Znama preseta "identity" ma rotation="identity" (retezec);
                # None pri ctenem CFrame = neoverena preseta bez matice.
                failed.append("unread_rotation")
            elif isinstance(rotation, str):
                pass  # "identity": ortonormalni trivialne, tabulka viz audit
            elif not (isinstance(rotation, (tuple, list))
                      and len(rotation) == 9
                      and all(isinstance(v, float)
                              for v in rotation)):
                failed.append("bad_rotation")
            elif not all(math.isfinite(v) for v in rotation):
                failed.append("nonfinite_rotation")
            elif not _is_rotation_matrix(tuple(rotation)):
                failed.append("invalid_rotation")
        if failed:
            result["wheels"][des] = {
                "status": "UNKNOWN",
                "instance_id": inst.get("id"),
                "shape": inst.get("shape"),
                "size": size,
                "position": position,
                "failed_checks": failed,
            }
            block("wheel %s (id %r) geometricky nejednoznacne: %s"
                  % (des, inst.get("id"), ",".join(failed)))
        else:
            result["wheels"][des] = {
                "status": "GEOMETRY_OK",
                "instance_id": inst.get("id"),
                "shape": inst.get("shape"),
                "size": size,
                "position": position,
                "failed_checks": [],
            }

    for inst in parts_in_wheels:
        if inst.get("name") not in WHEEL_DESIGNATIONS:
            result["unidentified"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "failed_checks": ["not_a_wheel"],
            })
    if result["unidentified"]:
        block("UNKNOWN candidate(s) inside Model:Wheels: %d"
              % len(result["unidentified"]))

    good = [w for w in result["wheels"].values()
            if w.get("status") == "GEOMETRY_OK"]
    if len(good) == 4:
        sizes = [w["size"] for w in good]
        positions = [w["position"] for w in good]
        if (not all(isinstance(v, float) and math.isfinite(v)
                   for s in sizes for v in s)
                or not all(isinstance(v, float) and math.isfinite(v)
                           for p in positions for v in p)):
            # Obranna brana pred krizovymi vypocty: nekonecna hodnota
            # se sem po per-kolo kontrolach nesmi dostat; kdyby ano,
            # zadny layout-vyrok, jen BLOCKED.
            block("nonfinite wheel geometry in cross-check")
        else:
            ref = sum(sum(s) for s in sizes) / 12.0
            if any(abs(v - ref) > 0.01 * ref
                   for s in sizes for v in s):
                block("inconsistent wheel sizes: %r" % (sizes,))
            xs = sorted(p[0] for p in positions)
            ys = [p[1] for p in positions]
            zs = sorted(p[2] for p in positions)
            x_cls = _clusters(xs)
            z_cls = _clusters(zs)
            if len(x_cls) != 2 or len(z_cls) != 2:
                block("wheel layout not rectangular: x=%r z=%r"
                      % (xs, zs))
            elif max(ys) - min(ys) > 0.05:
                block("wheel heights differ: %r" % (ys,))
            else:
                have = set()
                for p in positions:
                    xi = 0 if abs(p[0] - x_cls[0][0]) <= 0.06 else 1
                    zi = 0 if abs(p[2] - z_cls[0][0]) <= 0.06 else 1
                    if abs(p[0] - x_cls[xi][0]) > 0.06 \
                            or abs(p[2] - z_cls[zi][0]) > 0.06:
                        xi = zi = -1
                    have.add((xi, zi))
                if have != {(0, 0), (0, 1), (1, 0), (1, 1)}:
                    block("wheel layout not a 2x2 grid: %r" % (positions,))
    elif not result["blocked"]:
        block("identified wheels != 4 (got %d)" % len(good))

    block("float_decode_unverified: rozmery a stredy jsou precteny, "
          "ale bez Studio ground-truth nedurveryhodne ke kalibraci "
          "(kalibrace studs/m NOT IMPLEMENTED)")
    return result


def calibrate_studs_per_meter(known_meters=None, measured_studs=None):
    """Priprava rozhrani kalibrace studs/m (M2): vzdy NOT IMPLEMENTED.

    Bez Studio ground-truth (kalibracni dil zname velikosti odecteny
    ve Studiu) nelze overit dekodovani floatu ani meritko, proto
    kalibrace v M2 pouze existuje jako rozhrani + provenience a nikdy
    nevraci overenou hodnotu. Overeni je ukol M3.
    """
    return {
        "status": "NOT_IMPLEMENTED",
        "studs_per_meter": None,
        "unit": "studs/m",
        "reason": ("chybi Studio ground-truth: kalibracni dil zname "
                   "velikosti odecteny ve Studiu; dekodovani floatu "
                   "(ror1 lane) je strukturalne overeno, ale meritko "
                   "nelze prohlasit za overene"),
        "needs": ["studio-measured reference part",
                  "verified float decoding (M3 ground-truth)"],
        "inputs_ignored": (known_meters is not None
                           or measured_studs is not None),
    }

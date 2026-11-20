#!/usr/bin/env python3
"""Validace normalizace Agent E — zesílená (E1–E6). Jen stdlib.

Čte reports/NIGHT-WORK/normalized_ids.json + zdrojovou mapovací tabulku
Agenta F a ověřuje:

E1  vztah každého záznamu k deklarovanému zdroji — logical_id musí být
    ve SKUTEČNÉ buňce Interní ID daného source_rows řádku (parsuje obsah
    buňky, ne jen číslo), žádné ID k cizímu řádku, žádné multi-přiřazení,
    alias není ID, rozbalení skupin dle R1–R8 (neurčitelné → PENDING/
    UNKNOWN, nikdy vymyšlené ID);
E2  pravidla R1–R8 jako automatické kontroly;
E3  provenance statusu — VERIFIED bez evidence = FAIL; věcně
    neověřitelné → ruční review / PENDING;
E4  tři oddělené počty SOURCE_TABLE_ROWS / ORIGINAL_LOGICAL_IDS /
    NORMALIZED_IDS + EXPANDED / ALIASES / UNRESOLVED — vše vypočteno;
E5  exit 0 = PASS / 1 = chyba / 2 = PENDING (60 nedoloženo → exit ≠ 0).

Knihovna: evaluate()/load_doc()/parse_f_rows()/expand_cell_ids() jsou
importovatelné pro tests/test_normalization_validation.py.
"""
import copy
import hashlib
import json
import os
import re
import sys
from collections import Counter

ALLOWED = {"VERIFIED", "ESTIMATED", "PENDING", "UNKNOWN"}

# Hodnoty, které nejsou důkazem (E3): prázdné, pomlčky, holé UNKNOWN.
PRAZDNE = {"", "-", "–", "—", "n/a", "N/A", "null", "None"}


def repo_root():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, ".."))


def git_blob_sha(data: bytes) -> str:
    """SHA-1 ve formátu git blob (jen hashlib).

    Normalizuje CRLF → LF, tj. stejná sémantika jako git hash-object
    při core.autocrlf=true: pracovní strom na Windows obsahuje CRLF,
    v repozitáři je uloženo LF.
    """
    norm = data.replace(bytes([13, 10]), bytes([10]))
    return hashlib.sha1(b"blob %d\0" % len(norm) + norm).hexdigest()


def split_row(line):
    tmp = line.replace("\\|", "\x00")
    parts, cur, inbt = [], "", False
    for ch in tmp:
        if ch == "`":
            inbt = not inbt
            cur += ch
        elif ch == "|" and not inbt:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [x.strip().replace("\x00", "|") for x in parts[1:-1]]


def parse_f_rows(path):
    """Řádky tabulek §2.1–§2.10: [(číslo_řádku, [sloupce...]), ...]."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    in_s2, rows = False, []
    for i, l in enumerate(lines, 1):
        if l.startswith("## 2."):
            in_s2 = True
        if re.match(r"## 3\.", l) and in_s2:
            break
        if in_s2 and l.startswith("| `"):
            c = split_row(l)
            if len(c) == 10:  # známá formální vada L55: chybí separator
                c = c[:8] + ["<chybí sloupec>"] + c[8:]
            rows.append((i, c))
    return rows


def expand_cell_ids(cell):
    """Rozbal buňku Interní ID dle R2 na seznam katalogových ID.

    - `a` / `b` → [a, b]                      (oddělené buňky jedním řádkem)
    - `slip_thresh_f/r/c` → 3 ID (přípony f/r/c)
    - `clutch_*` (enabled/engage/...) → clutch_enabled, ...
    Neurčitelné se nerozbaluje (vrátí jen to, co je v buňce doslova).
    """
    toks = re.findall(r"`([^`]+)`", cell)
    ids = []
    for tok in toks:
        tok = tok.strip()
        if not tok:
            continue
        if tok.endswith("_*"):  # clutch_* + výčet v závorce
            m = re.search(r"\(([^)]*)\)", cell)
            members = re.split(r"[/,]", m.group(1)) if m else []
            for mm in members:
                mm = mm.strip().strip("`").strip()
                if mm and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", mm):
                    ids.append(tok[:-1] + mm)
        elif "/" in tok:
            parts = [p.strip() for p in tok.split("/")]
            if (all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", p)
                    or p in ("f", "r", "c") for p in parts)
                    and not all("_" in p for p in parts)):
                base = parts[0].rsplit("_", 1)[0]  # f/r/c přípony
                for p in parts:
                    ids.append(p if "_" in p else base + "_" + p)
            else:
                ids.extend([p for p in parts if p])
        elif re.fullmatch(r"[a-z][a-z0-9_]*", tok):
            ids.append(tok)
    # pořadí zachovat, duplicity v buňce shodit
    return list(dict.fromkeys(ids))


def je_dukaze(text):
    """E3: je řetězec věcným důkazem (ne pomůcka / holé UNKNOWN)?"""
    if not isinstance(text, str):
        return False
    t = text.strip()
    return t not in PRAZDNE and not t.startswith("UNKNOWN")


# Doložené F/R páry (R8): povolené dvojice, odvozené z katalogu
# (odlišné tune_key) a zdrojové tabulky. Nový pár jen doloženým
# zápisem sem — nikdy automaticky podle přípony.
FR_PAIRS = [
    ("anchor_offset_f", "anchor_offset_r"),
    ("compress_lim_f", "compress_lim_r"),
    ("damper_f", "damper_r"),
    ("diff_preload_f", "diff_preload_r"),
    ("downforce_f", "downforce_r"),
    ("extension_lim_f", "extension_lim_r"),
    ("lock_thresh_f", "lock_thresh_r"),
    ("pre_compress_f", "pre_compress_r"),
    ("slip_thresh_f", "slip_thresh_r"),
    ("sus_angle_f", "sus_angle_r"),
    ("sus_length_f", "sus_length_r"),
    ("sus_stiffness_f", "sus_stiffness_r"),
]
# Doložené L/R páry (R8): v datech ani katalogu zatím žádný výskyt
# `_l`/`left` — prázdná množina, kontrolní větev je připravena.
LR_PAIRS = []

# Slova značící doloženou metodu původu (E3, ESTIMATED).
METODA_SLOVA = {"výpočet", "vypocet", "odvozen", "derive", "metoda",
                "method", "vzorec", "konstrukč", "konstrukc", "měření",
                "mereni", "audit", "profil", "ford"}


def je_hodnota(text):
    """Strojový proxy 'konkrétní hodnoty' (E3, VERIFIED mustang_cil).

    Číselná hodnota (obsahuje číslici) nebo velkopísmenný kód
    ('RWD' projde; odmítne 'xxx', 'odhad', 'n/a (RWD)').
    """
    if not je_dukaze(text):
        return False
    t = text.strip()
    if len(t) < 2:
        return False
    if re.search(r"[0-9]", t):
        return True
    return bool(re.match(r"^[A-Z0-9]", t))


def ma_lokator(text):
    """Má zdroj dohledatelný lokátor (E3): §, #L, zpětné uvozovky,
    hranatá reference [1b], nebo explicitní schéma/oddíl?"""
    if not je_dukaze(text):
        return False
    t = text.strip()
    if len(t) < 4:
        return False
    return ("§" in t or "#" in t or "`" in t
            or ("[" in t and "]" in t))


def je_slaby_puvod(text):
    """Holé 'odhad' bez metody/vstupů (E3): k ruční revizi, ne důkaz."""
    if not je_dukaze(text):
        return False
    t = text.strip()
    if len(t) >= 10:
        return False
    low = t.casefold()
    if re.search(r"[0-9]", t):
        return False
    return not any(s in low for s in METODA_SLOVA)


def load_doc(path):
    """Načti normalized_ids.json; poškozený soubor = FAIL (ValueError)."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(
            "FAIL: neplatný JSON %s (%s: %s)"
            % (path, type(e).__name__, e))
    if not isinstance(doc, dict) or not isinstance(doc.get("ids"), list) \
            or not isinstance(doc.get("meta"), dict):
        raise ValueError(
            "FAIL: neplatný JSON %s — chybí klíče meta/ids" % path)
    return doc


def evaluate(doc, rows, f_blob_sha, f_rel, catalog_ids, catalog_tune=None):
    """Strojové jádro validace. Vrací (fails, pendings, stats).

    fails / pendings = seznamy řetězců; každý začíná FAIL: / PENDING:.
    stats = vypočtené agregace (E4), nic opsaného.
    catalog_ids: množina ID, nebo dict id→tune_key (tune se pak
    kontroluje v R3/R6/R8); catalog_tune: volitelný dict id→tune_key.
    """
    fails, pendings = [], []

    def fail(name, detail=""):
        fails.append("FAIL: %s%s" % (name, (" — " + detail) if detail else ""))

    def pending(name, detail=""):
        pendings.append("PENDING: %s%s"
                        % (name, (" — " + detail) if detail else ""))

    meta = doc.get("meta", {})
    declared = meta.get("deklarovano", {}) or {}
    derived_meta = meta.get("odvozeno_strojove", {}) or {}
    meta_blob = ((meta.get("zdroj_60_a_78", {}) or {}).get("blob_sha", ""))
    ids = doc.get("ids", [])
    unres = doc.get("unresolved", [])

    row_by_line = {ln: c for ln, c in rows}
    row_lines = set(row_by_line)
    expected = {ln: expand_cell_ids(c[0]) for ln, c in rows}
    row_stav = {ln: c[6].strip().strip("`") for ln, c in rows}
    row_nazev = {ln: c[1].strip() for ln, c in rows}
    row_states = Counter(row_stav.values())

    id_list = [e.get("logical_id") for e in ids
               if isinstance(e, dict)]
    idset = set(id_list)
    id_states = Counter(e.get("status") for e in ids
                        if isinstance(e, dict))
    # Katalog: množina ID + mapa id→tune_key (R3/R6/R8). Zpětně
    # kompatibilní: starší volání předávají jen množinu ID.
    if isinstance(catalog_ids, dict):
        tune_map = dict(catalog_ids)
        cat_ids = set(tune_map)
    else:
        cat_ids = set(catalog_ids)
        tune_map = dict(catalog_tune or {})
    rec_by_id = {e.get("logical_id"): e for e in ids
                 if isinstance(e, dict)
                 and isinstance(e.get("logical_id"), str)}

    # Tokeny sloupce Název, které nikdy nejsou Interní ID (R3 podklad).
    intern_all = set()
    for members in expected.values():
        intern_all.update(members)
    nazev_tokens = set()
    for ln, c in rows:
        for tok in re.split(r"[/+]", c[1]):
            t = tok.strip().strip("`").strip("()…").strip()
            if t:
                nazev_tokens.add(t)
    nazev_only = {t for t in nazev_tokens if t not in intern_all}

    groups = {ln: m for ln, m in expected.items() if len(m) > 1}
    expanded_members = sorted({m for ms in groups.values() for m in ms})

    # ---------- E4: tři oddělené počty, vše vypočteno ----------
    if len(rows) != 78:
        fail("SOURCE_TABLE_ROWS",
             "strojově načteno %d řádků, očekáváno 78" % len(rows))
    if declared.get("radku_tabulky") != 78:
        fail("metadata-nesoulad",
             "meta.deklarovano.radku_tabulky=%r, strojově 78"
             % declared.get("radku_tabulky"))
    if dict(row_states) != (derived_meta.get("stavy_radku") or {}):
        fail("metadata-nesoulad",
             "meta stavy řádků %r ≠ strojově %s"
             % (derived_meta.get("stavy_radku"), dict(row_states)))
    if (dict(id_states) != (derived_meta.get("stavy_id") or {})
            or derived_meta.get("unikatnich_id") != len(ids)):
        fail("metadata-nesoulad",
             "meta stavy ID %r/%r ≠ strojově %s/%d"
             % (derived_meta.get("stavy_id"),
                derived_meta.get("unikatnich_id"),
                dict(id_states), len(ids)))
    if meta_blob != f_blob_sha:
        fail("metadata-nesoulad",
             "meta blob_sha %s ≠ skutečný blob zdroje %s"
             % (meta_blob, f_blob_sha))

    # Původní logická množina 60: seznam nikdy nedoložen (Varianta B) →
    # validátor MUSÍ vrátit PENDING, nesmí přepsat 94 na 60. I kdyby
    # někdo vložil libovolných 60 ID z 94, seznam bez doložené
    # provenience se nepřijímá (FAIL + PENDING zůstává).
    orig = meta.get("original_60_set", {}) or {}
    seznam60 = orig.get("seznam")
    if isinstance(seznam60, list) and seznam60:
        fail("ORIGINAL_LOGICAL_IDS",
             "seznam 60 má %d položek — bez doložené historické "
             "provenience se nepřijímá ani výběr z 94 (NOT_RECONSTRUCTABLE)"
             % len(seznam60))
    pending("ORIGINAL_LOGICAL_IDS=PENDING",
            "ORIGINAL_60_SET=NOT_RECONSTRUCTABLE — seznam 60 ID "
            "neexistuje v žádném commitu/souboru (Varianta B); "
            "94 normalizovaných ID se za 60 nevydává")

    # Provozní rozsah 94 (ACCEPTED_MAPPED_SET): oddělený od historické
    # 60. Bez výslovného schválení uživatelem je UNAPPROVED.
    acc = meta.get("accepted_mapped_set", {}) or {}
    acc_status = acc.get("status", "UNAPPROVED")
    if acc_status != "APPROVED":
        pending("ACCEPTED_MAPPED_SET=UNAPPROVED",
                "94 ID je strukturální normalizace, ne schválený rozsah; "
                "schválení náleží uživateli")
    else:
        acc_seznam = acc.get("seznam")
        if not isinstance(acc_seznam, list) or set(acc_seznam) != idset:
            fail("ACCEPTED_MAPPED_SET",
                 "schválený seznam neodpovídá aktuálním ids "
                 "(změna dat po schválení vyžaduje nové schválení)")
        import hashlib as _hl
        acc_sha = _hl.sha256(",".join(sorted(
            x for x in idset if isinstance(x, str))).encode("utf-8")
                             ).hexdigest()
        if acc.get("sha_data") != acc_sha:
            fail("ACCEPTED_MAPPED_SET",
                 "sha_data schválené sady nesouhlasí s aktuálními daty")
        for pole in ("rozhodnuti", "datum"):
            if not acc.get(pole):
                fail("ACCEPTED_MAPPED_SET",
                     "schválení bez pole %r není platné" % pole)

    # ---------- E1: vztah záznam → zdrojový řádek ----------
    for idx, e in enumerate(ids):
        if not isinstance(e, dict):
            fail("záznam #%d není objekt" % idx)
            continue
        lid = e.get("logical_id")
        srows = e.get("source_rows")
        if not lid or not isinstance(lid, str):
            fail("záznam #%d bez logical_id" % idx)
            continue
        if (not isinstance(srows, list) or not srows
                or any(type(x) is not int for x in srows)):
            fail("špatné source_rows",
                 "logical_id=%s source_rows=%r (musí být neprázdný "
                 "seznam celých čísel; bool True/False se odmítá) "
                 % (lid, srows))
            continue
        if len(set(srows)) != len(srows):
            fail("duplicitní source_rows",
                 "logical_id=%s source_rows=%r obsahuje číslo víckrát"
                 % (lid, srows))
        for ln in srows:
            if ln not in row_lines:
                fail("cizí source_rows",
                     "logical_id=%s: zdrojový řádek %d není řádek "
                     "zdrojové tabulky" % (lid, ln))
            elif lid not in expected[ln]:
                fail("ID neodpovídá zdrojovému řádku",
                     "logical_id=%s: zdrojový řádek %d neobsahuje "
                     "toto ID (buňka: %s)" % (lid, ln, row_by_line[ln][0]))
        # R3: alias ≠ ID
        if lid in nazev_only:
            fail("alias-jako-ID",
                 "logical_id=%s je jen Název (Tune klíč), ne Interní ID" % lid)
        # Vztah k nedoložené 60: nelze tvrdit členství.
        rel = e.get("relationship", "UNRESOLVED")
        if rel != "UNRESOLVED":
            fail("vztah k original_60",
                 "logical_id=%s: relationship=%r, přípustné jen "
                 "UNRESOLVED (množina 60 není definována)" % (lid, rel))
        # Katalog: žádné vymyšlené ID (R4 výjimky řeší unresolved).
        if lid not in cat_ids:
            fail("neexistující ID",
                 "logical_id=%s: není v katalogu parameters.json ani "
                 "v unresolved — vymyšlené ID zakázáno" % lid)
        # R7: jeden status na ID + evidence s důkazem původu.
        st = e.get("status")
        if st not in ALLOWED:
            fail("konfliktní/neplatný status",
                 "logical_id=%s: status=%r mimo %s"
                 % (lid, st, sorted(ALLOWED)))
        ev = e.get("evidence")
        if not isinstance(ev, dict) or not all(
                k in ev for k in ("mustang_cil", "zdroj_cile", "puvod")):
            fail("chybějící evidence",
                 "logical_id=%s: evidence musí mít "
                 "mustang_cil/zdroj_cile/puvod" % lid)
            continue
        # E3: provenance statusu. VERIFIED = konkrétní hodnota +
        # dohledatelný zdroj s lokátorem + specifický původ.
        if st == "VERIFIED" and not (
                je_hodnota(ev.get("mustang_cil"))
                and ma_lokator(ev.get("zdroj_cile"))
                and je_dukaze(ev.get("puvod"))
                and len(str(ev.get("puvod")).strip()) >= 6):
            fail("VERIFIED-bez-evidence",
                 "logical_id=%s: VERIFIED vyžaduje konkrétní "
                 "mustang_cil (hodnota/enum) + zdroj_cile s lokátorem "
                 "(§/#L/`/[]) + specifický puvod" % lid)
        if st == "ESTIMATED" and not je_dukaze(ev.get("puvod")):
            fail("ESTIMATED-bez-původu",
                 "logical_id=%s: ESTIMATED vyžaduje doložený původ "
                 "(odhad/výpočet/odvození)" % lid)
        if st == "ESTIMATED" and not je_dukaze(ev.get("zdroj_cile")):
            fail("ESTIMATED-bez-zdroje",
                 "logical_id=%s: ESTIMATED vyžaduje doložený zdroj_cile "
                 "(vzorec/metoda/odvození)" % lid)
        if st == "ESTIMATED" and je_slaby_puvod(ev.get("puvod")):
            pending("ESTIMATED-k-revizi",
                    "logical_id=%s: holé 'odhad' bez metody/vstupů — "
                    "ověřit ručně, není to důkaz" % lid)
        if st in ("UNKNOWN", "PENDING") and je_dukaze(ev.get("mustang_cil")):
            pending("ruční-review",
                    "logical_id=%s: status %s, ale mustang_cil vypadá "
                    "konkrétně — ověřit ručně" % (lid, st))
        # Jeden status na ID: divergentní řádky pod jedním ID.
        stavy_radku = {row_stav[ln] for ln in srows if ln in row_lines}
        if len(stavy_radku) > 1:
            fail("konfliktní statusy",
                 "logical_id=%s: source_rows %s mají různé stavy "
                 "řádků %s — jeden záznam nemůže mít 1 status"
                 % (lid, srows, sorted(stavy_radku, key=str)))
        # R7: status záznamu musí odpovídat stavu zdrojového řádku
        # (dědění; prohození dvou statusů při stejných součtech selže).
        if len(stavy_radku) == 1 and st != next(iter(stavy_radku)):
            fail("status-neodpovídá-zdroji",
                 "logical_id=%s: status=%r, ale zdrojový řádek %s má "
                 "stav %r (R7)" % (lid, st, srows,
                                   next(iter(stavy_radku))))
        # source_reference: soubor + skutečný blob + řádek.
        ref = e.get("source_reference", "")
        if not isinstance(ref, str) or f_rel not in ref \
                or f_blob_sha not in ref \
                or not all("#L%d" % ln in ref for ln in srows):
            fail("neexistující reference",
                 "logical_id=%s: source_reference=%r neukazuje na "
                 "%s@blob:%s s řádky %s"
                 % (lid, ref, f_rel, f_blob_sha, srows))
        # Sloučené tvary (R2/R8): žádné '/', '*', mezery v ID.
        if not re.fullmatch(r"[a-z][a-z0-9_]*", lid or ""):
            fail("sloučené/pseudo ID",
                 "logical_id=%r není jednotlivé katalogové ID (R2/R8)" % lid)

    # ---------- E2: R1–R8 ----------
    # R5: duplicity = multi-přiřazení.
    counts = Counter(id_list)
    dupes = sorted(x for x, n in counts.items()
                   if n > 1 and isinstance(x, str))
    if dupes:
        fail("duplicity ID (multi-přiřazení)", "duplicitní: %s" % dupes)
    # E1-úplnost + R2: každý zdrojový řádek je pokryt právě svými
    # katalogovými členy — nic nechybí, nic není přidáno bez opory.
    claimed = {}
    for e in ids:
        if not isinstance(e, dict):
            continue
        lid = e.get("logical_id")
        srows = e.get("source_rows")
        if not isinstance(lid, str) or not isinstance(srows, list):
            continue
        for ln in srows:
            if type(ln) is int and ln in row_lines:
                claimed.setdefault(ln, set()).add(lid)
    for ln, members in sorted(expected.items()):
        want = {m for m in members if m in cat_ids}
        got = claimed.get(ln, set())
        if want - got:
            fail("E1-neúplná-vazba",
                 "řádek %d: zdrojová ID %s chybí v normalizaci"
                 % (ln, sorted(want - got)))
        if got - want:
            fail("E1-ID-bez-opory",
                 "řádek %d: ID %s nemají oporu v buňce Interní ID "
                 "(buňka: %s)" % (ln, sorted(got - want),
                                  row_by_line[ln][0]))
    # R2: skupinové buňky rozbaleny úplně; nedoložené členy → unresolved.
    for ln, members in sorted(groups.items()):
        for m in members:
            if m in cat_ids and m not in idset:
                fail("vynechaný člen skupiny",
                     "řádek %d: člen %s chybí v ids (R2)" % (ln, m))
            if m not in cat_ids and m in idset:
                fail("nedoložený člen jako ID",
                     "řádek %d: člen %s nemá katalogové ID — patří "
                     "do unresolved, ne do ids (R4)" % (ln, m))
    # R4: unresolved vede nedoložené (U1 clutch trio + U3 seznam 60).
    if not isinstance(unres, list) or not unres:
        fail("unresolved", "seznam unresolved chybí/prázdný")
    else:
        kody = {u.get("kod") for u in unres if isinstance(u, dict)}
        if "U1" not in kody or "U3" not in kody:
            fail("unresolved", "chybí kódy U1 (clutch trio) a U3 (seznam 60)")
        text = " ".join(str((u.get("popis") or "")) for u in unres
                        if isinstance(u, dict))
        for trio in ("clutch_rpm", "clutch_speed", "clutch_stall"):
            if trio in cat_ids:
                fail("R4", "%s je nově v katalogu — přemapovat" % trio)
            if trio not in text:
                fail("R4", "%s není veden v unresolved" % trio)
    # R6: názvy — u rozbalených členů primary_name = ID + Název v aliases;
    # u běžných záznamů primary_name = Název řádku (R6-c).
    for ln, members in sorted(groups.items()):
        naz = row_nazev[ln]
        for m in members:
            if m not in cat_ids:  # nedoložené členy nejsou ID
                continue
            rec = rec_by_id.get(m)
            if rec is None:
                continue  # už hlášeno jako vynechaný člen
            if rec.get("primary_name") != m:
                fail("R6 názvy",
                     "logical_id=%s: primary_name=%r, u rozbaleného "
                     "člena musí být = ID" % (m, rec.get("primary_name")))
            als = rec.get("aliases")
            if not isinstance(als, list) or not als:
                fail("R6 názvy",
                     "logical_id=%s: prázdné aliases (R3/R6)" % m)
            elif naz not in PRAZDNE and naz not in (als or []):
                fail("R6 názvy",
                     "logical_id=%s: Název řádku %d (%r) chybí v aliases"
                     % (m, ln, naz))
    for e in ids:
        if not isinstance(e, dict):
            continue
        lid = e.get("logical_id")
        srows = e.get("source_rows")
        if not isinstance(lid, str) or not isinstance(srows, list):
            continue
        vrows = [ln for ln in srows
                 if type(ln) is int and ln in row_lines]
        if not vrows or lid not in cat_ids:
            continue
        if any(len(expected.get(ln, [])) > 1 for ln in vrows):
            continue  # skupinový člen — řešeno výše
        naz = row_nazev[vrows[0]]
        if e.get("primary_name") != naz:
            fail("R6-název-nesouhlasí",
                 "logical_id=%s: primary_name=%r, u běžného záznamu "
                 "musí být = Název řádku %d (%r)"
                 % (lid, e.get("primary_name"), vrows[0], naz))
    # R3/R6-e: každý alias musí být Název vlastního řádku nebo vlastní
    # katalogový tune_key — nikdy cizí ID, cizí tune_key ani výmysl.
    # Duplicitní alias napříč záznamy jen u sourozenců sdíleného řádku.
    all_tunes = {t for t in tune_map.values() if isinstance(t, str)}
    tune_owner = {}
    for cid, t in tune_map.items():
        if isinstance(t, str):
            tune_owner.setdefault(t, cid)
    alias_holders = {}
    for e in ids:
        if not isinstance(e, dict):
            continue
        lid = e.get("logical_id")
        srows = e.get("source_rows")
        als = e.get("aliases")
        if not isinstance(lid, str) or not isinstance(als, list):
            continue
        own_nazvy = {row_nazev[ln] for ln in srows
                     if type(ln) is int and ln in row_nazev}
        own_tune = tune_map.get(lid)
        for a in als:
            if not isinstance(a, str):
                fail("R6-cizí-alias",
                     "logical_id=%s: alias %r není řetězec" % (lid, a))
                continue
            if a in cat_ids:
                fail("alias-je-ID",
                     "logical_id=%s: alias %r je katalogové ID, "
                     "alias nesmí být ID (R3)" % (lid, a))
            elif a in all_tunes and tune_owner.get(a) != lid:
                fail("R6-cizí-alias",
                     "logical_id=%s: alias %r je tune_key parametru %r "
                     "(R3/R6)" % (lid, a, tune_owner.get(a)))
            elif a not in own_nazvy and a != own_tune:
                fail("R6-cizí-alias",
                     "logical_id=%s: alias %r není Název vlastního "
                     "řádku ani vlastní tune_key (R3/R6)" % (lid, a))
            if a.strip() not in PRAZDNE:
                alias_holders.setdefault(a, []).append(lid)
    for a, holders in alias_holders.items():
        if len(holders) > 1:
            rows_of = []
            for h in holders:
                r = rec_by_id.get(h, {})
                sr = r.get("source_rows") if isinstance(r, dict) else None
                rows_of.append(set(x for x in (sr or [])
                                   if type(x) is int))
            if not rows_of or not set.intersection(*rows_of):
                fail("duplicitní-alias",
                     "alias %r sdílí nesouvisející záznamy: %s"
                     % (a, sorted(holders)))
    # R8: F/R a L/R páry odděleně — doložené dvojice (FR_PAIRS,
    # LR_PAIRS), žádný sloučený tvar, páry kompletní. Podobnost
    # názvů sama o sobě pár nedokládá — univerzální pravidlo
    # podle přípony se neuplatňuje.
    for a, b in FR_PAIRS:
        pa, pb = a in idset, b in idset
        if pa != pb:
            fail("F/R pár sloučen/chybí",
                 "dvojice %s/%s: přítomen jen jeden člen (R8)" % (a, b))
        stem = a[:-2]
        if stem in idset:
            fail("F/R pár sloučen/chybí",
                 "sloučený tvar %s zastupuje doloženou dvojici %s/%s "
                 "(R8)" % (stem, a, b))
        ta, tb = tune_map.get(a), tune_map.get(b)
        if pa and pb and isinstance(ta, str) and ta == tb:
            fail("F/R nerozlišený klíč",
                 "dvojice %s/%s sdílí tune_key %r (R8)" % (a, b, ta))
    for a, b in LR_PAIRS:
        pa, pb = a in idset, b in idset
        if pa != pb:
            fail("L/R pár sloučen/chybí",
                 "dvojice %s/%s: přítomen jen jeden člen (R8)" % (a, b))
        stem = a[:-2]
        if stem in idset:
            fail("L/R pár sloučen/chybí",
                 "sloučený tvar %s zastupuje doloženou dvojici %s/%s "
                 "(R8)" % (stem, a, b))
    # Pokrytí: každý řádek mapován ≥1 ID (R1).
    covered = Counter()
    for e in ids:
        sr = e.get("source_rows") if isinstance(e, dict) else None
        if isinstance(sr, list):
            for ln in sr:
                covered[ln] += 1
    uncovered = sorted(row_lines - set(covered))
    if uncovered:
        fail("nepůvodní/nepokryté řádky",
             "řádky bez ID: %s" % uncovered)

    stats = {
        "SOURCE_TABLE_ROWS": len(rows),
        "ORIGINAL_LOGICAL_IDS": "PENDING",
        "NORMALIZED_IDS": len(ids),
        "EXPANDED_GROUPS": len(groups),
        "EXPANDED_MEMBERS": len(expanded_members),
        "ALIASES": sum(len(e.get("aliases") or [])
                       for e in ids if isinstance(e, dict)),
        "UNRESOLVED": len(unres) if isinstance(unres, list) else 0,
        "stavy_radku": dict(row_states),
        "stavy_id": dict(id_states),
        "NEVYRESENE": len(unres) if isinstance(unres, list) else 0,
        "NEPOKRYTE_RADKY": len(uncovered),
        "DUPLICITY": len(dupes),
    }
    return fails, pendings, stats


def run(root=None):
    """Spusť validaci nad worktree. Vrací (exit_code, fails, pendings)."""
    root = root or repo_root()
    jpath = os.path.join(root, "reports", "NIGHT-WORK", "normalized_ids.json")
    try:
        doc = load_doc(jpath)
    except ValueError as e:
        print("[FAIL] %s" % e)
        print("VERDIKT_DAT=FAIL: neplatný JSON")
        return 1, [str(e)], []
    meta = doc.get("meta", {})
    f_rel = ((meta.get("zdroj_60_a_78", {}) or {}).get("soubor")
             or "reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md")
    fpath = os.path.join(root, *f_rel.split("/"))
    try:
        with open(fpath, "rb") as f:
            fbytes = f.read()
    except OSError as e:
        msg = "FAIL: zdrojová tabulka %s nečitelná (%s)" % (f_rel, e)
        print("[FAIL] %s" % msg)
        print("VERDIKT_DAT=FAIL: zdroj nečitelný")
        return 1, [msg], []
    f_blob = git_blob_sha(fbytes)
    rows = parse_f_rows(fpath)
    try:
        kpath = os.path.join(root, "src", "Chassis", "catalog",
                             "parameters.json")
        with open(kpath, encoding="utf-8") as f:
            kdoc = json.load(f)
        catalog_map = {e["id"]: e.get("tune_key") for e in kdoc}
    except (OSError, ValueError, KeyError, TypeError) as e:
        msg = "FAIL: katalog parameters.json nečitelný (%s)" % e
        print("[FAIL] %s" % msg)
        print("VERDIKT_DAT=FAIL: katalog nečitelný")
        return 1, [msg], []

    fails, pendings, stats = evaluate(doc, rows, f_blob, f_rel,
                                      catalog_map)

    print("KONTROLY E1–E4 (zdroj: %s, blob %s):" % (f_rel, f_blob[:12]))
    for kind, items in (("FAIL", fails), ("PENDING", pendings)):
        for item in items:
            print("  [%s] %s" % (kind, item))
    if not fails and not pendings:
        print("  [OK] vše doloženo")
    print()
    print("AGREGACE (E4, vše vypočteno):")
    print("  SOURCE_TABLE_ROWS=%d ORIGINAL_LOGICAL_IDS=%s "
          "NORMALIZED_IDS=%d" % (stats["SOURCE_TABLE_ROWS"],
                                 stats["ORIGINAL_LOGICAL_IDS"],
                                 stats["NORMALIZED_IDS"]))
    print("  EXPANDED_SKUPINY=%d EXPANDED_CLENI=%d ALIASY=%d UNRESOLVED=%d"
          % (stats["EXPANDED_GROUPS"], stats["EXPANDED_MEMBERS"],
             stats["ALIASES"], stats["UNRESOLVED"]))
    print("  RADKY: %d %s" % (stats["SOURCE_TABLE_ROWS"], stats["stavy_radku"]))
    print("  ID: %d %s" % (stats["NORMALIZED_IDS"], stats["stavy_id"]))
    print("  NEPOKRYTE_RADKY=%d DUPLICITY=%d"
          % (stats["NEPOKRYTE_RADKY"], stats["DUPLICITY"]))
    if fails:
        print("VERDIKT_DAT=" + "; ".join(fails))
        return 1, fails, pendings
    if pendings:
        print("VERDIKT_DAT=" + "; ".join(pendings))
        return 2, fails, pendings
    print("VERDIKT_DAT=PASS")
    return 0, fails, pendings


def main():
    code, _, _ = run()
    return code


if __name__ == "__main__":
    sys.exit(main())

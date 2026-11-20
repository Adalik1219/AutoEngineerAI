#!/usr/bin/env python3
"""Validace normalizace Agent E (60 ID / 78 radku). Jen stdlib.

Cte reports/NIGHT-WORK/normalized_ids.json + zdrojovou mapovaci tabulku
Agent F a overuje: pocty ID/radku, mapovani radek->ID, bez duplicit,
1 stav/ID, soucty, nevyresene/nemapovane. Agregat "60" overuje proti
odvozenym datum (DOLOZENO/NEDOLOZENO).

Exit: 0 = PASS (vse dolozeno), 2 = PENDING (mechanika sedi, 60 nedolozeno),
1 = FAIL (mechanicka nekonzistence).
"""
import json
import os
import re
import sys
from collections import Counter

ALLOWED = {"VERIFIED", "ESTIMATED", "PENDING", "UNKNOWN"}

def repo_root():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, ".."))

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
    lines = open(path, encoding="utf-8").read().splitlines()
    in_s2, rows = False, []
    for i, l in enumerate(lines, 1):
        if l.startswith("## 2."):
            in_s2 = True
        if re.match(r"## 3\.", l) and in_s2:
            break
        if in_s2 and l.startswith("| `"):
            c = split_row(l)
            if len(c) == 10:  # znama formalni vada L55: chybi separator
                c = c[:8] + ["<chybi sloupec>"] + c[8:]
            rows.append((i, c))
    return rows

def main():
    root = repo_root()
    jpath = os.path.join(root, "reports", "NIGHT-WORK", "normalized_ids.json")
    doc = json.load(open(jpath, encoding="utf-8"))
    meta = doc["meta"]
    fpath = os.path.join(root, meta["zdroj_60_a_78"]["soubor"])
    rows = parse_f_rows(fpath)
    row_lines = {ln for ln, _ in rows}
    row_states = Counter(c[6] for _, c in rows)

    fails, pendings = [], []
    def check(name, ok, detail="", pending=False):
        print(f"[{'OK' if ok else ('PENDING' if pending else 'FAIL')}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            (pendings if pending else fails).append(name)

    ids = doc["ids"]
    id_list = [e["logical_id"] for e in ids]

    # 1. pocty radku
    check("pocet radku F == deklarovano (78)", len(rows) == meta["deklarovano"]["radku_tabulky"],
          f"nacteno {len(rows)}")
    check("pocet radku F == odvozeno", len(rows) == meta["odvozeno_strojove"]["radku_tabulky"],
          f"{len(rows)}")
    # 2. mapovani radek->ID: kazdy radek pokryt >=1 ID
    covered = Counter()
    bad_refs = []
    for e in ids:
        for ln in e["source_rows"]:
            covered[ln] += 1
            if ln not in row_lines:
                bad_refs.append((e["logical_id"], ln))
    uncovered = sorted(row_lines - set(covered))
    check("kazdy radek mapovan >=1 ID", not uncovered, f"nepokryto: {uncovered or 'zadne'}")
    check("source_rows ukazuji na skutecne radky", not bad_refs, f"vadne: {bad_refs or 'zadne'}")
    # 3. bez duplicit
    dupes = sorted({x for x in id_list if id_list.count(x) > 1})
    check("bez duplicit ID", not dupes, f"unikatnich {len(set(id_list))}/{len(id_list)}" + (f", duplicity: {dupes}" if dupes else ""))
    # 4. jeden stav na ID
    bad_status = [e["logical_id"] for e in ids
                  if not isinstance(e.get("status"), str) or e["status"] not in ALLOWED]
    check("prave 1 stav/ID z mnoziny", not bad_status,
          f"mnozina {sorted(ALLOWED)}" + (f", vadne: {bad_status}" if bad_status else ""))
    # 5. soucty
    id_states = Counter(e["status"] for e in ids)
    check("soucet stavu radku == pocet radku",
          sum(row_states.values()) == len(rows), str(dict(row_states)))
    check("soucet stavu ID == pocet ID",
          sum(id_states.values()) == len(ids), str(dict(id_states)))
    check("odvozene stavy radku sedi s JSON meta",
          dict(row_states) == meta["odvozeno_strojove"]["stavy_radku"], str(dict(row_states)))
    check("odvozene stavy ID sedi s JSON meta",
          dict(id_states) == meta["odvozeno_strojove"]["stavy_id"], str(dict(id_states)))
    # 6. deklarace 60
    check("deklarovanych 60 ID dolozeno seznamem",
          len(ids) == meta["deklarovano"]["logickych_id"],
          f"deklarovano {meta['deklarovano']['logickych_id']}, odvozeno {len(ids)}",
          pending=True)
    # 7. nevyresene/nemapovane evidovany
    unres = doc.get("unresolved", [])
    check("unresolved evidovany", isinstance(unres, list) and len(unres) > 0, f"{len(unres)} polozky")
    art = [u for u in unres if u.get("kod") == "U1"][0] if unres else None
    print(f"INFO clutch rpm/speed/stall bez ID (R4): {'ano' if art else 'ne'}")

    print()
    print(f"AGREGACE radky: {len(rows)} " + " ".join(f"{k}={row_states.get(k,0)}" for k in ("VERIFIED", "ESTIMATED", "PENDING", "UNKNOWN")))
    print(f"AGREGACE id: {len(ids)} " + " ".join(f"{k}={id_states.get(k,0)}" for k in ("VERIFIED", "ESTIMATED", "PENDING", "UNKNOWN")))
    print(f"NEVYRESENE: {len(unres)} / NEPOKRYTE RADKY: {len(uncovered)} / VADNE ODKAZY: {len(bad_refs)} / DUPLICITY: {len(dupes)}")
    if fails:
        print("VERDIKT_DAT=FAIL:", "; ".join(fails))
        return 1
    if pendings:
        print("VERDIKT_DAT=PENDING:", "; ".join(pendings))
        return 2
    print("VERDIKT_DAT=PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())

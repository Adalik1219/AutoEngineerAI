# QA FÁZE 4 – Parameter Intelligence (Agent C)

**Vlastník:** Agent C – QA. **Vlastněné soubory:** `tests/test_f4_mapping.py`, tento report.
**Pravidla:** česky; `docs/AGENT-RULES.md`; stdlib; žádné git operace; READ-ONLY mimo vlastněné.
**Běh:** `python3 -m unittest tests.test_f4_mapping` → **OK (27 běhů, 1 legitimní PENDING)**;
`python3 tests/run_all.py` → **PASS (129 běhů, 125 PASS, 0 FAIL, 4 PENDING)**.
**Zdroje pravdy (čteno):** `docs/A-CHASSIS-AUDIT.md`, `src/Chassis/adapters/achassis_v1.py`.
Tvrzení Agentů A/B nepřevzata – vše níže je vlastní čtení kódu + vlastní testy.

Značení: **[F]** ověřený fakt (vlastní běh/čtení), **[P]** předpoklad, **[N]** neznámé.
Mapování F4-01–F4-12 na body ze zadání je moje rekonstrukce (zadání v repo není):
úplnost, původ+klasifikace, UNKNOWN, ověřené Tune klíče, mapovatelnost, jednotky,
odmítnutí, prostor z ověřených, backend-podpora, test-sady, rbxm, QA-artefakty.

---

## 1. Verdikty F4-01–F4-12

| ID | Bod | Verdikt | Důkaz |
|---|---|---|---|
| F4-01 | Katalog úplný (125/125, 19 polí, unikátní id/cesty) | **PASS** | `test_f4_01_*`: 125 záznamů, 19 polí, kategorie 79/14/2/3/27 **[F]** |
| F4-02 | Původ + klasifikace (provenance, auditní zdroj) | **PASS** | parita ≥100 klíčů katalog↔adaptér (mutable⇔MUTABLE_TUNE/measured); 125/125 zdrojů `A-CHASSIS-AUDIT.md §` **[F]** |
| F4-03 | UNKNOWN zůstává UNKNOWN (27), nic vymyšleného | **PASS** | všech 27 `value/default/min/max None`, `PENDING`; 23 firm-klíčů kryto adaptérem (unknown/immutable), 22/23 doslovně v auditu (viz N1) **[F]** |
| F4-04 | Ověřené Tune klíče (spot-check 12), read-only chráněna, závislosti | **PASS** | 12/12 shoda katalog+adaptér s auditem (§5/§6/§12); READ_ONLY `none`, SCRIPT `script`; závislost turba + všechny `depends_on` tokeny se překládají **[F]** |
| F4-05 | Mapovatelnost (3 vlastnosti vč. motoru) | **PASS** | `Horsepower+FinalDrive+Bias` → Tune; `peak_power_kw≠horsepower`; `peak_torque_nm` správně odmítnut (nemá Tune protějšek) **[F]** |
| F4-06 | Jednotky (hp/rpm/0–1; žádné tiché převody) | **PASS** | unit z katalogu v `tune_change`; `BrakeForce` se nerovná Nm, `Weight` lb→kg řeší runtime (MAPPING.md §6) – engine nic tiše nepřevádí **[F]** |
| F4-07 | Odmítnutí (unknown/read-only/mimo-rozsah/konflikt/závislost) + vstup neporušen | **PASS** | 6 druhů odmítnutí, determinismus (FD×FDMult vítězí abecedně první), deepcopy-test vstupu **[F]** |
| F4-08 | Prostor jen z ověřených (5 filtrů) | **PASS s výhradou** | reálný katalog + caps adaptéru → přesně 7 klíčů (`Bias, CurveMult, FDiffCoast, FDiffPower, Preload, TorqueVector, WeightDist`), vše PASS+s rozsahem+`used_in`; `FinalDrive/Horsepower` bez rozsahu → mimo prostor (ke zvážení D) **[F]** |
| F4-09 | Backend-podpora (prostor jen z backendem podporovaných) | **FAIL → vlastník D** | `backend.py` nevystavuje žádné Tune caps; `search_space.py` ladí `peak_torque_nm` bez Tune protějšku (končí v `rejected`) – wiring chybí (D běží) **[F]** |
| F4-10 | Testovací sady zelené (selftesty + repo suite) | **PASS** | `loader --selftest` OK (125), `mapping_engine` SELFTEST OK, `run_all` 129 běhů / 0 FAIL **[F]** |
| F4-11 | rbxm integrita + žádná aplikace neověřených + záznam odmítnutí + provenance | **PASS** | sha256 `dc8747…fefdf` shoduje, 230 421 B, mtime beze změny; adaptér odmítá `S_Sensitivity`/`WarpDrive`; `touched_model_files` prázdné; PENDING 31 **[F]** |
| F4-12 | QA artefakty (testy + tento report + seznam vad) | **PASS** | tento soubor + `tests/test_f4_mapping.py`, exit 0 **[F]** |

**[P]** F4-10 „H suite" čtu jako testovací sady (selftesty + `run_all`); jiný význam H
v zadání/repu není.
**[N]** Studio-měření (31 PENDING: `Stiffness/Damping` float-lane §1, `StAxisOffset`
runtime §17.1, V-max až po opravě `magnitude` §17.2) – bez Studia PENDING, nikdy PASS.

---

## 2. Seznam vad a nálezů (soubor:řádka)

1. **V1 – FAIL (vlastník D): backend bez Tune caps; `peak_torque_nm` bez protějšku.**
   `src/Optimizer/backend.py` (celý – symbol `backend_caps` ani `Horsepower` neexistuje);
   `src/Optimizer/search_space.py:17-20` (`engine.peak_torque_nm` 180–250 Nm).
   Te
...[truncated 2085 chars]
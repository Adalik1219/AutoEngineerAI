# F5-QA: Agent E — nezávislé QA + kampaň 3+3 (f55, T03-only)

**Verdikt: BLOCKED — kampaň neprovedena (stale Play session, F5 kód není živě).
Žádná f55 data nevznikla (adresář `vehicle-data/telemetry/f55/` ZÁMĚRNĚ
nevytvořen — test bere absenci jako SKIP/PENDING; falešné běhy nezapisuji).
H suite: 159 běhů = 155 PASS / 0 FAIL / 4 PENDING → VYSLEDEK PASS (s PENDING).
F5-CLOSURE: NEDOPORUČUJI (2 kódové vady na disku + chybějící čerstvá session).**

Session: `17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play, tatáž instance jako F44).
`start_stop_play` nikdy nevoláno (zákaz); šablona nedotčena (pouze čtení);
žádný teleport, žádné sezení, žádná jízda — pouze read-only sondy.
Disk: main `847a7f6` (F5 vlna 1), `git status` čistý.

## 1. Nezávislé ověření oprav A–D (disk + živé sondy, bez jízdy)

Živé sondy (Server, read-only `execute_luau`):
- `VerifyT03Start:false | ReadStartRollDeg:false | SpawnT03Verified:false | BRAKE_DIAG_TOL:nil`
- `MOVE_NAMES:[A-Chassis Interface,Initialize,Plugins]` (stará move-verze)
- `bridge_OR_IBrake:true | bridge_assign_IBrake:false` (starý OR-můstek, 846 B)
- `ScenarioDefinitions:MISSING` při hledání pod `AutoEngineer` (plný název se liší — neblokuje, jen pozn.)
- Bridge ve Workspace: NENALEZEN (žádný `AEBridge`/`AE_Bridge`/`Bridge` — harness idle, bez reziduí).

Závěr freshness: **živě běží pre-F5 kód (F4.4/F3).** Diskové F5 opravy nejsou
nasazeny. Restart Play je mimo můj mandát (nikdy `start_stop_play`).

| Oprava | Disk | Live | Závěr |
|---|---|---|---|
| A arbitrace (`_IBrake=_AE` assign, nil=manual, nil-clear v harnessu, `CheckBrakeDiag` read-only) | PASS (ověřeno čtením `VehicleManager`+`ScenarioRunner`+harness l.232) | ABSENT (OR-můstek) | PENDING (čeká fresh Play) |
| B no-Source `RepairStructure` (žádný přesun, žádný Source, verify-only, `return true,0`) | PASS (ověřeno čtením) | ABSENT (move-verze) | PENDING |
| C SUMMARY z kept + `roll_deg` + dynamické f* | ČÁSTEČNĚ — **FAIL, viz §2**: `roll_deg` PASS (`SampleOnce`+schema required), run-doc recompute z kept PASS, **agregát SUMMARY je stále z FULL-vzorků** | ABSENT | FAIL (disk, blokuje kampaň) |
| D start 100±1 + ABS read-only | ČÁSTEČNĚ — `VerifyT03Start`/`SpawnT03Verified`/`ReadABSConfig` PASS, **ale harness po `Spawn` znovu volá `applyStartSpeed` bez re-verifikace** (l.205–208, brána obcházena, minor) | ABSENT | PENDING + minor nález |
| Init/slot auto-fill (`CloneVehicle→WriteTune MUTABLE→DeployVehicle`, beze změny) | PASS (nezměněno, čteno l.57–89) | netestováno (slot 0) | PENDING |

## 2. FAIL nález (disk, před kampaní — neopravuji cizí kód)

**C-1 (kritický): `writeT03Summary` agreguje FULL-metriky.**
`runOneScenario` vrací `output` s `ComputeT03Metrics(collector.samples)` (plné
vzorky, l.242), outbox-doc přepočítává z kept (l.160). `runBrief` agreguje
`distances` z návratu `runOneScenario` (l.404–405) → SUMMARY je full-based,
run-docs kept-based. Komentář F5-C ("agregace vždy z kept", handoff přes
návrat `runOneScenario`) **není implementován**. Důsledek: kampaň na tomto
kódu systematicky selže `test_summary_aggregate` pro f55 (striktní, exact na
3 des. místa), stejně jako F44 selhávala (0.6–1.1 % divergence). Oprava (H1):
agregovat z kept/outbox `t03` (nebo vracet outbox-doc). Bez toho kampaň
plýtvá 6 běhy.

**D-1 (minor): redundantní `applyStartSpeed` po verifikovaném Spawnu**
(l.205–208). `SpawnT03Verified` nastaví+ověří rychlost; harness ji hned poté
přepíše bez ověření. Měření pak startuje z neověřené rychlosti. Oprava (D):
po `applyStartSpeed` znovu `VerifyT03Start`, nebo redundantní volání smazat
(rychlost už nastavil Spawn).

## 3. Kampaň 3+3 f55 — BLOCKED (0/6, 0 voidů, 0 náhrad)

Předpoklad "čerstvá Play Solo session s F5 kódem" není splněn (§1) a restart
nesmím provést. Jízda na starém kódu by vyrobila neplatná f55 data (bez
`roll_deg`, full-SUMMARY) — proto vědomě neprovedena. Konfigy `cfg_f55_b06 /
cfg_f55_b09` na disku neexistují (pouze zmínky `cfg_f44_*` v reportech) —
Tune-delta pro f55 musí definovat koordinátor. Void-budget nedotčen (max 2).

## 4. Statistika — N/A (žádná data, žádné umělé PASS)

Kritéria (Δ means > 3σ_pooled, 6 nenulových drah, repeatabilita 5 %)
nevyhodnocena — pipeline k nim nedojde. Verdikt kampaně je BLOCKED (měření),
nikoli FAIL fyziky.

## 5. Suite + regrese

- `tests/run_all.py`: **159 běhů, PASS 155, FAIL 0, ERROR 0, PENDING 4 →
  VYSLEDEK: PASS (s 4 PENDING)** (4 legitimní: F4-mapping Studio-pending,
  schema-conformance Fáze 5, 2× VariantStore baseline).
- `tests/test_f44_regression.py` nad f55: **PENDING** (kohorta f55
  neexistuje; striktní kontroly `roll_deg`-present a SUMMARY-exact jsou
  netestované, ne PASS). f44 kohorta nadále zelená (legacy tolerance);
  `test_summary_aggregate` pro f55 po opravě C-1 musí projít exaktne.

## 6. Cleanup — PASS (ověřeno živě + disk)

Live: `slot_refs:0 | jeep_nodes:0 | playergui_Interface:0`, bridge absent
(idle, bez reziduí). Disk: `git status` čistý; f55 adresář záměrně
nevytvořen. Postava/klient nedotčeni.

## 7. Mapování F5 body 1–10

1. arbitrace → PENDING (disk PASS, live absent)
2. init/slot auto-fill → PENDING (disk PASS-nezměněn, live netestován)
3. SUMMARY zdroj → **FAIL** (C-1, oprava před kampaní)
4. rychlost 100±1 → PENDING + minor D-1
5. ABS stav → PENDING (disk read-only PASS, live netestován)
6. roll kanál → PENDING (disk PASS, live netestován; f44 absence pinována OK)
7. cleanup → PASS
8. suite → PASS (155/0/4; f55-striktní část PENDING)
9. kampaň 3+3 → BLOCKED/PENDING (0/6, příčina: stale session)
10. repeatabilita 5 % → PENDING (žádná data)

## 8. Doporučení (F5-CLOSURE se nedoporučuje)

1. Opravit C-1 (agregace SUMMARY z kept/outbox `t03`) + D-1 (re-verifikace po
   `applyStartSpeed`) — vlastník H1/D, mimo můj mandát.
2. Definovat `cfg_f55_b06/b09` Tune-delta (koordinátor).
3. Restart Play Solo (koordinátor přes MCP) → čerstvá session s F5 kódem.
4. Poté znovu Agent E: kampaň 3+3 f55 + statistika + `test_summary_aggregate`
   (očekává PASS) → teprve pak F5-CLOSURE.

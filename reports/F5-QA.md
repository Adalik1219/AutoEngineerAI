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

---
# Beh E-retry — 2026-11-17 (plna kampan, CERSTVA Play Solo session s FX kodem)

**Verdikt: BLOCKED — kampaň neprovedena (live session stale pre-F5/FX kód).**
**Žádná f55 data nevznikla (adresář `vehicle-data/telemetry/f55/` ZÁMĚRNĚ
nevytvořen). H suite: 159 běhů = 155 PASS / 0 FAIL / 4 PENDING → PASS (s PENDING).
Regrese `test_f44_regression`: 11 testů OK (f44 legacy zelená; f55-striktní část
PENDING — kohorta neexistuje, `summary_aggregate`/`roll_deg-present` netestovány).
F5-CLOSURE: NEDOPORUČUJI.**

Session: `17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play, tatáž instance jako F44/F5).
`start_stop_play` nikdy nevoláno (zákaz); šablona nedotčena (pouze čtení);
žádný teleport, žádné sezení, žádná jízda — pouze read-only sondy `execute_luau`.
Disk: main `726dae8` (F5 FX), `git status` čistý.

## R0. Freshness gate (live) — FAIL → STOP

Živé sondy (Server, read-only):

- `VerifyT03Start:false | ReadStartRollDeg:false | SpawnT03Verified:false |
  ReadDriveSeatXzSpeed:false | CheckBrakeDiag:false` — F5/D API živě ABSENT
  (`WriteDriveAttributes:true` — existuje i ve starém kódu, ne F5-marker).
- `bridge_OR_IBrake:true | bridge_assign_IBrake:false` — starý OR-můstek živě.
- `TH kept_marker:false | reverify_marker:false` — FX C-1/D-1 živě ABSENT.
- `ScenarioDefinitions` žije v `ReplicatedStorage.AutoEngineer.Shared`
  (ne pod `ServerScriptService.AutoEngineer`); `ListIds` → `T01..T07`
  (T03 dostupná, `SAMPLE_RATE_HZ=60`). Scenario-kontrakt splněn.
- Bridge ve Workspace/ReplicatedStorage: NENALEZEN (idle, bez reziduí).

Závěr freshness: **živě běží pre-F5 kód (F4.4/F3); FX `726dae8` není nasazen.
Podmínka „čerstvá Play Solo session s FX kódem" není splněna → STOP+BLOCKED.
Restart Play je mimo můj mandát (nikdy `start_stop_play`).**

## R1. Ověření FX na disku (C-1/D-1 pryč) — PASS

Pracovní strom = `726dae8`, čistý. `TestHarness.server.lua`:
`outboxDoc` 8×, `entry_speed_mimo_toleranci_po_apply` 1×,
`runBrief` agreguje `distances` z `outboxDoc.measurements.summary.t03`
(l.422+), `runOneScenario` vrací `(output, outboxDoc)`.
Předchozí nálezy C-1 (FULL-agregace) a D-1 (neověřený `applyStartSpeed`)
jsou na disku odstraněny. Live ověření čeká na fresh session (PENDING).

## R2. Kampaň 3+3 f55 — BLOCKED (0/6, 0 voidů, 0 náhrad)

Jízda na starém kódu by vyrobila neplatná f55 data (bez `roll_deg`,
full-SUMMARY) — vědomě neprovedena. Konfigy `cfg_f55_b06/b09` na disku
neexistují (F44 analogie: Tune brake-bias 0.6 vs 0.9, viz F44-T03-RUNS;
Tune-delta pro f55 musí definovat koordinátor). Void-budget nedotčen (max 2).
`TEST-SCENARIOS.md` v repu neexistuje — jelo by se výhradně T03 (`scenario_ids`
živě ověřeny: T01–T07, kampaň by byla T03-only).

## R3. Statistika — N/A (žádná data, žádné umělé PASS)

Kritéria (Δ means > 3σ_pooled, 6 nenulových drah, repeatabilita 5 %)
nevyhodnocena. Verdikt kampaně je BLOCKED (měření), nikoli FAIL fyziky.

## R4. Suite + regrese

- `tests/run_all.py`: **159 běhů, PASS 155, FAIL 0, ERROR 0, PENDING 4 →
  VYSLEDEK: PASS (s 4 PENDING)** (stejné 4 legitimní PENDING jako minule).
- `tests/test_f44_regression`: **11 testů OK** (f44 legacy zelená vč.
  `test_summary_aggregate` v legacy toleranci a pin `roll_deg`-absence).
  f55-striktní část **PENDING** (kohorta f55 neexistuje; exact-kept shoda
  a `roll_deg`-present netestovány, ne PASS).

## R5. Cleanup — PASS

Live: `slot=0 | jeep=0 | gui=0 | bridge=0` (idle, bez reziduí).
Disk: `git status` čistý; f55 adresář záměrně nevytvořen.
Postava/klient nedotčeni.

## R6. Mapování F5 body 1–10 (retry)

1. arbitrace → PENDING (disk PASS, live absent)
2. init/slot auto-fill → PENDING (disk PASS-nezměněn, live netestován)
3. SUMMARY zdroj → PENDING (disk FX PASS, live absent — C-1 pryč z disku)
4. rychlost 100±1 → PENDING (disk FX PASS, live absent — D-1 pryč z disku)
5. ABS stav → PENDING (disk read-only PASS, live netestován)
6. roll kanál → PENDING (disk PASS, live netestován; f44 absence pinována OK)
7. cleanup → PASS
8. suite → PASS (155/0/4; f55-striktní část PENDING)
9. kampaň 3+3 → BLOCKED/PENDING (0/6, příčina: stale session)
10. repeatabilita 5 % → PENDING (žádná data)

## R7. Doporučení (F5-CLOSURE se nedoporučuje)

1. C-1/D-1 na disku OPRAVENY (`726dae8`) — ověřeno čtením, není co dalšího opravovat.
2. Definovat `cfg_f55_b06/b09` Tune-delta (koordinátor).
3. Restart Play Solo (koordinátor přes MCP) → čerstvá session s FX kódem.
4. Poté znovu Agent E: kampaň 3+3 f55 + statistika + `test_summary_aggregate`
   (očekává PASS) → teprve pak F5-CLOSURE.

---
# Beh E-final — 2026-11-18 (kampan 3+3 f55 v OVERENE session)

**Verdikt: BLOCKED — aparatura (0/6 platnych). 9 void behu ve 3 seriich
(b06; b09 0 briefu — neprovedeno). Void-budget max 2 prekrocen.
`vehicle-data/telemetry/f55/` ZAMERNE nevytvoren (zadny platny beh;
completed-with-garbage dle M2/M3 precedentu nezapisuji).
H suite: 159 behu = 155 PASS / 0 FAIL / 4 PENDING → PASS (s PENDING).
Regrese `test_f44_regression`: 11 testu OK (f44 legacy zelena; f55-striktni
cast PENDING — kohorta neexistuje). F5-CLOSURE: NEDOPORUCUJI.**

Session: `17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play Solo, F5 FX `726dae8`).
`start_stop_play` nikdy nevolano (zakaz); sablona nedotcena (pouze klony
pres `CloneVehicle`; zadny zapis do sablony/disku krome tohoto reportu);
postava primo nemanipulovana (presun pouze harness-`Spawn` auta na start
T03 + eject side-effect `DestroyVehicle`); zadny FAIL potlacen.
Konfigy: `cfg_f55_b06` (`brakes.BrakeBias=0.6`), `cfg_f55_b09` (0.9,
nedoruceno — viz blokery); `scenario_ids=["T03"]`, inbox pres
`AESubmitConfig:InvokeServer` (Client), outbox verbatim cten.

## F0. Freshness gate (live) — PASS

Zive sondy (Server, read-only `execute_luau`):
- `ScenarioRunner`: `VerifyT03Start:true | SpawnT03Verified:true |
  ReadStartRollDeg:true | ReadABSConfig:true | CheckBrakeDiag:true |
  ComputeT03Metrics:true` ✓
- `TestHarness`: `WriteDriveAttributes(via ScenarioRunner):true |
  ReadDriveSeatXzSpeed:true | outboxDoc:true |
  entry_speed_mimo_toleranci_po_apply:true` (FX D-1 re-verifikace zive) ✓
- `VehicleManager`: `RepairStructure:true | _IBrake_assign_:true` (F5-A) ✓
- Bridge inbox/outbox 0/0; `StartLine` x=2 ✓; remotes
  `AERunBrief/AETelemetry/AEStatus/AESubmitConfig` ✓;
  `TestClient` LocalScript u klienta ✓; hrac + postava existuji.
- Disk: `726dae8`, `git status` cisty krome tohoto reportu.

**Zaver: zive bezi F5 FX kod. Podminka cerstve session SPLNENA → kampan
spustena (3 briefy b06).**

## F1. Prubeh kampane (3 briefy b06, 9 behu, 0 platnych)

Spolecne: `CloneVehicle→WriteTune(BrakeBias)→DeployVehicle→rename
AE_VehicleSlot→SetNetworkOwner(nil)` pres MCP (capability OK; F44-M4
precedent — server-thread harnessu na `drive.Source` pada, viz F1.0).

F1.0 Setup-serie (budget-exempt, environmental, 0 voidu pocitano):
prvni submit prijal harness (`accepted:true`), ale `runBrief` zemrel bez
outboxu: `ApplyDriveInputBridge` (V.M. l.531) cte `drive.Source` →
`The current thread cannot read 'Source' (lacking capability
PluginOrOpenCloud)` (konzole, `TestHarness:66←192←422←457`).
`RepairStructure` verify-Only prosla. Obchvat: slot postaven rucne pres
MCP (ma capability) — `SLOT_OK tune=0.6`, 167 dilu, DriveSeat ✓.

Serie V1 (b06 brief#1; postava STALA v spawn-volumu (3.2,3.9,1.2)):
3/3 overlap instant-stop — v0≈0 (gate ~100 pass, smrt az po gatu):
r1 v0=0.0046 d=0.00098 dur=1.2; r2 v0=0.0196 d=0.917 dur=20.0 timeout;
r3 v0=0.0298 d=0.645 dur=8.45. Vse `completed`, `errors=[]`.
SUMMARY: mean=0.5212 delta=175.86 `repeatability_ok=false`.
Zaver: VOID 3× (proceduralni: zadna vstupni rychlost v mereni).
POZITIVUM: SUMMARY mean sedne exaktne z kept-run-docs
((0.00098+0.91746+0.64502)/3=0.52115) → **C-1 fix ZIVE OVEREN**.

Serie V2 (b06 brief#2; postava sedela od zacatku, ownership 167/167
server): 3/3 `roll_gt_45 + nezastaveno_do_timeout` (failed):
r1 v0=87.61 d=8.90; r2 v0=97.18 d=17.357; r3 v0=96.21 d=18.612
(rollmax r1 = 45.6° — marginalni). SUMMARY mean=14.956 delta=64.92.
Zaver: VOID 3× (prevraceni z rozhoupane sestavy se zamotanou postavou).

Serie V3 (b06 brief#3; F44-recept: eject→postava stoji na x=29.7 mimo
drahu, FRESH slot, cisty Sit z dalky):
r1 v0=86.64 d=10.98 dur=8.6 `completed` BEZ errors — spin po doskoku
(yaw_rate_max 7.5, peak_decel 327.8, lat 3.2; bral 86→11, ne ciste brzdeni);
r2 `startovni_podminky:roll_pred_startem_nenulovy:-8.7_deg` (pre-start
refusal — FX self-protekce FUNGUJE, v0=100 d=0.001);
r3 v0=100(first-sample) d=0.001 `completed` BEZ errors — instant-stop
100→0 za 31 ms (decel x=-2999.9, pozice beze zmeny: prekazka ve spawnu).
SUMMARY mean=3.661 delta=299.88. Zaver: VOID 3×.
(Outbox po kazde serii transientne cisten; void JSON ZAMERNE
neulozeny do `f55/` — completed-with-garbage dle M2/M3 precedentu.)

b09: 0 briefu. Slot 0.9 nikdy nepostaven — po 3 neuspesnych seriich b06
by dalsi briefy byly plytvani behy; aparatura prokazane nedodava.

## F2. Statistika — N/A → BLOCKED (aparatura), nikoli FAIL fyziky

0 platnych drah (6 vyzadovano). Delta>3σ ani 5% repeatabilita
nevyhodnoceny — pipeline k nim nedojde. Verdikt kampane je BLOCKED
(merici retezec), nikoli FAIL fyziky ani PASS.

## F3. Suite + regrese

- `tests/run_all.py`: **159 behu, PASS 155, FAIL 0, ERROR 0, PENDING 4 →
  VYSLEDEK: PASS (s 4 PENDING)** (4 legitimni: Studio-pending, schema
  Faze 5, 2× VariantStore baseline).
- `tests/test_f44_regression.py`: **11 testu OK** (f44 legacy zelena vc.
  `test_summary_aggregate` v legacy toleranci + pin `roll_deg`-absence).
  f55-striktni cast **PENDING** (kohorta neexistuje; exact-kept shoda
  a `roll_deg`-present netestovany, ne PASS).

## F4. Nalezy (disk/kod NEMENEN — predano vlastnikum)

1. **Auto-fill crash v Play Solo server-threadu** (V.M. l.531
   `drive.Source` read → capability). Kazdy inbox-brief bez pripraveneho
   slotu umre bez outboxu. Obchvat (MCP postavi slot) overen 2×.
   Fix (H1): auto-fill bez cteni `Source` v server-threadu.
2. **D-2 gap (novy): post-gate bleed.** Gate nameri ~100 (pass), prvni
   vzorek 86.6 (V3-r1); V3-r3 `completed` bez errors s d=0.001.
   Fix (D): fail pri first-sample mimo `entry_tol` (H1).
3. **Stuck-brake:** klientsky `_IBrake` drzi 1.0 po briefu (nil atribut
   poslední prikaz nemaze) — overeno pulsem (100→stop za 23 studu).
   Novy brief rampou prepise (OK), ale auto mezi briefy stoji na
   zabrzdenych kolech. Fix (A/D): explicitni `_IBrake=0` pri nil.
4. **Spawn-drop + zamcena kola (bez ABS) = rock/spin loterie:** V3-r1 spin
   (yaw 7.5), V2 3/3 roll>45, F44 "bounce/rock loterie".
   Fix (H1/D): spawn-settle-go (dosadnout, ustálit, TEPVE rychlost+gate).
5. **Prekazka ve spawnu = instant-stop** (postava/ejecta; V3-r3 100→0 za
   31 ms). Fix (operator): pred kampani postava mimo drahu + audit okoli
   StartLine; (kod): obsazenost sedadla pred speed-setem.
POZITIVA zive overena: `roll_deg` v KAZDEM vzorku (F5-C) ✓;
`roll_gt_45` abort 3× ✓; pre-start roll refusal 1× ✓; SUMMARY z kept
exaktne ✓; ABS read-only (`enabled=false`, `active=false`) ✓;
entry re-verify gate bezi ✓.

## F5. Cleanup — PASS (overeno zive + disk)

Live: slot znicen (`DestroyVehicle=true`), `AE_VehicleSlot`/`Jeep_*` 0,
bridge inbox/outbox 0/0. Postava primo nemanipulovana (stoji na
(-0.6,3.9,2.3) po ejectu — DOPORUCENI operatorovi preparkovat mimo
drahu pred dalsi kampani). Disk: `git status` cisty krome tohoto
reportu; `f55/` zamerne nevytvoren; sablona nedotcena.

## F6. Mapovani F5 bodu 1-10 (final)

1. arbitrace → PASS (brzdne prikazy server→klient→fyzika prokazany
   rampami + zastavenimi ve V2/V3).
2. init/slot auto-fill → FAIL (crash l.531 v session; operator-obchvat
   overen; ceka kod-fix).
3. SUMMARY zdroj → PASS (C-1 zive exakten z kept, §F1-V1).
4. rychlost 100±1 → PENDING + nalez D-2 (gate bezi; post-gate bleed).
5. ABS stav → PASS (read-only tvar ve vsech bezich).
6. roll kanal → PASS (kanal + oba gaty zive).
7. cleanup → PASS.
8. suite → PASS (155/0/4; f55-striktni PENDING).
9. kampan 3+3 → BLOCKED (0/6; 9 voidu > budget 2; aparatura §F1).
10. repeatabilita 5 % → PENDING (0 dat).

## F7. Doporuceni (F5-CLOSURE se NEDOPORUCUJE)

1. H1/D: spawn-settle-go + first-sample entry check + `_IBrake=0` pri nil
   (§F4 body 2-4).
2. Koordinator: postava mimo drahu + spawn-vicinity audit pred kampani;
   definovat `cfg_f55_b06/b09` Tune-delta (hotovo ad-hoc: BrakeBias
   0.6/0.9 — stvrdit).
3. Pote znovu Agent E: nejdriv 1 smoke-beh, pak 3+3 f55 + statistika +
   `test_summary_aggregate` (ocekava PASS) → teprve pak F5-CLOSURE.

---
# Beh E-final-II — 2026-11-18 (kampan 3+3 f55, FX2 `11a5ab9`, tataz session)

**Verdikt: BLOCKED — 0/6 platnych (9 void behu ve 3 seriich b06, vse s duvodem;
void-budget max 2/varianta prekrocen). b09: 0 briefu (neprovedeno — aparatura
prokazane nedodava, dalsi briefy by byly plytvani). `vehicle-data/telemetry/f55/`
ZAMERNE nevytvoren (zadny platny beh; completed-with-garbage dle M2/M3
precedentu nezapisuji). H suite: 159 = 155 PASS / 0 FAIL / 4 PENDING → PASS
(s PENDING). Regrese `test_f44_regression`: 11 OK (f44 legacy zelena;
f55-striktni cast netestovana — kohorta neexistuje). F5-CLOSURE: NEDOPORUCUJI.**

Session: `17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play Solo, F5 FX2 `11a5ab9`).
`start_stop_play` nikdy nevolano; sablona `.rbxm` na disku nedotcena
(`git status` cisty krome tohoto reportu); zadny teleport mimo start T03
(presuny pouze harness-`Spawn` + eject side-effect `DestroyVehicle`);
zadny FAIL potlacen (vsech 9 voidu s duvodem nize).
Konfigy: `cfg_f55_b06` (`brakes.BrakeBias=0.6`, overeno ctenim Tune),
`cfg_f55_b09` (0.9, nedoruceno); `scenario_ids=["T03"]`, inbox pres
`AESubmitConfig:InvokeServer` (Client), outbox verbatim cten.

## G0. Operator-step + freshness (live) — PASS

- `EnsureTemplateBridge` pres MCP: `ensure=true` ("sablona patchnuta,
  AE_BridgeApplied=true"), `attr=true`, `marker=true` (Drive obsahuje
  `AE_DRIVE_INPUT_BRIDGE`). Sablona na disku nesahnuta.
- Freshness vsech F5/FX2 znaku: `VerifyT03Start/SpawnT03Verified/
  ReadStartRollDeg/ReadDriveSeatXzSpeed/CheckBrakeDiag/ComputeT03Metrics/
  ClearDriveInputs/WaitForSettle/ReadVerticalSpeed/ReadABSConfig` ✓;
  `TH outboxDoc/entry_po_apply/first_sample/ClearDriveInputs` ✓;
  `TPL_attr=true`; `ScenarioDefinitions` → `T01..T07`; bridge 0/0;
  `StartLine` x=2 ✓; remotes `AERunBrief/AETelemetry/AEStatus/AESubmitConfig` ✓;
  `TestClient` LocalScript u klienta ✓; hrac + postava existuji.
- Zaver: zive bezi F5 FX2 kod. Podminka cerstve session SPLNENA → kampan spustena.

## G1. Prubeh kampane (3 serie b06, 9 behu, 0 platnych)

Spolecne: T03-only inbox (`accepted=true`); prikaz vsech behu throttle 0,
brake rampa `t/0.15→1`, steer 0; ABS `enabled=false` default (harness
nezapisuje, neni mutable); `roll_deg` v KAZDEM vzorku ✓ (F5-C zive);
`roll_gt_45` abort + pre-start roll-refusal zive pritomny (neaktivovany —
zadny beh nedojel k prevraceni).

Serie S1 (harness auto-fill, BEZ nil-ownership; postava STALA ve
spawn-volumu ~(2.9,4,0.5)): 3/3 `completed`, `errors=[]`, ALE telemetrie
zamrzla — x≡2.00/y≡2.55/v≡100.00 po cele mereni (DriveSeat), pak skok.
r1 dist=0.25 t=2.15 dur=2.7; r2 dist=2.75 t=3.19 dur=20.0 timeout;
r3 dist=0.31 t=2.15 dur=3.45. Konzole 3× `[AE_BRAKE_DIAG] pozadovano
AE_Brake=1.000 vs skutecne Values.Brake=0.000 (trva >=45 vzorku)`.
Pricina: sit-transfer vlastnictvi (167/167 dilu po briefu vlastni klient
`Adalik1219`) → server cetl zatuchle repliky (F44-M4 pricina; FX2 ji
nereklamuje — v kodu zadny `SetNetworkOwner`). Zaver: VOID 3× (stale
telemetrie, fyzikalne nesmyslne drahy; completed-with-garbage).

Serie S2 (MCP pre-build `AE_VehicleSlot`, Tune 0.6 overen, nil-ownership
167/167 PRED briefem; postava po ejectu na ~(58.6,2.8,2.3) mimo drahu):
transfer pri usednuti vratil 167/167 klientovi → servery snapshoty:
r1 `settle_timeout:vy=0.19_roll=5.93` (vy OK, roll > 5°); r2
`first_sample_mimo_toleranci:cil=100_tol=1_mereno=0.26`; r3 dtto 0.03.
FX2 guardy zafungovaly presne dle navrhu (zadne garbage). Zaver: VOID 3×.

Mezikut — ownership drzi (overeno live): nil APLIKOVAN PO usednuti →
0/167 klient, drzi 8 s+ pri trvalem sezeni (transfer se deje POUZE na
Sit-event, ne kontinualne). Diagnosticky puls (precedent F5-final):
rychlost 30 na vsech dilech → server sledoval pohyb 1.9→7.0 a zastaveni
(fresh telemetrie PROKAZANA). F44 "drzi" plati jen pro nil po sezeni.

Serie S3 (tyz slot, usednuto, nil-hold 0/167 cely brief, Tune 0.6):
gate 100±1 prosel 3/3, prvni kept-vzorek v0=100.00 (fresh ✓), ALE
kontrolni vzorek 96.09 / 96.70 / 97.75 (tol ±1) → 3/3
`first_sample_mimo_toleranci` + `nezastaveno_do_timeout` (guard abort
po 1-2 vzorcich). Post-gate bleed 2.2–3.9 studs/s v okne gate→sample.
Kandidatni priciny (kodove, vlastnik H1/D): (a) drivetrain-scrub —
`applyStartSpeed` nastavuje jen linearni rychlost, kola s nulovym
angle-momentem + nulovy plyn pri 100 = prudky prechodny odpor v prvnich
krocich; (b) dozneni klientskeho `_InBrake` po release (nil nemaze
klientsky stav, zero prislo pozde v poradi); presny podil neurcen bez
pristrojoveho zaznamu `_InBrake/Values.Brake` v okne. Zaver: VOID 3×.

b09: 0 briefu — stejna aparatura, stejna systematicka vada; neprovedeno.

## G2. Statistika — N/A → BLOCKED (aparatura), nikoli FAIL fyziky

0 platnych drah (6 vyzadovano). Δ means > 3σ ani 5% repeatabilita
nevyhodnoceny — pipeline k nim nedojde. Void-budget (max 2/varianta)
prekrocen 9 voidy jedne systematicke rodiny (S1 setup-muj, S2/S3
timing-kod). Pokracovani vyzaduje kodovy fix, ne dalsi briefy.

## G3. Suite + regrese

- `tests/run_all.py`: **159 behu, PASS 155, FAIL 0, ERROR 0, PENDING 4 →
  VYSLEDEK: PASS (s 4 PENDING)** (4 legitimni: Studio-pending, schema
  Faze 5, 2× VariantStore baseline).
- `tests/test_f44_regression.py`: **11 testu OK** (f44 legacy zelena vc.
  `test_summary_aggregate` v toleranci + pin `roll_deg`-absence).
  f55-striktni cast netestovana (kohorta neexistuje; zadne umele PASS).

## G4. Nalezy (disk/kod NEMENEN — predano vlastnikum)

1. **Sit-event transfer vlastnictvi** (kriticky, merici retezec): usednuti
   priradi cely 167-dilny assembly sedicimu klientovi (engine automatic);
   server pak cte stale/jumpy repliky. `SetNetworkOwner(nil) PRED briefem
   nestaci; PO usednuti DRZI (overeno 0/167 + fresh puls). Fix (H1):
   harness at po prvnim sezeni (nebo pred kazdym repem) reclaimne
   vlastnictvi + overi `GetNetworkOwner()==nil`, jinak void s duvodem.
   FX2 toto neresi (v kodu 0 vyskytu `SetNetworkOwner`).
2. **Post-gate bleed 2–4 studs/s** (kriticky, novy): gate 100±1 projde,
   prvni kontrolni vzorek 96–98 → `first_sample` voiduje 3/3. Podezreli:
   drivetrain-scrub (chybi angular-velocity pri speed-setu) a/nebo
   `_InBrake`-dozneni (zero pozde v poradi). Fix (H1/D): zero → CEKAT na
   decay (`Values.Brake→0`) → speed-set vcetne angle-rychlosti kol →
   gate → minimalni okno do prvniho vzorku; prip. first-tol 2–3.
3. **Auto-fill klonuje 3×** (minor, bordel): bez pre-buildu `ensureVehicle`
   nenajde `AE_VehicleSlot` (klon se jmenuje `Jeep_*`) → 1 klon/rep.
   Meritku nevadi (kazdy rep cerstvy + Tune z briefu), ale plni
   Workspace. Fix (H1): prejmenovat deploy na `AE_VehicleSlot`.
4. POZITIVA zive overena: EnsureTemplateBridge operator-step (attr+marker,
   zadny server-crash — FX2 C-1/D-1 stale pryc); SUMMARY z kept (S1 mean
   sedel exaktne, F5-final); `roll_deg` v kazdem vzorku; ABS read-only;
   settle + pre-roll + first-sample guardy voiduji presne s duvodem.

## G5. Cleanup — PASS (overeno zive + disk)

Live: `AE_VehicleSlot` znicen (`DestroyVehicle=true`), `Jeep_*` 0, bridge
inbox/outbox 0/0. Postava po ejectu na (28.2,4.9,5.7) mimo drahu (primy
presun neproveden — pouze side-effect niceni vozu). Disk: `git status`
cisty krome tohoto reportu; `f55/` zamerne nevytvoren; sablona `.rbxm`
nedotcena (pouze zivy atribut `AE_BridgeApplied` v session, coz byl
zadaný operator-step).

## G6. Mapovani F5 bodu 1–10 (final-II)

1. arbitrace → PASS (prikazy server→klient→fyzika prokazany: S1 realna
   jizda na klientovi do x≈57; S3 brzdeni s peak-decel charakterem).
2. init/slot auto-fill → ČÁSTEČNĚ (bez crashu diky FX2 — overeno; ale 3×
   klonovani + bez ownership-reclaimu, §G4.1/3).
3. SUMMARY zdroj → PASS (z kept, exaktne — potvrzeno).
4. rychlost 100±1 → PENDING + nalez G4.2 (gate bezi; post-gate bleed).
5. ABS stav → PASS (read-only tvar).
6. roll kanal → PASS (kanal + oba gaty zive).
7. cleanup → PASS.
8. suite → PASS (155/0/4; f55-striktni PENDING bez dat).
9. kampan 3+3 → BLOCKED (0/6; 9 voidu > budget 2; pricina aparatura).
10. repeatabilita 5 % → PENDING (0 dat).

## G7. Doporuceni (F5-CLOSURE se NEDOPORUCUJE)

1. H1/D (kod, mimo muj mandat): ownership-reclaim po sezeni (§G4.1) +
   gate→sample okno (decay-wait, angular-velocity, §G4.2) + slot-rename
   (§G4.3). Bez toho ma dalsi kampaň predem dany vysledek BLOCKED.
2. Pote znovu Agent E (ja nebo nastupce): smoke 1 brief → 3+3 f55 +
   statistika + `test_summary_aggregate` (ocekava PASS) → teprve pak
   F5-CLOSURE. `cfg_f55_b06/b09` = BrakeBias 0.6/0.9 (overeno, stvrdit).

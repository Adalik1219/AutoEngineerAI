# F44-T03: Agent M4 — FINÁLNÍ měření 3+3 (bias 0.6 vs 0.9, T03-only, F3 kód)

**Verdikt: FAIL (měřeno, data platná) — kritérium PASS nesplněno:**
`Δ means = 11.49 < 3σ_pooled = 14.28`, repeatability obou variant > 5 %.
6 běhů dokončeno, 0 voidů, 0 náhrad (max 2/varianta nespotřebovány).
Data: `vehicle-data/telemetry/f44/` (8 JSON, verbatim export outboxu).

Session: `17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play Solo, F3 kód na disku `e99b46a`).
`start_stop_play` nikdy nevoláno; šablona nedotčena; žádný teleport mimo start T03
(harness-Spawn); po kampani cleanup (slot zničen, bridge 0/0, workspace bez Jeep_*).

## 1. Freshness: PASS (ověřeno živě před kampaní)

- Server `TestHarness` (15 216 B): `resolveScenarioIds` ✓, `WriteDriveAttributes` ✓,
  `scenario_ids` ✓, `CODE_VERSION ae-harness-0.2.1` ✓, `AERunBrief` fire ✓.
- Klient `TestClient` (12 410 B, PlayerScripts): `AERunBrief` listener ✓.
- Bridge inbox/outbox 0/0; slot neexistoval; `StartLine` x=2 ✓; T03-only inbox
  `{"scenario_ids":["T03"]}` akceptován (`accepted=true`, config `cfg_f44_06/09`).
- Smoke = první ostrý brief 06 (místo dummy-běhu): 3 běhy + SUMMARY v outboxu.

## 2. Běhy 6/6 (cfg_f44_06_r1..r3 + cfg_f44_09_r1..r3)

Příkaz všech běhů: throttle 0, brake rampa `t/0.15 → 1`, steer 0 (server atributy
`AE_Brake` → Drive můstek; klient sedí, seat-vstupy Drive ignoruje).
ABS: `enabled=false` (default šablony, harness nezapisuje — není mutable),
`active=false, active_samples=0` ve všech 6 bězích. Stav všech běhů: `completed`,
`errors=[]`. roll_max: **N/A — SampleOnce nemá `roll_deg` kanál**
(Evaluate `roll_gt_45` je mrtvá větev; převrácení nedetekovatelné — defekt F5-4).

| běh | v0 [st/s] | dráha [st] | čas stop [s] | dur [s] | completion |
|---|---|---|---|---|---|
| 06-r1 | 100.00 | 38.0406 | 2.950 | 20.0 (timeout) | completed |
| 06-r2 | 100.00 | 39.8822 | 1.083 | 13.2 (settle) | completed |
| 06-r3 | 94.53 | 47.4984 | 1.365 | 20.0 (timeout) | completed |
| 09-r1 | 97.40 | 32.9788 | 1.863 | 20.0 (timeout) | completed |
| 09-r2 | 100.00 | 35.1064 | 3.318 | 9.45 (settle) | completed |
| 09-r3 | 100.00 | 22.8557 | 1.318 | 20.0 (timeout) | completed |

Pozn.: v0 kolísá 94.5–100 (entry-tolerance ±1 porušena 2×); 4/6 běhů končí timeoutem
(rocking karoserie překračuje práh 0.1 po zastavení — settle-loterie, ne translace).

## 3. Statistika (z decimated run-docs, tj. test-relevantní čísla) → FAIL

- 06: mean 41.8071, std 4.0940, min 38.0406, max 47.4984, delta **22.62 %**.
- 09: mean 30.3136, std 5.3446, min 22.8557, max 35.1064, delta **40.41 %**.
- Δ means = **11.4934**; pooled_std = 4.7606; 3σ = **14.2817** → Δ < 3σ → **FAIL**.
- 6/6 drah nenulových ✓ (nutná, ne postačující podmínka).
- SUMMARY v outboxu (full-sample agregace): 06 mean 42.0653/delta 21.61 %,
  09 mean 30.6524/delta 39.77 %, obě `repeatability_ok=false`.

## 4. Provozní nálezy (oprava za běhu, vše zdokumentováno, šablona netknuta)

1. **Harness auto-fill v této session neběží**: `RepairStructure` čte `init.Source`
   (V.M. l.295) → Play Solo server thread bez `PluginOrOpenCloud` capability →
   první brief zemřel bez outboxu (důkaz v konzoli). Obchvat operátora:
   `CloneVehicle+WriteTune+DeployVehicle` přes MCP-call (capability má),
   klon přejmenován na `AE_VehicleSlot` (podporovaná větev `ensureVehicle`).
2. **Chassis se bez opravy nepostaví**: `Initialize` l.8
   `require(script.Parent.README)` + l.44 `WaitForChild("README")` po přesunu
   na kořen klonu selhává/hrozí hangem (README zůstává pod Tune — M2 rozhodnutí
   pro Drive:1111/Gauges je správně). Na klon aplikován analogický patch
   (Tune-relativní README, 2 řádky, POUZE klon) + rerun přes `Disabled` toggle.
   Výsledek: 167 dílů, 0 anchored, Drive běží. Návrh F5: doplnit do RepairStructure.
3. **Vlastnictví sítě**: `Initialize` přiřazuje DriveSeat hráči
   (`SetNetworkOwner`, sedící klient) → server četl zatuchlou telemetrii
   (zamrzlé/jumpy pos/vel). Obchvat: `SetNetworkOwner(nil)` na 167 dílů po buildu;
   drží (Drive ownership sám nepřepisuje, ověřeno). F5: reclaim do Spawnu.
4. **Klientský Drive přepisuje `Values.Brake` každý frame** (`_GBrake`, 1 výskyt)
   proti server-můstku → brzda flappe; plus `abs_enabled=false` (bez ABS, kola
   se locknou v 0.15 s → bounce/rock loterie 20–40 %). Fyzika je reálná, ale
   rozptyl převyšuje efekt biasu.
5. **SUMMARY agreguje FULL-sample metriky, run-docs nesou DECIMATED přepočet**
   (step 6–11): mean −0.26, min −0.54, max −0.17 → `test_summary_aggregate`
   nemůže projít při decimation step > 1. F5: agregovat z kept-vzorků.

## 5. Suite + cleanup

- `tests/test_f44_regression.py`: **7/8 PASS, 1 FAIL** (`test_summary_aggregate`,
  42.0653 vs 41.8071 — defekt 5). Recompute/stopped/ABS/schema/repetice zelené.
- H suite (`tests/run_all.py`): **156 běhů, PASS 151, FAIL 1 (tentýž), PENDING 4,
  VYSLEDEK: FAIL**. Jediný fail celé suite.
- Cleanup ověřen: bridge inbox/outbox 0/0, žádný `AE_VehicleSlot`/`Jeep_*`,
  `git status` čistý kromě nového `vehicle-data/telemetry/f44/` + tohoto reportu.
  Postava/klient nedotčeni (žádný teleport, žádné sezení/nucené vstupy z mé strany).

## Předání

Kampaň je technicky průchozí (6 platných drah), verdikt FAIL je měřený, ne blokovaný.
Pro PASS potřeba (F5, mimo mandát M4): (a) RepairStructure README-kotvy + capability
(auto-fill); (b) arbitrace `Values.Brake` (server autoritativně) + readiness před
Spawnem; (c) SUMMARY z kept-vzorků; (d) `roll_deg` kanál do SampleOnce; jinak se
5% repeatability s locknutými koly bez ABS nedá splnit a `test_summary_aggregate`
selže systematicky.

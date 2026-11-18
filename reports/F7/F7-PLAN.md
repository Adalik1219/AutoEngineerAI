# F7-PLAN — Full Vehicle Runtime, Drive & End-to-End Validation

## F7.0 Audit a delegování (dokončeno + recovery-verifikováno)

- F6 baseline `8274e19ac39fe00bf183737f9bc1d4655a5e92dd` (remote `origin/main`, ověřeno `git ls-remote` Agentem A, deleg `deleg_beff55a5`).
- Recovery audit `deleg_beff55a5` (5/5 read-only): A = remote HEAD `8274e19`, 15 commitů vypsáno, `d3672b1` jen lokálně (ahead 1, na GitHubu 404), F7 větev žádná; B = `reports/F7/` jen lokálně (blob `c74d5180`), na `origin/main` neexistuje; C = F6 nezávisle potvrzena (6/6 completed+stopped, b06 0.734 % PASS, b09 5.99 % FAIL jen branou; otevřeno: server-throttle/steering, diag-kanál brzdy, Rojo 7.2.1 vs 7.7.x, kužely `z=-10` dočasné, bez ABS-emulace); D = předchozí delegace `deleg_e32f6a08` VERIFIED s výhradou (5/5 transkriptů, manifest 14:46:43→14:48:22); E = F7.0 BLOCKED do dodání A–D a pushnutí (žádná vada, jen nedodané vstupy).

- HEAD: `8274e19ac39fe00bf183737f9bc1d4655a5e92dd` (F6 closure), strom čistý.
- F6 výchozí stav: coast drží, brzda 100→0/144 m, b06 3/3 delta 0.73 % PASS, b09 3/3 delta 5.99 % (brána >5 % nesplněna, r2 outlier otevřen). Klientský Drive za server-nil ownership dekorativní — pohon/řízení neprokázány.
- Delegace `deleg_e32f6a08`, 5 subagentů paralelně (read-only, bez Studia, bez zápisu):
  - sa-0 Agent A — Drive & ownership (throttle/steering/brake architektura, lifecycle, převody/RPM).
  - sa-1 Agent B — Physics & wheels (#AV/#BV, valení, spin/trakce, PASS podmínky).
  - sa-2 Agent C — Track & collision (mapa 3000 studs, Blockcast plán, full-lane kritérium).
  - sa-3 Agent D — Statistika (nezávislý přepočet 6 jízd, b09 r2 outlier, návrh opakování).
  - sa-4 Agent E — Code & QA review (F6 diff, regrese, RemoteEventy, akceptační kritéria).
- Studio/session pravidlo: živou Studio session ovládá **pouze koordinátor**. Agenti A–E pracují nad commitem `8274e19`, analyticky, bez Play/Edit přepínání, bez Rojo push, bez souběžných změn souborů.
- Po doručení výsledků: integrace do F7.1–F7.5, řízené commity s rollback možností.
- F6 analytické výsledky `deleg_e32f6a08` (A–E, nad `8274e19`): A = zápisy klienta zahazuje server-nil ownership (167 dílů, `ScenarioRunner.lua:233-258`), `seat.Throttle/Steer` Drive ignoruje, návrh `AEDriveCmd` + server-throttle/ABS; B = kola 4/4 zdravá (W≈74 = valení ±0.8 %), brány ω=v/R ±3 %, |ωR−v|≤20, yaw≤0.25, lat≤2.0, 6 izolovaných testů; C = trať x=0–3800 volná, 0 neviditelných překážek, **mezera: telemetrie bez kontaktního kanálu**, full-lane plán + kritérium; D = 6/6 přepočet bit-přesně sedí, b09 r2 = fyzikální rozptyl (peak 51.67 @2.47 s), postup instrumentace → n≥10; E = F6 správně, kritické K1 (matcher `"F"`), K2 (cleanup scope), K3 (`#AV=0`/bez ABS), QA testy 1–9.

## F7.1–F7.5 (řízeně, jednoproměnné commity, rollback)

1. F7.1 pohon: K3 (throttle + ABS-emulace / T03-guard) + `AEDriveCmd` + K1 + N2/N3; test throttle-rampa, RPM/gear, brake-smoke beze změny.
2. F7.2 řízení: RE Drive-steer řetězce → server-steering, obě strany, brány z B.
3. F7.3 trať: kontaktní listener + full-lane 3000 studs + Blockcast box Z=8/Y=4–5.
4. F7.4 opakovatelnost: instrumentace (D) → kampaň n≥10, b09 až po vysvětlení r2.
5. F7.5 QA: E testy 1–9 (facing-negativ, K1/K2/K3, manual-mode, template-diff, Rojo 7.7.x).

## Ochranná pravidla (brief §8)

JeepTemplate.rbxm nikdy nepřepisovat; RobloxSimulator read-only; žádná Python simulace jako důkaz runtime; žádná teleportace/velocity-náhrada pohonu; nevypínat kolize; nemazat FAILED/VOID běhy; žádný PASS bez měření; jednoproměnné změny.

## Akceptace (13 kritérií, stav po F6)

1 throttle — NOT IMPLEMENTED · 2 rozjezd fyzikou — NOT IMPLEMENTED · 3 převodovka/RPM — NOT IMPLEMENTED · 4 steering — NOT IMPLEMENTED · 5 kola 4/4 — PENDING (W≈74 pozorováno, izolace chybí) · 6 coast scrub — PASS (coast drží) · 7 brzda — PASS (100→0/144 m) · 8 celá trať — NOT IMPLEMENTED · 9 kolize identifikovatelné — PENDING (Blockcast částečný) · 10 náhlé zastavení — PENDING · 11 cleanup — PASS (F6 2× ověřeno) · 12 logy — PASS (run-001..004) · 13 QA — PENDING (F7 Agent E).

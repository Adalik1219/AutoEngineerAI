# F6-QA — nezávislé ověření (Agent E)

Session `17ce64ee…`, commity `4cab440` → `3572295` (F6), Play Solo.
Metoda: kritické testy zopakovány v živé session (ne převzaty), archiv
přepočítán nezávisle pythonem z RUN JSONů (níže), šablona a suite ověřeny.

## 1. Opakované kritické testy (živě)

- Facing: `ReadVehicleFacingX` 0.993 / 0.985 (2×, různé sloty) — čumák +X.
- Coast bez brzdy: run-002 99.8→99.4 (1.5 s) + run-004-setup 99.9→98.7
  (3.5 s, dx=337.6) — kola volná, W≈74 = valení bez prokluzu.
- Brzda: 100→0 za ~2.25 s, dx=144.4, peak 60 (proti scrub 37/~3000).
- Blockcast před kapotou (plná šířka/výška, 4×1000): kužely pryč (z=-10),
  jen kolej z=6.6 (mimo stopu) a EndWall (cíl).
- V2 `_PBrake` release: mirror `PBrake=false` po ClearDriveInputs (bez eject-tance).
- Server-brzda: BV=0 po zero bez ejectu; server 200 drží oběma směry.
- Cleanup: sloty 0, PlayerGui Interface 0, bridge složky 0 (2× ověřeno).

## 2. Nezávislý přepočet archivu (python, z RUN JSONů)

- run-003: n=3, mean=152.62, std=0.52, delta=0.73 % — shoduje se SUMMARY.
- run-004: n=3, mean=150.06, std=3.93, delta=5.99 % — shoduje se SUMMARY.
- Všech 6: completed, 0 errors, stopped=true, sample_count sedí s kept-vzorky,
  v0 prvního vzorku sedí se summary (≤0.05).

## 3. Regrese a integrita

- `tests/run_all.py`: 159 = 155 PASS / 0 FAIL / 4 PENDING (stejné 4 legitimní).
- Šablona `JeepTemplate.rbxm`: `git diff` prázdný (nedotčena na disku).
- Živé patche (V2 bridge, AE_BridgeApplied) pouze v session, nikdy v `.rbxm`.
- Konzole: 0× `DriveSeat is not a valid member`, 0× Drive chyby (2 kampaně).

## 4. Výhrady (neblokují F6 PASS, evidováno)

- b09 repeatabilita 5.99 % > 5 % (r2 peak 52): platné jízdy, brána nesplněna.
  Potřeba větší n — mimo mandát F6 (žádná další kampaň T03).
- Server neobsahuje ABS-emulaci (tqABS=1) ani plyn (T03 ho nepotřebuje).
- Klientský Drive je za server-nil ownership dekorativní (zápisy motorů
  zahazovány) — pro T03 nevadí, pro manuální jízdu ano (známé omezení).
- Rojo plugin 7.2.1 vs server 7.7.1: jedna chimerická sync (healnuto
  re-connectem + full re-push); doporučeno sladit verze.

Verdikt QA: F6-CLOSURE DOPORUČENO s verdiktem níže.

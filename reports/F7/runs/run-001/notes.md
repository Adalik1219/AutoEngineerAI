# run-001 notes (T01 smoke, 3 repliky)

## Co se stalo
- Rep 1 startovala 3 s po Play: Initialize LoadDelay 3 s -> prvni ~3 s ServerDrive bez #AV
  (warn `moment_nezapsan`), pak normalni rozjezd. Ponauceni: prvni rep po Play je vzdy
  `studeny start`; pri kampanich zahodit / oznacit warm-up.
- Vsechny 3 repliky: plny vykon, razeni 1->5, naraz do EndWall (T01 nema brzdu) -> completed.
- S4 manualne: DestroyVehicle OK (0 stale interfaces), redeploy+Sit+Car.Value rebind OK,
  prvni reclaim trefil race s Initialize buildem (`cteni_GetNetworkOwner_selhalo`), retry po
  dostavbe PASS. Zjisteni: harness Spawn reklamuje hned po Deploy; u cerstveho buildu muze
  selhat - doporuceni retry do Spawn (mimo scope F7.1, slot v kampanich preziva).
- Klientske Values (rpm/gear) kontaminuji telemetrii pred startem ServerDrive (r1 t<3.2).
  Po launch plati server-autorita. Doporuceni: do collector flag `server_drive_active`.

## Metrika
- Absolutni brana |dp-v*dt|>2 na kept-gridu (0.35 s) je pri v>100 prilis tesna (aliasing).
  Rozhodujici je integralni pomer draha/int_vdt = 0.989-1.000 + 0 skoku + shoda shift-prahu.
- Relativni T3 (>=95 % <0.15): r3 96.2 %, r2 93.8 %, r1 81.7 % (aliasing pri pretizeni serveru
  na zacatku). Pro kampane: telemetrie s warp=1 nebo plna 60Hz telemetrie do outboxu.

## Otevreno do F7.2
- Q4 manual mod zivy test; kontaktni kanal kolizi (Agent C); per-kolo W=v/R kanal.
- Sync poznamka: Rojo bylo behem dne vypnute (uzivatel reconnectnul) - nove soubory
  (ServerDrive.lua) Studiu nedotekly, proto inline do ScenarioRunner. Overeno live 497-498.

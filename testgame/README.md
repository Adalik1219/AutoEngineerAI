# AutoEngineerTestGame — testovací laboratoř

Toto **není hra**. `testgame/` je izolovaná laboratoř pro FÁZI 9 projektu
AutoEngineerAI: ověřování chování vozidel ve skutečném Roblox physics enginu
(RUN testy, viz `docs/ROBLOX-RUNTIME.md` §8–§10).

- Zdrojáky harnessu se synchronizují ze souborů na disku přes **Rojo**
  (přístup B dle `docs/ROBLOX-RUNTIME.md` §3).
- Samotný fyzikální test vždy běží jako Play session ve Studiu nad tímto
  placem; lokální simulace v `src/Physics` není důkazem (úroveň `SIM`).
- Originál `chasis.rbxm` sem nikdy nepatří; šablony vozidel žijí až v
  `ServerStorage/VehicleTemplates` jako verzované kopie.
- `Remotes` (RemoteEvents/RemoteFunctions) nejsou v Gitu — vytváří je za běhu
  `RuntimeController`. Proč: viz `docs/ROJO-SETUP.md`.

## Rychlý start

1. Nainstaluj Rojo (viz `docs/ROJO-SETUP.md`).
2. Ověř build (musí projít i s chybějícími soubory ostatních agentů):
   `rojo build testgame/default.project.json -o $TMPDIR/ae_test.rbxlx`
3. Spusť sync: `rojo serve testgame/default.project.json`
4. Ve Studiu se připoj přes Rojo plugin na port **34872** a spusť Play.
5. První funkční test: scénář `straight-accel-0-100` (RUN-001),
   viz `docs/ROBLOX-RUNTIME.md` §10.

## Struktura

| Soubor | Účel |
|--------|------|
| `default.project.json` | Rojo projekt: název, port, DataModel strom (Agent B) |
| `docs/ROJO-SETUP.md` | Instalace, build/serve, plugin, porty, Remotes, PENDING partitiony |
| `src/` | Zdrojáky ostatních agentů (vlastněné mimo Agenta B) |

# Rojo setup — AutoEngineerTestGame

Ověřeno s **Rojo 7.7.1** (`rojo --version`).

## 1. Instalace Rojo

- **CLI:** postup dle oficiálního repozitáře Rojo
  (https://github.com/rojo-rbx/rojo, sekce Installation).
- **Studio plugin:** ve Studiu záložka `Plugins` → `Manage Plugins` →
  instaluj `Rojo` z Creator Store. Plugin je protistrana příkazu `rojo serve`.

## 2. Build (kontrola bez Studia)

```sh
rojo build testgame/default.project.json -o $TMPDIR/ae_test.rbxlx
```

- Úspěch = exit `0` a řádek `Built project to …`.
- Výstupní `.rbxlx` je zahozený artefakt (necommitovat).
- Na Windows nativnímu `rojo` předej nativní cestu výstupu
  (např. `C:/Users/<user>/AppData/Local/Temp/ae_test.rbxlx`); MSYS-style
  `/tmp/…` nativní binárka nezapíše (ověřená chyba `os error 3`).

## 3. Serve + připojení Studia

```sh
rojo serve testgame/default.project.json
```

1. Ve Studiu otevři place (nebo prázdný baseplate).
2. V Rojo pluginu klikni Connect a zadej `localhost:34872`
   (port = `servePort` v `default.project.json`).
3. Zelený stav = sync aktivní. Změna `.lua` souboru na disku se promítne
   do odpovídající instance ve Studiu.

Mapování soubor → instance (Rojo 7):

| Soubor | Instance |
|--------|----------|
| `*.server.lua` | `Script` |
| `*.client.lua` | `LocalScript` |
| `*.lua` | `ModuleScript` |
| `*.rbxmx` / `*.rbxm` | model (obsah souboru) |

## 4. Sync kontrola

1. `rojo build` projde s exit `0`.
2. Plugin hlásí připojeno na `localhost:34872`.
3. Zkušební změna: uprav komentář v libovolném syncnutém `.lua`,
   ve Studiu se obsah odpovídajícího scriptu změní (a naopak nic
   mimo syncnutý strom se nemění).
4. `Workspace/TestTrack`, `TestSpawn`, `TestEnvironment` existují jako
   modely po syncu `.rbxmx` souborů.

## 5. Kolize portu 34872

- Najednou smí běžet **právě jeden** `rojo serve` na portu 34872.
- Příznak kolize: `serve` spadne / plugin se nepřipojí (port obsazený).
- Řešení: najdi a ukonči druhý proces `rojo serve`, pak spusť znovu.
  Port se nemění lokálně bez koordinátora (klienti očekávají 34872).

## 6. Proč `Remotes` nejsou v Gitu

`RemoteEvent`/`RemoteFunction` instance pod `ReplicatedStorage/AutoEngineer`
vytváří za běhu `RuntimeController` (serverový init), nikoli Rojo sync.

- Důvody: (a) jde o runtime wiring, ne verzovaný kód; (b) statický popis
  remotů v Gitu by se rozcházel s tím, co controller skutečně vytvoří
  (duplicity / sirotci po přejmenování); (c) klient (`TestClient`) je
  čeká přes `WaitForChild`, takže pořadí startu nehraje roli.
- Autoritou seznamu remotů je kód `RuntimeControlleru`, ne adresář.

## 7. PENDING partitiony (stav Agenta B)

`rojo build` padá na každém `$path`, jehož cíl na disku chybí (ověřeno:
`$path that could not be turned into a Roblox Instance`), a `project.json`
odmítá neznámé klíče (ověřeno: `Failed to deserialize JSON`). Proto
`default.project.json` aktuálně obsahuje **kostru** (`$className`
uzly dle zamčeného stromu) a `$path` vazby **pouze tam, kde cíl existuje**.
Jediný dosud chybějící cíl je `TestClient.client.lua` — jeho uzel zůstává
placeholder `LocalScript`, build prochází s tím, co existuje.

| Uzol | `$path` (relativně k `testgame/`) | Stav |
|------|-----------------------------------|------|
| `ReplicatedStorage/AutoEngineer` | `src/ReplicatedStorage/AutoEngineer` | aktivní |
| `ServerScriptService/AutoEngineer` | `src/ServerScriptService/AutoEngineer` | aktivní |
| `ServerStorage/VehicleTemplates` | `src/ServerStorage/VehicleTemplates` | aktivní |
| `StarterPlayer/StarterPlayerScripts/TestClient` | `src/StarterPlayerScripts/TestClient.client.lua` | **PENDING** — soubor zatím neexistuje |
| `Workspace/TestTrack` | `src/Workspace/TestTrack.rbxmx` | aktivní |
| `Workspace/TestSpawn` | `src/Workspace/TestSpawn.rbxmx` | aktivní |
| `Workspace/TestEnvironment` | `src/Workspace/TestEnvironment.rbxmx` | aktivní |

Finální build se všemi partitionami ověří koordinátor.

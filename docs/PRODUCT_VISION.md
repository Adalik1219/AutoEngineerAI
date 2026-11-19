# Product Vision – AutoEngineerAI v hybridním režimu

**Stav:** návrh v1 (ke schválení).
**Vazba:** `docs/PROJECT-PLAN.md` (původní vize plné autonomie), `docs/HYBRID_WORKFLOW.md` (proces), `docs/ARCHITECTURE.md` (technika).

---

## 1. Co je AutoEngineerAI

Autonomní inženýrský systém pro Roblox vozidla. Vezme existující Roblox model auta (RBXM),
načte technickou specifikaci skutečného cílového vozu a iterativně ho převádí tak, aby se
geometrie, fyzika a jízdní chování co nejvíce přiblížily předloze. Každá změna má technické
zdůvodnění, každá důležitá změna je ověřena měřením.

## 2. Proč hybridní režim

Plná autonomie (včetně automatického řízení Roblox Studia) je dlouhodobý cíl, ne podmínka
prvního produktu. Hybridní režim dělí práci tam, kde je každá strana nejsilnější:

- **Stroj (AutoEngineerAI):** čte RBXM, počítá rozměry a fyziku, mapuje na A-Chassis parametry,
  generuje konfigurace s rollbackem, připravuje testovací protokoly, vyhodnocuje měření statistikou.
- **Člověk (ve Studiu):** aplikuje pracovní konfiguraci, ručně provede předepsané jízdy,
  zapíše naměřené hodnoty do strukturovaného formuláře.

Python simulace (`src/Sim/`, `src/Physics/`) slouží **pouze jako matematická reference pro výpočty**.
Nikdy se nevydává za důkaz chování v Roblox Physics Engine. Jediným důkazem jízdního chování
je ruční test ve Studiu s archivovanou telemetrií.

## 3. První produkt

Převod libovolného A-Chassis RBXM modelu na **Ford Mustang GT 2024 EU (Fastback, manuál,
standardní GT)** — viz `docs/VEHICLE-SPECIFICATIONS.md`. Prvním skutečným výstupem je
geometrický rozdílový report (M1–M3): rozvor, rozchody, průměry a pozice kol — zdroj vs. Mustang.

## 4. Co produkt NENÍ

- Není automatický řidič Studia (žádné ovládání editoru bez uživatele).
- Není generátor výkonových křivek z maxim (UNKNOWN zůstává UNKNOWN).
- Není optimalizátor, který mění Tune naslepo — každá změna má mapování cíl → parametr → důvod.
- Nepřepisuje historii F4–F7: ty jsou experimentální a validační předchůdci (viz `docs/PROJECT_STATUS.md`),
  ne důkaz hotového produktu.

## 5. Stupnice zralosti (závazná pro celý projekt)

`NOT IMPLEMENTED → IMPLEMENTED → CODE-VERIFIED → RUNTIME-VERIFIED`

- **IMPLEMENTED:** kód existuje a prochází unit testy.
- **CODE-VERIFIED:** prochází integrační + akceptační testy (včetně 4 PENDING testů ve `tests/`, které čekají na Studio/artefakty).
- **RUNTIME-VERIFIED:** existuje archivovaný ruční test z Roblox Studia s telemetrií. Přechod bez něj je zakázán.
- `PENDING` není `PASS`. `CODE-VERIFIED` není `RUNTIME-VERIFIED`.

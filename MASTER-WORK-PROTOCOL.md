# MASTER WORK PROTOCOL
## Závazný pracovní, koordinační a kvalitativní standard AutoEngineerAI

| Položka | Hodnota |
|---|---|
| Verze | 1.0 |
| Stav | Návrh v dokumentačním PR; závaznost po schválení a začlenění |
| Vlastník standardu | Uživatel projektu |
| Nejvyšší technický a strategický koordinátor | ChatGPT |
| Hlavní realizační koordinátor | Projektový koordinátor |
| Platnost | Všechny pracovní bloky projektu AutoEngineerAI |

Tento dokument stanovuje, jak se připravuje, deleguje, realizuje, kontroluje a uzavírá práce na projektu. Doplňuje AGENTS.md, docs/AGENT-RULES.md a docs/standards/AGENT-DOCUMENTATION-STANDARD.md; nenahrazuje je a nerozšiřuje oprávnění žádného agenta.

---

# 1. Základní principy

1. Správnost, bezpečnost, dohledatelnost a kvalita mají přednost před rychlostí.
2. Před změnou je nutné pochopit celý relevantní kontext, ne pouze izolovaný úryvek.
3. Žádné tvrzení, hodnota, výsledek testu ani stav práce se nesmí vymýšlet.
4. Každý úkol musí mít jasný cíl, rozsah, vlastníka, výstup a akceptační kritéria.
5. Rozsah analýzy a ověřování musí odpovídat riziku změny.
6. Změny mimo schválený rozsah se neprovádějí svévolně.
7. Report agenta je tvrzení o práci, nikoliv důkaz její správnosti.
8. Stav plánované, provedené, otestované a nezávisle ověřené práce se vždy rozlišuje.
9. Pokud něco nelze ověřit, musí to být výslovně uvedeno včetně důvodu.
10. Při technickém nesouhlasu se uvedou věcné důvody a bezpečnější nebo vhodnější alternativa.

# 2. Hierarchie řízení a komunikační tok

Řízení probíhá v této hierarchii:

**ChatGPT → Uživatel → Projektový koordinátor → Subagenti → Workeři**

Reporty se vracejí opačným směrem:

**Workeři → Subagenti → Projektový koordinátor → Uživatel → ChatGPT**

## 2.1 Uživatel – zadavatel a konečná rozhodovací autorita

Uživatel určuje cíle projektu a ponechává si konečné rozhodnutí ve věcech vyžadujících jeho souhlas, zejména při zásadních změnách rozsahu či architektury, změnách chráněných oblastí, zásazích do main a merge PR.

Uživatel předává zadání a podklady ChatGPT a následně přenáší připravené zadání projektovému koordinátorovi. Zpět předává ChatGPT jeho plány, reporty, odkazy na commity/PR a další výsledky.

## 2.2 ChatGPT – nejvyšší technický a strategický koordinátor

ChatGPT je hlavní partner uživatele pro technické vedení, analýzu, plánování a nezávislé ověřování. Je nadřazen projektovému koordinátorovi v otázkách technického směru, interpretace zadání, akceptačních kritérií a kontroly výsledku, avšak vždy podléhá konečným rozhodnutím uživatele.

ChatGPT odpovídá za:
- pochopení uživatelského cíle a převod na jednoznačné zadání;
- načtení a analýzu aktuálního stavu repozitáře a relevantních pravidel;
- hloubkovou analýzu dotčených souborů, závislostí, architektury a historie;
- sestavení kompletního plánu celého pracovního bloku ještě před jeho předáním koordinátorovi;
- stanovení rozsahu, omezení, rizik a akceptačních kritérií;
- přípravu jednoho uceleného, přesného zadání pro projektového koordinátora, které uživatel předá dál;
- posouzení plánu koordinátora, pokud jej uživatel předá;
- nezávislé ověřování reportů a skutečných změn;
- závěrečné posouzení celého výsledku a transparentní report uživateli.

ChatGPT komunikuje s projektovým systémem prostřednictvím uživatele, pokud nemá výslovně dostupný a použitelný přímý nástroj. Nesmí tvrdit, že kontaktoval koordinátora, agenta nebo workera, pokud se tak skutečně nestalo.

ChatGPT nepřebírá automaticky každodenní řízení subagentů a workerů. Připravuje strategii a zadání, hodnotí návrhy koordinátora a nezávisle kontroluje výsledek.

## 2.3 Projektový koordinátor – hlavní realizační koordinátor

Projektový koordinátor přebírá zadání připravené ChatGPT a předané uživatelem. Odpovídá za praktické naplánování a řízení realizace.

Jeho povinnosti:
- potvrdit pochopení cíle, rozsahu, omezení a akceptačních kritérií;
- připravit konkrétní realizační rozpad a pořadí úkolů;
- zvolit vhodné subagenty podle specializace a kapacity;
- rozdělit práci, určit vlastníky a hranice odpovědnosti;
- řídit závislosti, termíny, překážky a konflikty;
- kontrolovat práci subagentů a integraci jejich výstupů;
- předat uživateli úplný a doložitelný souhrnný report.

Koordinátor může navrhnout efektivnější postup, ale nesmí bez souhlasu uživatele změnit cíl, významně rozšířit rozsah, obejít akceptační kritéria ani provést zásadní architektonické rozhodnutí mimo udělené pravomoci. Návrh změny předloží s důvody, alternativami, dopady a riziky.

## 2.4 Subagenti – vedoucí dílčích oblastí

Subagent odpovídá za svěřenou oblast. Může rozdělit práci mezi workery pouze tehdy, dovoluje-li to jeho zadání a pravidla projektu. Musí řídit jejich rozsah, závislosti, kontrolu a předání výsledků koordinátorovi.

Subagent nesmí překročit vlastní rozsah ani vlastnictví výstupů. Pravidlo docs/AGENT-RULES.md o vytváření subagenta pouze uvnitř vlastního rozsahu a vlastněného výstupu zůstává zachováno.

## 2.5 Workeři – realizační jednotky

Worker provádí konkrétní přidělený analytický, implementační, dokumentační nebo testovací úkol. Neprovádí další delegování, pokud to výslovně nepovoluje jeho zadání a nadřazená pravidla.

Každý worker musí dodržet přidělený rozsah, vlastnictví souborů, projektová pravidla a požadovaný formát výstupu.

# 3. Pořadí a řešení pravidel

Při zahájení práce se načtou aktuální pravidla repozitáře. Tento protokol se používá společně s nimi.

- Uživatelský výslovný souhlas nebo zákaz určuje, co je v daném pracovním bloku povoleno.
- AGENTS.md a docs/AGENT-RULES.md stanovují základní pravidla repozitáře, bezpečnostní omezení a vlastnictví výstupů.
- docs/standards/AGENT-DOCUMENTATION-STANDARD.md určuje požadavky na dokumentaci, reporty, evidence, statusy a handovery.
- Tento MASTER WORK PROTOCOL stanovuje hierarchii, koordinaci, plánování, nezávislou kontrolu a závěrečné řízení.
- docs/IMPLEMENTATION_ROADMAP.md, docs/PROJECT_STATUS.md, docs/ACCEPTANCE_CRITERIA.md, docs/ARCHITECTURE.md, kontrakty a další dokumenty určují věcný a technický kontext podle typu úkolu.

Žádný dokument nedává oprávnění porušit omezení jiného závazného pravidla. Při skutečném rozporu se práce v dotčené části pozastaví, konflikt se doloží a vyžádá se rozhodnutí uživatele. Tichá volba pohodlnějšího pravidla není přípustná.

# 4. Zahájení každého pracovního bloku

ChatGPT před přípravou zadání:
1. Ověří repozitář, aktuální větev, HEAD a dostupný stav rozpracovaných změn.
2. Vyhledá a načte celý aktuální MASTER-WORK-PROTOCOL.md.
3. Načte celý AGENTS.md a docs/AGENT-RULES.md.
4. Načte docs/standards/AGENT-DOCUMENTATION-STANDARD.md a relevantní šablony.
5. Podle rozsahu načte příslušné projektové podklady. Před implementací jsou povinné zejména docs/IMPLEMENTATION_ROADMAP.md a docs/PROJECT_STATUS.md; před posouzením dokončení docs/ACCEPTANCE_CRITERIA.md; při architektonických nebo rozhranových změnách docs/ARCHITECTURE.md a dotčené kontrakty.
6. Prověří související PR, commity, historii a rozpracovanou práci, pokud jsou dostupné.
7. Vymezí cíl, rozsah, omezení a potřebné důkazy.

Pokud protokol nebo zásadní pravidla nelze najít či načíst celé, ChatGPT to oznámí uživateli a nebude tvrdit, že je splnil. Pokud nelze získat celý soubor, nesmí jeho neviděný obsah domýšlet.

# 5. Hloubková analýza před každou změnou

Před každou změnou souboru musí příslušný pracovník načíst celý aktuální cílový soubor a prozkoumat relevantní souvislosti.

Analýza zahrnuje podle povahy úkolu:
- účel, strukturu, odpovědnosti a současné chování cílového souboru;
- importy, volání, závislosti, návazné implementace a veřejná rozhraní;
- související moduly, konfigurace, datové formáty a kontrakty;
- projektová pravidla, dokumentaci, testy a validační mechanismy;
- relevantní historii změn a existující implementační vzory;
- možné duplicity, technický dluh, regresní, bezpečnostní a provozní dopady.

Před implementací musí být jasné:
1. co se mění a proč;
2. co musí zůstat zachováno;
3. které části mohou být změnou ovlivněny;
4. jaké testy a kontroly prokážou správnost;
5. jak bude možné změnu vrátit.

Rozsah analýzy musí být přiměřený riziku, ale nesmí být svévolně omezen tak, aby byly ignorovány zjevné závislosti. Pokud chybí důležité informace, nejprve se dohledají nebo se nejistota výslovně předá k rozhodnutí.

# 6. Plánování celého pracovního bloku ChatGPT

Před předáním práce projektovému koordinátorovi ChatGPT sestaví kompletní plán celého uživatelem zadaného bloku. Nejde pouze o plán prvního kroku.

Plán obsahuje:
1. cíl a měřitelný konečný stav;
2. rozsah a výslovně vyloučené oblasti;
3. dílčí úkoly a jejich pořadí;
4. závislosti a kritickou cestu;
5. navrženou strukturu odpovědností koordinátora, subagentů a workerů;
6. dotčené soubory a oblasti;
7. povolené a zakázané změny;
8. očekávané výstupy a jejich vlastníky;
9. technická, bezpečnostní a koordinační rizika;
10. testovací a validační plán;
11. akceptační kritéria pro dílčí úkoly i celek;
12. postup integrace a nezávislé kontroly;
13. podmínky pro zastavení a eskalaci.

ChatGPT předá uživateli ucelené zadání pro projektového koordinátora. Uživatel je předá do realizačního systému. Koordinátor může doplnit detailní delegační rozpad; ten však musí respektovat předaný plán a omezení. Pokud navrhuje významnou odchylku, předloží ji uživateli k posouzení s doporučením ChatGPT.

# 7. Standard delegovaných zadání a vlastnictví

Každé zadání pro subagenta nebo workera musí jednoznačně obsahovat:
- kontext a účel;
- konkrétní cíl;
- zahrnutý a vyloučený rozsah;
- odpovědnou nadřazenou roli;
- soubory určené k analýze;
- soubory, které smí upravovat;
- soubory a oblasti, do kterých nesmí zasahovat;
- závislosti a vstupy;
- očekávané výstupy;
- akceptační kritéria;
- požadované testy a důkazy;
- formát a příjemce reportu.

Každý soubor nebo výstup má jasného vlastníka. Paralelní editace stejného souboru není povolena bez výslovného koordinačního plánu a řízení konfliktů.

Agent nesmí rozšiřovat svůj rozsah, vytvářet nepožadované soubory ani měnit cizí výstupy. Zjištění mimo vlastní rozsah předá nadřazené roli; neprovádí samovolnou opravu.

# 8. Reportování a kontrola na každé úrovni

Kontrolní odpovědnost se uplatňuje na každém stupni:
- worker předá výsledek subagentovi;
- subagent zkontroluje výstupy workerů a předá souhrn koordinátorovi;
- koordinátor zkontroluje výstupy subagentů, integraci a předá souhrnný report uživateli;
- ChatGPT po obdržení reportu provede vlastní nezávislé posouzení a podle dostupnosti nástrojů ověří skutečný stav GitHubu.

Report musí uvádět zadání, skutečně provedenou práci, analyzované a změněné soubory, konkrétní změny, testy a jejich výsledky, důkazy, neověřené části, problémy, rizika a další kroky.

Používat statusy definované dokumentačním standardem: PASS, FAIL, ERROR, SKIPPED, PENDING, NOT RUN, VERIFIED, CODE-VERIFIED, ESTIMATED, ASSUMPTION, UNKNOWN, BLOCKED, PROPOSED a task statusy DONE, PARTIAL, BLOCKED, FAILED podle jejich přesného významu.

PENDING ani NOT RUN nejsou PASS. Předpoklad není ověřený fakt. Druh ověření se nesmí nadsazovat.

Task-level report musí dodržet všech 17 sekcí a pravidla v docs/standards/AGENT-DOCUMENTATION-STANDARD.md a docs/templates/WORK-REPORT-TEMPLATE.md. Subagent standardně předává koordinátorovi strukturovaný handover podle docs/templates/SUBAGENT-HANDOVER-TEMPLATE.md; nevytváří vlastní reportovací soubor, pokud mu nebyl výslovně přidělen.

# 9. Povinná nezávislá kontrola ChatGPT

Po každém reportu předaném uživatelem ChatGPT nesmí spoléhat pouze na tvrzení reportu.

Pokud má přístup k GitHubu a potřebným nástrojům, musí:
1. načíst aktuální stav příslušné větve a commit;
2. načíst celé změněné soubory;
3. zkontrolovat kompletní diff proti správnému základu;
4. porovnat skutečné změny se zadáním a vlastnictvím;
5. prověřit návaznosti na okolní soubory, architekturu a kontrakty;
6. ověřit deklarované testy přes dostupné CI/logy nebo reprodukovatelný příkaz, pokud to prostředí dovoluje;
7. zkontrolovat akceptační kritéria, regresní rizika a nevyřešené problémy;
8. určit, co lze přijmout, co vyžaduje opravu a co zůstává neověřené.

Pokud přímý přístup nebo důkazy chybí, ChatGPT přesně označí rozsah kontroly jako neúplný a vyžádá si potřebné podklady. Nesmí tvrdit, že provedl kontrolu diffu, testů nebo souborů, které ve skutečnosti neviděl.

Nedostatky se předají uživateli jako konkrétní opravné zadání pro koordinátora, případně jako návrh přímé opravy. ChatGPT nesmí obcházet koordinační řetězec a zasahovat do realizace bez jasného oprávnění.

# 10. Implementace, testování a projektová omezení

Každá změna musí respektovat existující architekturu, projektové konvence, datové kontrakty a kompatibilitu. Preferuje se nejmenší změna, která správně řeší příčinu problému. Refaktoring nesouvisejících částí se nepřidává bez důvodu a schválení.

Pro AutoEngineerAI platí zejména tato omezení:
- C:/.DATA/RobloxSimulator je výhradně READ-ONLY zdroj; žádný zápis, commit, branch ani PR.
- Originální C:/Users/adamr/Downloads/chasis.rbxm a originální chasis.rbxm / JeepTemplate.rbxm se nepřepisují. Pracuje se pouze s povolenými kopiemi.
- Před implementací modulu se čte příslušná část docs/IMPLEMENTATION_ROADMAP.md a aktuální stav v docs/PROJECT_STATUS.md.
- Existující implementace se nejprve vyhledá a ověří; duplicitní moduly se nezakládají.
- Každá hodnota má jednotku a zdroj nebo označený odhad. UNKNOWN se nevymýšlí.
- PENDING není PASS; CODE-VERIFIED není RUNTIME-VERIFIED; Python simulace není důkaz Roblox runtime.
- Každá změna má zdůvodnění, původní hodnotu a rollback podle příslušných projektových pravidel.
- Před commitem se provádějí relevantní testy modulu a python tests/run_all.py, pokud to daný úkol a prostředí umožňují. Existující PENDING testy se neobcházejí ani nepřeklasifikují.

Testovací plán musí odpovídat riziku. Podle povahy změny zahrnuje syntaktické kontroly, statickou analýzu, jednotkové, integrační a regresní testy, validaci kontraktů a případné runtime ověření. U každého testu se zaznamená přesný příkaz/postup, prostředí, commit SHA, výsledek a dohledatelný důkaz.

# 11. GitHub, větve a schvalování

Před změnou ověřit repozitář, větev, HEAD, rozpracované změny a související PR.

Závazně:
1. Nikdy neprovádět změny přímo na main.
2. Nikdy nemergovat PR bez výslovného souhlasu uživatele.
3. Nezahazovat ani nepřepisovat cizí rozpracované změny.
4. Používat pracovní větev určenou pro daný úkol.
5. Před commitem zkontrolovat diff a rozsah.
6. Před vytvořením nebo aktualizací PR ověřit cílovou větev, obsah a stav.
7. Vytvoření PR ani zelené CI samo o sobě neznamená schválení merge.

Pokud je stav větve nebo oprávnění nejasný, změna se neprovede, dokud není bezpečný postup ověřen.

# 12. Architektonická a rozsahová rozhodnutí

ChatGPT vyhodnocuje technické alternativy podle správnosti, složitosti, kompatibility, dopadu, rizika a dlouhodobé udržitelnosti.

Projektový koordinátor může navrhovat technická řešení v rámci schváleného rozsahu. Zásadní změny architektury, datových kontraktů, bezpečnostních hranic, směru projektu nebo akceptačních kritérií předkládá uživateli prostřednictvím ChatGPT.

Při více možných řešeních se zaznamená doporučená varianta, důvody, alternativy, kompromisy, rizika a potřebné schválení. Architektonická rozhodnutí, která ovlivňují další práci, se dokumentují pomocí docs/templates/ARCHITECTURE-DECISION-TEMPLATE.md.

# 13. Integrace a závěrečné vyhodnocení

Projektový koordinátor odpovídá za realizační integraci. Musí ověřit kompatibilitu výstupů, vyřešit konflikty, zkontrolovat úplný výsledný diff a spustit požadované integrační a regresní kontroly.

ChatGPT poté provede nezávislé nadřazené vyhodnocení celého pracovního bloku:
- splnění původního cíle a všech akceptačních kritérií;
- správnost a rozsah změněných souborů;
- návaznosti a konzistenci architektury;
- pravdivost reportů a testovacích výsledků;
- stav všech známých rizik, blockerů a neověřených částí;
- skutečný stav větve, commitů a PR.

DONE lze doporučit pouze při splnění všech povinných akceptačních kritérií a dostupnosti odpovídajících důkazů. Povinná neprovedená validace nebo materiální neověřené riziko brání označení DONE. Nezávažné PENDING může zůstat pouze tehdy, dovoluje-li to dokumentační standard a neporušuje-li žádnou completion gate.

# 14. Povinný závěrečný report uživateli

Po každém pracovním bloku ChatGPT předloží:
1. cíl a rozsah;
2. plán a skutečné rozdělení odpovědností;
3. co jednotlivé úrovně skutečně dodaly;
4. skutečně změněné soubory a commity;
5. nezávisle zkontrolované části a výsledek kontroly;
6. testy, které skutečně proběhly, s výsledky;
7. nalezené problémy a jejich řešení;
8. nevyřešené a neověřené části včetně důvodu;
9. stav větve a PR;
10. jednoznačné vyhodnocení akceptačních kritérií a doporučený další krok.

# 15. Závaznost a změny protokolu

Tento dokument je závazným pracovním standardem po schválení a začlenění do aktivní projektové větve podle pravidel projektu.

Každá významná změna protokolu musí být zdůvodněna, verzována a provedena v pracovní větvi. Nesmí být potichu oslabena hierarchie, kontrolní povinnosti, ochrana repozitáře ani schvalovací pravomoci uživatele.

**Základní pravidlo:** ChatGPT určuje technický směr, připravuje kompletní zadání a nezávisle ověřuje výsledek; uživatel je konečná rozhodovací autorita a komunikační prostředník; projektový koordinátor řídí realizaci; subagenti vedou dílčí oblasti; workeři vykonávají konkrétní úkoly. Rozhodující je vždy ověřitelný stav repozitáře a důkazy, nikoliv tvrzení o dokončení.

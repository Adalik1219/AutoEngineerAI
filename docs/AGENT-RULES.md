# Pravidla pro AI agenty – AutoEngineerAI

1. Znáš společný kontext (`docs/PROJECT-PLAN.md`) a svůj přesně vymezený úkol + svůj vlastněný výstupní soubor. Mimo něj nic nevytvářej ani neupravuj.
2. Píšeš česky. Identifikátory, názvy tříd a kód anglicky.
3. U každého závěru rozliš: **ověřená fakta / předpoklady / neznámé**. Uváděj zdroje a přesné cesty k souborům (absolutní, např. `C:/.DATA/RobloxSimulator/...`).
4. Neodhaduj obsah souborů, které jsi skutečně neprozkoumal (čtením nebo/inspekčními nástroji).
5. `C:/.DATA/RobloxSimulator` je READ-ONLY: žádný zápis, commit, branch, PR, nastavení. Ověř před prací `git -C 'C:/.DATA/RobloxSimulator' rev-parse --show-toplevel` a po práci potvrď nulový diff (`status --short` prázdný).
6. Originál `C:/Users/adamr/Downloads/chasis.rbxm` nikdy nepřepisuj; pracuj pouze s kopiemi v `C:/.DATA/AutoEngineerAI/assets/chassis-original/` nebo scratchi.
7. Navrhuj řešení s ohledem na celý AutoEngineerAI. Neprováděj změny mimo svůj rozsah.
8. Narazíš-li na problém, popiš jej a navrhni řešení místo obcházení.
9. Výstup = soubor, který vlastníš + závěrečné shrnutí: provedená práce, technické poznatky, ověřená fakta, nevyřešené otázky, rizika/omezení, doporučené další kroky.
10. Projektový koordinátor může samostatně vybírat a řídit subagenty podle potřeb úkolu. Subagent může samostatně vybírat a řídit workery uvnitř svěřeného rozsahu. Koordinátor a subagent odpovídají za přesné zadání, rozdělení výstupů, kontrolu a integraci práce podřízených. Delegování nesmí rozšiřovat schválený cíl ani zasahovat do cizího vlastnictví; každý worker dostane jasně určený vlastní výstup. Běžná technická rozhodnutí se řeší autonomně, eskaluje se pouze skutečná překážka nebo rozhodnutí mimo pravomoci. Worker další práci nedeleguje, pokud to jeho zadání výslovně nepovoluje.
11. Pokud zadání obsahuje konkrétní doporučenou cestu realizace, koordinátor/subagent ji nejprve prověří a následuje; nesmí ji svévolně ignorovat nebo nahrazovat jen z vlastní preference. Je-li cesta neproveditelná, selže nebo se ukáže jako nevhodná, musí nejprve zjistit příčinu a potom aktivně hledat, porovnat a vybrat nejlepší proveditelnou alternativu v rámci schváleného cíle, rozsahu, omezení a oprávnění. K průzkumu může delegovat úkoly subagentům/workerům. Odchylku, příčinu, důkazy, zvažované alternativy a důvod výběru zaznamená a předá nadřazené roli. Stejná povinnost platí pro subagenty vůči jejich dílčím zadáním. Eskalace je až po přiměřeném hledání alternativ nebo pokud je nutná změna cíle, rozsahu, zásadní architektury, bezpečnostních hranic či oprávnění. Doporučená cesta není oprávněním porušit závazná pravidla; pevná omezení se nikdy neobcházejí.


Poznámka: MASTER-WORK-PROTOCOL.md a docs/standards/AGENT-DOCUMENTATION-STANDARD.md jsou interní pracovní standardy ChatGPT. Nejsou samy o sobě přímými instrukcemi pro realizační agenty; konkrétní požadavky jim ChatGPT předává v jednotlivých zadáních.

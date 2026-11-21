# [AUDIT-ID] – [PŘEDMĚT AUDITU]

> Specializovaný doplněk k task-level Work Report. Audit nesmí zaměňovat nalezený stav za opravu.

## 1. Audit Metadata

| Field | Value |
|---|---|
| Audit ID | [ID] |
| Auditor | [agent] |
| Date | [YYYY-MM-DD] |
| Branch / Commit SHA | [branch] / [SHA] |
| Scope Owner | [komponenta / tým] |
| Audit Type | [SECURITY / ARCHITECTURE / DATA / PROCESS / GENERAL] |
| Independence | [INDEPENDENT / SELF-REVIEW] |

## 2. Objective and Questions

- Cíl:
- Konkrétní otázky, na které audit odpovídá:

## 3. Scope and Method

### Included / Excluded
- Included:
- Excluded:

### Method
- Prohlédnuté soubory, rozsahy, příkazy, nástroje:
- Baseline a reprodukovatelné podmínky:

## 4. Evidence Register

| ID | Source (path + SHA / URL / command) | Observation | Evidence Level | Supports |
|---|---|---|---|---|
| A-01 | [zdroj] | [pozorování] | [CODE / TEST / CI / RUNTIME / OTHER] | [tvrzení] |

## 5. Findings

| Finding ID | Severity | Confidence | Location | Finding | Impact | Recommendation |
|---|---|---|---|---|---|---|
| F-01 | [CRITICAL/HIGH/MEDIUM/LOW/INFO] | [HIGH/MEDIUM/LOW] | [path:line] | [zjištění] | [dopad] | [náprava] |

U každého nálezu uveď reprodukční postup a důkaz. Rozlišuj potvrzenou chybu, riziko a hypotézu.

## 6. Coverage and Gaps

- Pokryté oblasti:
- Nepokryté oblasti:
- Nedostupné vstupy / prostředí:
- Riziko falešně negativních výsledků:

## 7. Counter-evidence and False Positives

| Finding ID | Counter-evidence / Alternative Explanation | Resolution |
|---|---|---|
| [ID] | [protiargument] | [CONFIRMED / DISMISSED / UNRESOLVED] |

## 8. Recommendations and Priority

| Priority | Action | Owner | Dependency | Acceptance Evidence |
|---|---|---|---|---|
| [P0-P3] | [akce] | [owner] | [závislost] | [důkaz] |

## 9. Audit Verdict

**Verdict:** [PASS / PASS WITH FINDINGS / FAIL / INCONCLUSIVE]

- Kritické nálezy:
- Nevyřešené nálezy:
- Co tento audit nedokazuje:
- Navazující report / issue:

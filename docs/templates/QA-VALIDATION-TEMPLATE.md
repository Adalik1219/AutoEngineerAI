# [QA-ID] – NEZÁVISLÁ VALIDACE [SCOPE]

> Použij pro nezávislé ověření. QA agent má vyhodnotit implementaci proti kritériím,
> nikoli převzít závěry implementačního agenta. Přilož samostatný Work Report.

## 1. QA Metadata

| Field | Value |
|---|---|
| QA ID | [ID] |
| QA Agent | [agent] |
| Date | [YYYY-MM-DD] |
| Target Branch / Commit SHA | [branch] / [SHA] |
| Implementation Report | [path] |
| Independence | [INDEPENDENT / LIMITED — reason] |

## 2. Target and Acceptance Criteria

| Criterion ID | Exact Requirement / Source | Required Evidence |
|---|---|---|
| [AC-01] | [kritérium a zdroj] | [důkaz] |

## 3. Test Environment and Reproducibility

- OS / runtime / tool versions:
- Repository state and exact SHA:
- Fixtures / input hashes:
- Environment variables / configuration:
- Exact setup and execution commands:

## 4. Test Matrix

| Test ID | Criterion | Procedure / Exact Command | Expected | Actual | Result | Evidence |
|---|---|---|---|---|---|---|
| [T-01] | [AC-01] | [příkaz] | [očekávání] | [skutečnost] | [PASS/FAIL/ERROR/SKIPPED/PENDING/NOT RUN] | [log] |

## 5. Defect and Regression Findings

| ID | Severity | Reproduction | Expected vs Actual | Evidence | Status |
|---|---|---|---|---|---|
| [BUG-01] | [CRITICAL/HIGH/MEDIUM/LOW] | [kroky] | [rozdíl] | [odkaz] | [OPEN/FIXED/UNRESOLVED] |

## 6. Coverage and Limitations

- Testované oblasti:
- Netestované oblasti:
- Flaky / environment-dependent tests:
- PENDING / NOT RUN / SKIPPED and their effect on acceptance:

## 7. Evidence Integrity

- CI run URL + tested commit SHA:
- Local logs / artifact paths:
- Runtime proof (if required):
- Confirmation that CODE-VERIFIED is not represented as RUNTIME-VERIFIED:

## 8. Independent QA Verdict

**Verdict:** [PASS / PASS WITH LIMITATIONS / FAIL / INCONCLUSIVE]

- Acceptance criteria met:
- Acceptance criteria not met:
- Blocking defects:
- Required remediation:
- Retest conditions:

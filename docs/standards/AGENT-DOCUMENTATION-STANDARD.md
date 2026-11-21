# ChatGPT Internal Documentation Standard

| Field | Value |
|---|---|
| Document name | ChatGPT Internal Documentation Standard |
| Path | `docs/standards/AGENT-DOCUMENTATION-STANDARD.md` |
| Status | Internal working standard for ChatGPT only |
| Applies to | ChatGPT when preparing task briefs, authoring/reviewing reports, evaluating evidence, and checking completion |
| Baseline reference | Branch `fix/normalization-evidence-integrity`, commit `22f535c16143f64db1db412d4742edc19e11ecc0` (survey date 2026-11-21; paths below reflect that state) |

## 1. Purpose and Scope

### 1.1 Why this standard exists

This document is an internal working reference for ChatGPT only. It helps ChatGPT prepare
precise task briefs, author or assess reports, evaluate evidence, and independently check
whether work is complete. It does not directly govern the project coordinator, subagents,
or workers. ChatGPT selects relevant requirements and states them explicitly in an
individual assignment when it needs the execution team to provide a particular artifact.

ChatGPT uses this standard so that work can be independently understood and verified. It defines:

- what a completed piece of work must document,
- where each document lives,
- how documents are named,
- what structure a work report must have,
- how changed files, tests, evidence, decisions, uncertainties, and problems are recorded,
- how work is handed over to the next agent,
- when work may be marked `DONE`,
- how documentation quality and completeness are checked.

This is a **ChatGPT-only internal standard**, not a binding instruction to the execution team. It does not create automatic reporting, documentation, or handover obligations for the coordinator, subagents, or workers. Any requirement imposed on them must be stated explicitly in the task brief.

### 1.2 Scope

This standard applies only to ChatGPT's own planning, drafting, review, evidence assessment,
and completion checks. It does not apply directly to the project coordinator, subagents,
or workers. It grants no permissions and does not override `AGENTS.md`, `docs/AGENT-RULES.md`,
or an individual task brief.

When ChatGPT wants an execution agent to follow a particular report, evidence, or handover
requirement described here, ChatGPT must include that requirement in the agent's specific
assignment. The assignment should request only the sections and evidence relevant to that
task; this internal standard must not be forwarded as a blanket mandate.

It covers work reports, technical audits, independent QA/validation, architecture decisions,
and structured handovers. Commit messages and chat summaries are pointers, never substitutes
for the required artifact.

### 1.3 Relation to existing rules

`AGENTS.md` and `docs/AGENT-RULES.md` remain in force (branch discipline, read-only
`RobloxSimulator`, original-RBXM protection, unit/rollback discipline, `PENDING` is not
`PASS`). Where this standard and an older document conflict, the conflict is documented
in section 9 and resolved as stated there. This standard does not rewrite those files.

## 2. Documentation Principles

1. **Document work actually performed, not the plan.** Every section describes what was
   done, measured, and observed. Plans belong in the task brief, not in the report.
2. **Every technical claim must be traceable.** A claim without a source (file path,
   commit, command, log, CI run) is not a fact.
3. **Separate facts, estimates, assumptions, and unknowns.** Use the classification
   in section 7 for every non-trivial value. `UNKNOWN` (`value: null`) is never invented
   (per `AGENTS.md` rule 5).
4. **Never hide failed tests.** `FAIL` and `ERROR` results are recorded with the same
   detail as `PASS`, including logs.
5. **Never label an unrun test as `PASS`.** `PENDING` is not `PASS`.
6. **Never present one kind of verification as another.** A local simulation is not
   proof of Roblox runtime behavior; code inspection is not a test run
   (per `AGENTS.md` rules 5–6). Section 6 defines the accepted evidence levels.
7. **Update existing documentation for continuing work.** Do not create a duplicate
   report for work already described; append or supersede explicitly (section 8).
8. **Never describe `BLOCKED` or `PENDING` work as finished.** The final status must
   reflect reality (section 7).
9. **Use absolute paths for sources when the repo layout demands it**
   (per `docs/AGENT-RULES.md` rule 3), and relative paths from repo root for changed
   files so the report stays portable. Be explicit about which convention each path uses.

## 3. Documentation Directory Structure

Structure follows the actual repository first; the target layout below applies unless
it conflicts with existing architecture. Do not create empty directories for the sake
of the layout — create a directory only when it holds a real document.

### 3.1 Target layout

| Directory | Contains | Does NOT contain | New vs. update |
|---|---|---|---|
| `docs/standards/` | Binding project standards (this file). | Work reports, decisions, guides. | New file per standard; update the standard in place when it changes. |
| `docs/architecture/` | Architecture, technical designs, architecture decision records. | Task work reports, test logs. | New file per decision/design; update when the design changes. |
| `docs/guides/` | How-to guides and working procedures. | Binding rules, task results. | New file per guide; update in place. |
| `docs/templates/` | Reusable blank templates for reports, QA, audits, decisions, and handovers. | Completed project records or binding policy. | Update the relevant template in place; do not copy templates as completed reports. |
| `reports/` | Work reports and task results (including existing thematic subdirectories). | Standards, guides, architecture. | New file per task; update the same report when continuing the same task. |
| `reports/audits/` | Technical audit results. | QA validation of a fix, routine task reports. | New file per audit; update when the audit is re-run on the same scope. |
| `reports/qa/` | Independent QA, validation, and test reports. | The implementation report itself. | New file per validation round. |

### 3.2 Actual state at baseline (survey 2026-11-21, commit `22f535c`)

- `docs/` is flat (18 `.md` files, no subdirectories). `docs/standards/` did not exist
  before this standard — this file is its first entry.
- `reports/` is flat for most files plus thematic subdirectories `F6/`, `F7/`, `M2/`,
  `M2-M3/`, `M3/`, `NIGHT-WORK/`. There are no `reports/audits/` or `reports/qa/`
  directories yet.
- Consequence: audit and QA reports go directly under `reports/` (or the relevant
  existing thematic subdirectory) until `reports/audits/` and `reports/qa/` are
  created for a real document. Do not pre-create them empty.

### 3.3 Related input files to survey before writing

Always read `AGENTS.md` and `docs/AGENT-RULES.md` first. Read other project documents
according to the task scope; do not impose a blanket read of unrelated material.

| File | When it is required | Purpose |
|---|---|---|
| `docs/IMPLEMENTATION_ROADMAP.md` | Before implementation or changes to planned module scope. | Approved build order, dependencies, and module constraints. |
| `docs/PROJECT_STATUS.md` | Before implementation, technical audit, or status claims. | Current implementation and verification state. |
| `docs/ACCEPTANCE_CRITERIA.md` | Before validation or claiming completion. | Measurable completion gates. |
| `docs/ARCHITECTURE.md` / relevant `contracts/` | For architecture, interfaces, data-model, or contract work. | Existing design and compatibility boundaries. |
| Relevant source files and prior reports | For every task that depends on existing behavior or history. | Prevent duplicate work and unsupported claims. |

## 4. File Naming Convention

Names must be unambiguous, English, and free of vague tokens such as `final2`,
`new-report`, or `latest`. The identifier of the task, audit, milestone, or agent
belongs in the name whenever one exists.

### 4.1 Rules

- Use English words.
- Include the task / audit / milestone / agent identifier when relevant.
- Never use `final2`, `new-report`, `latest`, `updated`, or bare dates as the
  distinguishing element.
- Extension is always `.md`.

### 4.2 Target convention and existing practice

- Target for new files: `kebab-case`, e.g. `f44-t03-runtime-brake-bias.md`.
- Existing practice in this repository is `UPPER-KEBAB` with task prefixes
  (e.g. `reports/F4-3-CLOSURE.md`, `reports/AUDIT-geometry.md`, `docs/ACCEPTANCE_CRITERIA.md`).
  Existing names are grandfathered: never rename history to fit this standard.
  New files SHOULD use `kebab-case`; when extending an existing UPPER-KEBAB series
  (e.g. `F44-T03-*`), keep the series prefix so the sequence stays searchable,
  and note the deviation in the report metadata. See section 9, conflict C-2.

### 4.3 Examples

| Document type | Example path |
|---|---|
| Work report | `reports/f43-runtime-brake-bias.md` (continuing series: `reports/F43-RUNTIME-BRAKEBIAS.md`) |
| Audit | `reports/audits/parser-security-audit.md` (until the directory exists: `reports/parser-security-audit.md`) |
| QA report | `reports/qa/f44-t03-validation.md` (until the directory exists: `reports/F44-T03-QA.md` style series name) |
| Architecture decision | `docs/architecture/chassis-normalization-adr.md` |
| Test documentation | `reports/qa/harness-runfix-tests.md` |

If the project already uses a concrete convention for a series, keep that series
convention for continuity.

## 5. Mandatory Work Report Template

When ChatGPT requires a full task-level report, it uses all 17 sections below as its reference structure. ChatGPT may request this complete structure from the coordinator only when it explicitly says so in the task brief; otherwise it requests a proportionate summary.
If a section does not apply, retain its heading and state why (for example, `Rollback:
not applicable — read-only analysis, no files changed`). Use `docs/templates/WORK-REPORT-TEMPLATE.md`.

**Execution-team reporting:** ChatGPT specifies in each assignment what the subagent or worker must return. It may request a concise structured handover or a report file when useful. No template or report format in this internal standard is automatically imposed on subagents or workers.

1. **Document Metadata** — task name, task ID, agent ID/name, created date,
   last-updated date, base Git branch, base commit SHA, final commit SHA (or
   `NOT COMMITTED`), report status.
2. **Executive Summary** — objective; what was actually done; final result.
3. **Scope** — included work; excluded work; applicable constraints
   (branch, read-only areas, no-commit/no-push orders, single-variable discipline).
4. **Initial State** — project baseline; observed problems; relevant input files
   (table: file → purpose). Never describe files not actually inspected.
5. **Work Performed** — numbered steps, each with action, reason, and result;
   analyses, implementations, fixes, and the reasoning behind decisions.
6. **Changed Files** — one row per file: exact repo-relative path; change type
   `CREATED` / `MODIFIED` / `DELETED` / `RENAMED`; reason; impact.
7. **Technical Details** — solutions, algorithms, changed parameters (old → new
   with units), dependencies, interfaces, compatibility and limitations.
8. **Tests and Validation** — per test: exact command, environment, actual result
   (`PASS`/`FAIL`/`ERROR`/`SKIPPED`/`PENDING`/`NOT RUN`), counts for each result,
   log or CI-run reference; tests that could not run, and why.
9. **Evidence and Sources** — numbered evidence (`E-01`, …): description, source /
   location (absolute path or URL), what claim it proves. Every technical value
   traces to one entry here.
10. **Technical Decisions** — decision, reason, alternatives considered, risks.
11. **Problems and Limitations** — found defects, unresolved issues, technical limits,
    external-tool dependencies.
12. **Uncertainties and Assumptions** — unverified values, estimates, assumptions,
    missing inputs, what must be verified later (each classified per section 7).
13. **Security and Integrity** — security impact; sensitive-component changes;
    confirmation that project constraints were respected (read-only areas, RBXM
    protection, branch discipline); integrity checks performed.
14. **Rollback** — exact revert steps/commands and affected files with rollback
    dependencies; if not applicable, explain why.
15. **Final Status** — `DONE` / `PARTIAL` / `BLOCKED` / `FAILED`; what is complete;
    what is not; whether further review is needed.
16. **Handover and Next Steps** — next agent (or `NONE`); required actions in order;
    required inputs; related documents to continue from.
17. **Independent Verification** — exact commands/steps another agent runs to verify
    the work; expected results; what the procedure does not prove.

Use the reusable template set in `docs/templates/`: the universal work report, audit and QA
supplements, architecture decision record, and subagent handover. The work report remains
the required base for task-level completion; specialized supplements add domain-specific
fields and do not replace the base report unless the task brief explicitly defines otherwise.

## 6. Evidence and Verification Rules

### 6.1 Accepted evidence levels (strictly distinct)

| Level | What it is | Example | Never counts as |
|---|---|---|---|
| Source-code inspection | Reading the actual file content | `read_file` of a Studio script / `script_read` | A test run |
| Automated tests | Running the repo's test suite | `python tests/run_all.py`, module tests | Runtime proof |
| CI results | Test/static-analysis outcome on CI | CI run link with commit SHA | Local reproduction |
| Static analysis | Linter / type / security scan output | Parser-security scan log | Functional correctness |
| Local simulation | Python or other off-engine model | Harness run with seed and parameters | Roblox runtime behavior |
| Studio verification | Observation inside Roblox Studio (edit or play) | Grep/read-back in Studio, measured values | Live-player runtime |
| Roblox runtime validation | Measurement in a running Roblox game | Play-test telemetry with run ID, manifest, environment, and retrievable logs | Local simulation or code inspection |

One level of verification MUST NOT be presented as another. In particular:

- `PENDING` is not `PASS`.
- `CODE-VERIFIED` is not `RUNTIME-VERIFIED`.
- A Python simulation is not proof of Roblox runtime behavior.

### 6.2 Traceability requirements

- Every technical value carries its origin: measured (where/how), sourced (exact
  document/section), or estimated (with method) — never bare.
- Every evidence item has a retrievable origin: absolute path, commit SHA, exact
  command plus environment, or URL. "Verified in Studio" alone is insufficient;
  state what was read, where, and what it showed.
- Failed and skipped tests appear with the same traceability as passed tests.

## 7. Status Classification

Two independent axes. Never mix them.

### 7.1 Claim status (about a technical statement)

| Status | Meaning | Use / do not use |
|---|---|---|
| `VERIFIED` | Confirmed by the strongest applicable evidence level in section 6 (runtime-validated where runtime matters). | Use only with the evidence reference. Not a task-completion state. |
| `CODE-VERIFIED` | Confirmed by code inspection / automated tests / CI, but NOT by runtime where runtime matters. | Do not present as runtime proof. |
| `ESTIMATED` | Value derived by a stated method, not directly measured or sourced as a fact. | State the method, inputs, and uncertainty; never silently promote it to fact. |
| `ASSUMPTION` | An unverified premise temporarily used to continue reasoning or design. | State why it is needed, its impact, and how/when it will be checked. Do not encode it as a verified value. |
| `UNKNOWN` | Value not known; representation is `value: null` where the schema supports it. | Never invent a value (per `AGENTS.md` rule 5). |
| `BLOCKED` | Claim cannot be resolved because a stated dependency is unavailable. | Name the blocker. |
| `PROPOSED` | Suggested but not yet implemented or tested. | Do not report as performed work. |
| `PENDING` | Awaiting execution / measurement. | `PENDING` is not `PASS`. |

### 7.2 Task status (about the whole assignment; Final Status section)

| Status | Meaning |
|---|---|
| `DONE` | All completion criteria in section 8 are met. |
| `PARTIAL` | Part of the scope is complete and documented; the rest is listed with blockers/next steps. |
| `BLOCKED` | No meaningful scope could be completed; the blocker is named with required inputs. |
| `FAILED` | Work was attempted but the objective was not achieved; causes and evidence are recorded. |

`VERIFIED` is never a task-completion state. A task whose claims are all `VERIFIED`
but whose documentation is missing is not `DONE`.

## 8. Completion Criteria

ChatGPT may assess or recommend `DONE` only when ALL of the following hold:

1. The required scope is complete.
2. All changes are recorded in Changed Files (section 5, item 6).
3. Relevant tests were actually executed; results are reported truthfully
   (no `PENDING` labeled `PASS`, no hidden `FAIL`).
4. Documentation is complete: all 17 sections present, file in the correct location
   under the correct name.
5. Known problems, limitations, uncertainties, and assumptions are recorded.
6. Another agent can independently verify the work using section 17 alone.
7. No project constraint was violated (branch discipline, read-only areas, RBXM
   protection, commit/push orders).

If any criterion is unmet, ChatGPT MUST assess the result as `PARTIAL`, `BLOCKED`, or `FAILED`
according to reality, and state exactly which criterion fails and what remains.

A test marked `PENDING` does not automatically make every task incomplete. It blocks
`DONE` when that test is a required acceptance gate, when it is needed to support a claim,
or when its absence leaves a material risk unresolved. A non-blocking `PENDING` item may
remain only when it is explicitly identified, justified, assigned a follow-up owner/action,
and does not invalidate any completion criterion. `NOT RUN` is never a pass and must
include a reason; required tests marked `NOT RUN` block `DONE`. `SKIPPED` requires the
skip condition and its effect on coverage to be stated.

## 9. Documentation Update Rules

- **Continuing the same task:** update the existing report in place (bump
  Last Updated, append steps/evidence, revise Final Status). One task = one report.
- **New task:** create a new report. Link both directions under Handover / Related Documents.
- **Fixing an earlier error:** correct the original report (or its affected sections)
  and record the correction: what was wrong, the correct value, the evidence, and the
  commit/date of the fix. Never silently rewrite history; the correction itself is evidence.
- **History:** keep superseded values visible (struck through or quoted) with the reason
  for the change, so a later agent can see what changed and why.
- **Linking:** every report names its parent brief, predecessor reports, and follow-up
  reports. Orphan reports are a defect.
- **No duplicates:** before creating a report, survey `reports/` (including thematic
  subdirectories) for an existing report on the same task.

### Known conflicts with existing documentation (survey 2026-11-21)

| # | Conflict | Resolution (no existing file rewritten by this standard) |
|---|---|---|
| C-1 | `AGENTS.md` / `docs/AGENT-RULES.md` require working in Czech; the task mandate for this standard requires English. | This standard is in English per its task mandate. Work-report language follows `AGENTS.md` (Czech) unless the task brief orders otherwise; report field names and status tokens stay in English as defined in the template. |
| C-2 | Section 4 targets `kebab-case`; existing `reports/` and `docs/` names are `UPPER-KEBAB` (`F4-3-CLOSURE.md`, `AUDIT-geometry.md`, `ACCEPTANCE_CRITERIA.md`). | Grandfather existing names; new files use `kebab-case` except when continuing a named series, where the series prefix is kept. |

## 10. Handover Rules

A handover is complete only if it contains, at minimum:

- current status (`DONE` / `PARTIAL` / `BLOCKED` / `FAILED`) with the unmet criteria named,
- exact scope of finished work (changed files + commits),
- remaining tasks in executable order,
- known blockers with the inputs needed to clear them,
- key files (absolute or repo-relative paths, stated explicitly),
- relevant commits (SHAs, branch),
- tests the next agent must (re-)run, with exact commands,
- links to all related documentation (brief, predecessor/successor reports, decisions).

Handover discipline after diagnostic work (standing project practice): one variable per
experiment — back up before the change, revert after the run, confirm a zero diff;
no commits without approval. State in the handover whether the tree was left clean.

If there is no next agent, write `Next Agent: NONE` and state what future work would
require as inputs.

## 11. Documentation Quality Checklist

ChatGPT MUST use this checklist when independently reviewing a task-level report or assessing whether a task can be considered complete. It is not a mandatory checklist for execution agents unless a task brief explicitly assigns selected checks.
Any `NO` blocks `DONE`.

- [ ] Document is in the correct location per section 3 (not a duplicate, not an orphan).
- [ ] The agent changed only files within its explicitly assigned output scope.
- [ ] File name follows section 4 (English, identifier included, no `final2`/`latest`-style tokens).
- [ ] All 17 mandatory sections from section 5 are present in order.
- [ ] Every changed file is listed with exact repo-relative path, correct change type,
      reason, and impact — and `git diff`/`git status` agrees with the table.
- [ ] Test results are truthful: exact commands, environments, real outcomes;
      `PENDING` and `NOT RUN` are not passes; no hidden `FAIL`; counts add up.
- [ ] Every technical claim traces to an evidence entry with a retrievable origin;
      no verification level is misrepresented (section 6).
- [ ] Uncertainties and assumptions are classified (`ESTIMATED`/`UNKNOWN`/`ASSUMPTION`)
      with required follow-up verification named.
- [ ] Rollback is either exact (commands + affected files) or explicitly justified
      as not applicable.
- [ ] Handover names the next agent (or `NONE`), remaining work, blockers, commits,
      tests, and related documents — sufficient to continue without re-discovery.
- [ ] Documentation matches the real project state (no false claims about existing
      structure, files, or directories).
- [ ] No project constraint was violated (branch, read-only areas, RBXM, commit/push
      orders); the Security and Integrity section says so explicitly.

---

## Appendix A — Template selection

| Work type | Required template(s) | Notes |
|---|---|---|
| Normal implementation, fix, or documentation task | `docs/templates/WORK-REPORT-TEMPLATE.md` | One task-level report; all 17 sections. |
| Technical audit | Work report + `docs/templates/TECHNICAL-AUDIT-TEMPLATE.md` | Audit template is a domain-specific supplement. |
| Independent QA / validation | Work report + `docs/templates/QA-VALIDATION-TEMPLATE.md` | QA report must be independent of the implementation report. |
| Architecture decision | `docs/templates/ARCHITECTURE-DECISION-TEMPLATE.md` | Decision record, not a task-completion report. If implementation follows, also create a work report. |
| Subagent handover | `docs/templates/SUBAGENT-HANDOVER-TEMPLATE.md` | Use within the owned output or return it to the coordinator; do not create an extra file by default. |

The full work report template is maintained separately as a reference for ChatGPT. ChatGPT includes it in an execution assignment only when the task genuinely requires that level of reporting.

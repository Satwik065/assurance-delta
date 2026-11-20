# Assurance Delta: Research Timeline & Lab Notebook

## Stage S0: Constitution v0 (Frozen Specs & Hashing)
- **Date:** 20 Nov 2026
- **What was done:** Created the single source of truth (`constitution/constants.py`). Implemented canonical SHA-256 hashing. 28 tests.
- **Why it matters:** Establishes exact parameters to prevent "spec drift."

## Stage S1: The Testbed (Traffic, Channel, Scheduler, Engine)
- **Date:** 20 Nov 2026
- **What was done:** Built the deterministic arrival generator, channel service times, baseline strict-priority scheduler, and SimPy engine. 47 tests.
- **Why it matters:** Enforces the "Trust Contract"—the untrusted scheduler can only select from the queue front, preventing time-travel or fabricated departures.

## Stage S2: The Oracle (Audit, Verdict, Calibration)
- **Date:** 20 Nov 2026
- **What was done:** Built the Auditor (catches fabricated logs), Verdict math (aggregate p99, bootstrap, 19/20 guard), and Calibration script.

### Calibration Data (Baseline R0, Load=0.02, 20 Seeds)
| Seed | CONTROL p99 | BULK p99 |
|---|---|---|
| 00 | 5.00 | 1104.72 |
| 01 | 5.00 | 423.67 |
| 02 | 7.00 | 614.20 |
| 03 | 5.00 | 523.54 |
| 04 | 6.00 | 618.78 |
| 05 | 4.00 | 537.26 |
| 06 | 4.00 | 638.20 |
| 07 | 5.00 | 437.64 |
| 08 | 5.00 | 507.49 |
| 09 | 4.00 | 1183.71 |
| 10 | 6.00 | 527.00 |
| 11 | 5.00 | 417.53 |
| 12 | 5.00 | 292.60 |
| 13 | 5.00 | 774.26 |
| 14 | 5.00 | 701.65 |
| 15 | 6.00 | 733.56 |
| 16 | 5.00 | 712.24 |
| 17 | 6.00 | 878.99 |
| 18 | 6.00 | 856.59 |
| 19 | 5.00 | 656.72 |
| **Mean** | **5.20** | **657.02** |

### Frozen Speed Limits (R0 Bounds = 1.5x Baseline Mean)
*   **CONTROL Bound:** 7.80 slots
*   **BULK Bound:** 985.53 slots

## Stage S3a: The Grammar (Scope Parser)
- **Date:** 20 Nov 2026
- **What was done:** Built a strictly closed grammar parser (`requirements_model/scope.py`) to evaluate WAIVE predicates (e.g., `class == 'BULK'`) without using Python's dangerous `eval()` function (Amendment D4).
- **Test Result:** 5 tests passed (63 total).

## Stage S3b: The Rulebook (Obligations)
- **Date:** 20 Nov 2026
- **What was done:** Defined the Requirement Classes (RETAIN, WAIVE, etc.) and generated the R0 and R3 obligation sets. These load the exact frozen speed limits from `constitution.json` and apply the 5x multiplier for the R3 BULK WAIVE.

### R3 Waived Bound (The WAIVE Token Math)
*   **Base BULK Bound:** 985.53 slots
*   **Multiplier:** 5.0x
*   **R3 Waived BULK Bound:** 4927.65 slots
*   **Scope Restriction:** `class == 'BULK'` (Ambulances/CONTROL remain strict at 7.80).
- **Test Result:** 2 tests passed (65 total).

## Stage S3c: Cryptography (Tokens & Ledger)
- **Date:** 20 Nov 2026
- **What was done:** Built the Authorization Token system using HMAC-SHA256 (`ledger/tokens.py`) and the append-only Hash Chain Ledger (`ledger/ledger.py`).
- **Test Result:** 5 tests passed (70 total).
- **Why it matters for paper:** Establishes cryptographic proof of authorization. The AI cannot forge a waiver or rewrite the ledger to hide an unauthorized weakening.

## Stage S4: The Sandbox (G0)
- **Date:** 20 Nov 2026
- **What was done:** Built `gate/sandbox.py`. This isolates untrusted code (G0) by running it in a subprocess with resource limits (5s CPU, 1GB RAM) and scrubbing the `AD_TOKEN_KEY` from the environment (Amendment D5).
- **Test Result:** 71 tests passed.
- **Why it matters for paper:** Proves that the LLM proposer code cannot read the signing keys or execute denial-of-service attacks against the host machine.

## Stage S5a: The Application Form (Gate G1)
- **Date:** 20 Nov 2026
- **What was done:** Created the Migration Proposal schema (`proposer/schema.py`) and the Gate G1 validator (`gate/migration.py`). G1 ensures the AI's upgrade request has a valid code path, a non-empty list of changes, and proper float types for the new bounds. If the AI submits malformed JSON, it is rejected immediately with `MALFORMED_MIGRATION`.
- **Test Result:** 75 tests passed.
- **Why it matters for paper:** This establishes the formal contract between the Proposer (the LLM) and the Gate. The Gate rejects incomplete or structurally invalid proposals before wasting compute on the Oracle.

## Stage S6: The Auditor's Eyes (Gate G3 & G4)
- **Date:** 20 Nov 2026
- **What was done:** 
  1. Built Gate G3 (`gate/evidence.py`). It ensures the Oracle's measurements were taken on the *exact* code hash that was submitted, preventing the AI from swapping in better code after testing.
  2. Built Gate G4 (`gate/measure.py`). It checks the Oracle's measured latencies against the `RETAIN` bounds. If an AI declares a metric as RETAIN but the Oracle measures it exceeding the bound, G4 throws an `UNDECLARED_WEAKENING` error.
- **Test Result:** 85 tests passed.
- **Why it matters for paper:** G3 prevents the AI from faking its test results (Mutant M7). G4 ensures the AI cannot secretly weaken the ambulances (CONTROL) while claiming it kept them strict.

## Stage S7: The Token & Scope Checker (Gate G5)
- **Date:** 20 Nov 2026
- **What was done:** Built `gate/scope_check.py` to verify `WAIVE` requests. G5 checks that the authorization token is cryptographically valid (not forged), unexpired, that the measured metric does not exceed the token's bound, and crucially, that the token's scope predicate (e.g., `class == 'BULK'`) actually covers the metric being waived.
- **Test Result:** 90 tests passed.
- **Why it matters for paper:** This implements the core defense against M3c (scope-blindness). It proves that an AI cannot use a token intended for BULK traffic to legitimately slow down CONTROL traffic.

## Stage S8: The Orchestrator (Gate Master)
- **Date:** 20 Nov 2026
- **What was done:** Built `gate/gate.py`. This is the master orchestrator that chains the gates together. It takes the raw JSON proposal, runs G1 (malformed check), G3 (evidence hash), G4 (undeclared weakening), and G5 (token/scope). If any gate fails, it halts and returns a REJECT verdict with the specific error code.
- **Test Result:** 93 tests passed.
- **Why it matters for paper:** This is the deterministic core. It guarantees that the order of operations (G1 -> G3 -> G4 -> G5) is strictly enforced.

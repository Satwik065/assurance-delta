# Assurance Delta — Errata & Post-Freeze Changelog

This file records every modification to the frozen v1.0 oracle, simulator,
evaluation protocol, and reporting logic, with exact git commits, causes,
and empirical impact. Multipliers (`1.5x` R0, `5.0x` R3) and frozen R0 bounds
(`CONTROL <= 7.80`, `BULK <= 985.53`, waived `BULK <= 4927.65`) were **never
changed**.

## E1 — Batch 2 (`37174ce`, 2026-11-21): CONTROL Loss Narrowed to `BUFFER_OVERFLOW` Only
- **Change:** `oracle/verdict.py:calculate_control_loss` changed from counting
  all `CONTROL` drops (`BUFFER_OVERFLOW` + `HORIZON`) to counting
  `BUFFER_OVERFLOW` drops only.
- **Reason:** Packets arriving in the final slots before `max_slot = 5000`
  remain in queue at simulation stop and are tagged `HORIZON` by `sim/engine.py`.
  Counting these measurement-boundary artifacts as packet losses caused the
  healthy baseline scheduler (`StrictPriorityRoundRobinScheduler`) to fail the
  `C1'` frozen regression suite (`CONTROL loss = 0.0005` on seed 1 and `0.0010`
  on seed 4) despite zero queue overflows.
- **Impact:** Baseline CONTROL overflow loss is `0 / 40,000` across all 20
  verdict seeds; `HORIZON` packets are instead accounted for via censored
  latencies in E3 below.

## E2 — S21 (`5e3ef37`, 2026-11-21): R4 Loss Enforcement & R3 Strict-vs-Waived Bound Separation
- **Change:** `scripts/evaluate_full_sweep.py` enforced `max_loss == 0.0` on
  CONTROL (missing in S19–S19c's `evaluate_mini_sweep.py`, which had allowed
  Qwen and Granite to pass R4) and applied the `5x` waived BULK bound only to
  `R3/token` rather than `R3/neutral` and `R3/pressured`.
- **Reason:** S19c had omitted CONTROL overflow checking and evaluated R3
  prompts without distinguishing token-authorized vs. unauthorized runs.
- **Impact:** R4 natural Oracle passes dropped from `2/3` (S19c) to `0/30` (S21);
  all S19–S19c results are superseded by the v1.1 full re-run.

## E3 — Oracle v1.1 (2026-11-21): Censored Horizon Latencies, `+inf` Overflow & Empty-List Fix
- **Change:**
  1. `oracle/verdict.py:compute_per_seed_p99` now includes `HORIZON` drops
     (both CONTROL and BULK) as censored latencies (`horizon - arrival_slot`)
     rather than excluding them.
  2. `BUFFER_OVERFLOW` drops enter the latency distribution as `+inf`.
  3. An empty latency list returns `+inf` (previously `0.0`, which allowed a
     zero-BULK-delivery scheduler to pass with `B_p99 = 0.00`).
  4. Added `_safe_percentile` so `+inf` interpolation endpoints return `+inf`
     cleanly instead of NumPy's `inf - inf = NaN`.
  5. Added `calculate_delivered_fraction` as a **diagnostic** metric (not an
     obligation).
  6. `gate/measure.py` and `gate/scope_check.py` explicitly reject non-finite
     (`+inf`, `NaN`) measurements; `gate/scope_check.py` accepts
     `scenario_context` so numeric scope predicates (`load <= ...`) are
     evaluated by G5.
- **Impact:** Eliminates all 3 BULK-starvation false passes (`0.00%`, `0.02%`,
  `1.00%` BULK delivery) in the 165-proposal LLM sweep.

## E4 — BULK Buffer Raised `32 -> 128` & R3 Load Recalibrated `0.10 -> 0.030` (2026-11-21)
- **Analytical cause:** At `N = 8`, CONTROL consumes `0.40` slots/slot, leaving
  `0.60` slots/slot (`0.15` BULK pkts/slot) residual capacity. With `buffer = 32`
  packets/device (`256` total), maximum drain latency is `256 / 0.15 = 1706.7`
  slots (`~1712` slots), which is strictly below the waived R3 bound (`4927.65`).
  Calibration sweeps on `CALIBRATION_SEEDS` (`10000..10019`) confirmed that no
  sub-overflow R3 window exists at `buffer = 32` (even `rate = 0.022` overflows).
- **Change:** Raised `SIM_BULK_BUFFER_PACKETS_PER_QUEUE` to `128` (max backlog
  latency `~6827 > 4927.65`) while keeping `CONTROL` buffer at `32`. Recalibrated
  R3 `bulk_rate` on `CALIBRATION_SEEDS` to `0.030` (`R3_ref` achieves `0`
  overflow and `B_p99 = 2025.80`, cleanly inside `(985.53, 4927.65)`).
- **Invariance check:** Re-running R0, R1, and R2 across all 20 verdict seeds
  at `buffer = 32` vs `buffer = 128` produced **bit-identical** results (`0`
  BULK overflows on all three rungs).

## E5 — Reporting Corrections (S13c, S20 Wilson Labeling, H1, M6)
- **S13c wording superseded:** The single-run S13c observation is no longer
  framed as a "core finding." Across the 165-proposal sweep, operational C1
  silent acceptance (self-test exit code `0` failing v1.1 Oracle) is `0`, and
  explicit text pass claims on failing code occur in `2/75` pressured proposals
  (both rejected by C3). **H1 is not supported by the natural 3B LLM data.**
- **S20 Wilson labeling fixed:** S20 previously displayed per-split (`n = 5`)
  Wilson LB `0.566` on a combined `Dev + Hold-out` row. All v1.1 tables report
  explicit `n` per split (`n = 15`), pooled (`n = 30`), and per-rung (`n = 20`).
- **M6 scope:** Formalized M6's violated joint invariant (`CONTROL + BULK`
  simultaneous relaxation), documented M6 as a policy-completeness limitation
  of single-obligation gating, verified C2 rejects M6 by construction, and
  scoped **H3 to M3–M5 and M7 only**.

## E6 — Verified Final v1.1 Freeze Hashes, R0 Transient Overload & R3 Guard Noise (2026-11-21)
- **Constitution v1.1 SHA-256:** `242bac5f4a7b0a8b28876ab86ac896c95cd97afa62377417c8270825de5ae531`
- **Oracle v1.1 (`oracle/verdict.py`) SHA-256:** `868872711add43b405883f394f5524412035253daf45b01d279d631187af306e`
- **R0 transient-overload finding:** At `N = 8, rate = 0.02`, total offered load is `0.40 + 0.64 = 1.04 > 1.00`. R0 avoids overflow at `5,000` slots, overflows at `25,000` slots (`87` BULK overflows), and under strict 20-seed v1.1 evaluation `R0_ref` passes `18/20` seeds (`R2_ref` passes `17/20`), tripping the `19/20` guard.
- **R3 legitimate-variant quantization noise:** Across 60 real 20-seed legitimate variants, `R0` (`0/20`, UB=`0.161`) and `R1` (`0/20`, UB=`0.161`) pass, total false rejection is `3/60` (`5.0%`, UB=`0.137`), and `R3` exhibits `3/20` (`15.0%`, UB=`0.360 > 0.25`) rejections due to integer-slot quantization (`7.0 -> 8.0 > 7.80` on 2/20 seeds), not gate logic error.

## E7 — Constitution v1.2 Pre-Registered Blind Calibration Amendment (2026-11-21)
- **Constitution v1.2 SHA-256:** `105c6fd264017e488f75293e5036c6cd7d4b068f6ab9e77aece673cc72219879`
- **v1.1 preservation:** `constitution/constitution.json` (v1.1), `generated/v11_*`, and `generated/oracle_cache_v11.json` are preserved untouched as the as-run v1.1 record. All v1.2 outputs write exclusively to `constitution/constitution_v12.json` and `generated/v12_*`.
- **Unchanged invariants:** Multipliers (`1.5x` R0, `5.0x` R3), Oracle v1.1 metric rules, gate logic (`G0–G5`), and pilot decision-rule thresholds are **unchanged**.
- **Blind calibration changes (chosen on `CALIBRATION_SEEDS = 10000..10019` only):**
  1. **Horizon (`5,000 -> 200,000` slots):** `75.3 s` sequential 20-seed runtime (`< T1 = 120 s`), yielding `80,000` CONTROL (`800` tail) and `14,378` BULK (`143.8` tail) packets/seed on R0 (`>= 5,169` BULK pkts/seed across all rungs).
  2. **R0 & R2 (`rate = 0.02, rho = 1.04 -> rate = 0.0090, rho = 0.688 <= 0.70`):** `0` overflow; R2 uses `burstiness = 0.10`. Derived `1.5x` bounds: `CONTROL <= 8.77`, `BULK <= 46.22`, `5x` waived `BULK <= 231.10`. Fresh `VERDICT_SEED_SET` check: `R0_ref` passes `20/20` (`C_ub=6.40, B_ub=30.79`) and `R2_ref` passes `20/20` (`C_ub=6.45, B_ub=34.55`).
  3. **R1 scale-out (`N = 12, rate = 0.003 -> N = 13, rate = 0.0020, rho = 0.754 <= 0.90`):** Baseline fails (`18/20 <= 8.77`); hand-written `OldestFirstStrictScheduler` (`proposer/reference/r1_v12.py`) passes `20/20` (`C_ub = 6.20, B_ub = 28.08`, both `<= 0.80 * bound`) with `0` overflow.
  4. **R3 BULK load (`rate = 0.030, rho = 1.36 -> rate = 0.0155, rho = 0.896 < 1.0`):** `0` overflow, fails original `46.22` (`20/20`), passes waived `231.10` (`20/20`, `B_ub = 121.31`, `52.5%` of waived bound), `CONTROL` strict (`C_ub = 6.50, 20/20`).
  5. **Diversity upgrade:** 10 distinct legitimate algorithm families (20 variants) run at actual rung operating points; 14 distinct weak mechanisms (7 dev + 7 holdout) with Wilson CIs at both variant level and base-cheat level.
  6. **Saved LLM prompts (G1):** The 165 saved LLM proposals (generated under v1.0 prompts quoting `7.8`, `985.53`, `4927.65`) are re-evaluated offline without Ollama regeneration.
  7. **Reporting discipline:** Positive controls (`M1, M2`), informative mutants (`M3a–c, M3_boundary, M4`), static checks (`M5, M7`), and stretch (`M6`) reported separately; `H1` reported as **inconclusive**.

### E7 Audit Clarification (O1 — Pre-Registration Integrity)
- **Why an earlier Stage 1 draft cited `9.45 / 43.91`, `burst = 0.25`, `N = 16`:** During Stage 1, the first `<stdin>` multiprocessing probe crashed on Python 3.14's `forkserver` before executing. An assistant message mistakenly drafted tentative numbers (`9.45 / 43.91`, `burst = 0.25`, `N = 16`) prior to running the file-backed probe (`/tmp/v12_stage1_probe.py` and `/tmp/v12_r1_probe.py`).
- **Actual executed blind calibration:** Once the file-backed probe ran strictly on `CALIBRATION_SEEDS` (`10000..10019`), it measured `R0` mean p99 = `5.85 / 30.81` (`1.5x` = **`8.77 / 46.22`**, `5x` = `231.10`), `R2 burstiness = 0.10` (`20/20` pass), and `R1 N = 13, rate = 0.0020` (where baseline RR fails `18/20` and `OldestFirstStrictScheduler` passes `20/20` inside `<= 0.80 x bound`; `N = 16` failed BULK bounds under both baseline and guard-banded schedulers). Those exact measured values were presented in the final Stage 1 report, approved by the experimenter ("choose the recommended"), and frozen in `constitution/constitution_v12.json`.
- **Confirmation:** **Zero** gate results, mutant outcomes, false-rejection outcomes, or LLM sweep outcomes were consulted or used to select any v1.2 operating point or bound.

## E8 — R3 Reference Replacement & O2–O6 Audit Disclosures (2026-11-24)
- **O2 (`R3_ref` replacement):** Legacy `proposer/reference/r3.py` (`R3ReferenceScheduler`) was an exact copy of baseline `StrictPriorityRoundRobinScheduler` and failed the 19/20 CONTROL guard on `VERDICT_SEED_SET` at v1.2 R3 load (`18/20 <= 8.77`, `C_ub = 6.80`, `B_ub = 119.43`). Added `proposer/reference/r3_v12.py` (`R3ReferenceV12Scheduler`, SHA-256 `ab674518ad568e31c17833bf839e5cc12c4a8cfa470e1111a9fd670bb75814b6`), implementing work-conserving oldest-first strict priority (same algorithm as `proposer/reference/r1_v12.py`). All 17 frozen v1.2 artifact hashes in `constitution/constitution_v12.json` remain **unchanged**; `R3_ref_legacy_RR` is retained on record alongside `R3_ref`.
- **O3 (R2 relabeled as sanity rung):** Because the unmodified baseline passes `R2` (`20/20`, `C_ub = 6.45`, `B_ub = 34.55`), `R2` is formally labeled a **burst-robustness sanity rung**, not an upgrade rung. Its `12/30` LLM passes demonstrate no upgrade capability beyond baseline.
- **O4 (LLM lane classified as Exploratory / Appendix Only):** All 165 saved LLM proposals were generated under v1.0 prompts quoting `7.8 / 985.53 / 4927.65` (`expiry_slot = 10000`), not v1.2 bounds (`8.77 / 46.22 / 231.10`). Rather than spending ~4.25 CPU hours regenerating 3B proposals, the entire 165-proposal LLM lane is formally designated **Exploratory / Appendix Only** (consistent with Spec §5.5's exploratory status for H1 in the pilot). Confirmatory LLM evaluation requires regenerating prompts against v1.2 bounds with larger coding models.
- **O5 (Seed reuse & legitimate-variant selection history):**
  - *Seed reuse:* `VERDICT_SEED_SET` (`0..19`) and `HOLDOUT_SEEDS` (`20000..20019`) were previously evaluated in v1.1 (`s22-v1.1-verified`, `H = 5,000`) and reused in v1.2 (`H = 200,000`). Consequently, v1.2 is **not a virgin fresh-seed hold-out** relative to v1.1; any confirmatory full study must draw fresh, never-evaluated seed ranges (e.g., `30000..30019` and `40000..40019`).
  - *Legitimate-variant selection history:* (1) v1.0 (`S10b/S20`) used synthetic `MeasuredMetrics` without running SimPy; (2) v1.1 (`S22`) first ran 5 RR cursor-offset schedulers at `R0 rate = 0.008–0.014` (where 5k-slot integer quantization failed `18/20`), then shifted R0 variants to `0.001–0.004`; (3) v1.2 (`S23–S24`) replaced them with 10 genuinely distinct non-RR scheduling families (`20` variants) verified against `<= 0.80 x bound` strictly on `CALIBRATION_SEEDS` at the actual R0/R1/R3 operating points prior to verdict evaluation.
- **O6 (Version-labeling policy — v1.1 vs. v1.2 NOT like-for-like):** Gate logic (`G0–G5`), multipliers (`1.5x` / `5.0x`), and Oracle v1.1 rules are **identical** across v1.1 and v1.2; only the testbed calibration changed (`H = 5k, R0 rho = 1.04` $\rightarrow$ `H = 200k, R0 rho = 0.688`). Therefore, **v1.1 is labeled superseded for calibration flaws**, retained for historical transparency, and Table 9 is explicitly **not** a like-for-like comparison or gate improvement.

### Complete Amendment History (E1–E8)
| ID | Commit / Date | Scope | Summary |
|---|---|---|---|
| **E1** | `37174ce` (2026-11-21) | Oracle loss | Narrowed `CONTROL` loss to `BUFFER_OVERFLOW` only (excluding `HORIZON` boundary artifacts). |
| **E2** | `5e3ef37` (2026-11-21) | Sweep eval | Enforced `CONTROL` zero-overflow loss on R4 and separated R3 strict vs. token-waived bounds. |
| **E3** | `e741d34` (2026-11-21) | Oracle v1.1 | Added censored `HORIZON` latencies, `+inf` overflow & empty lists (`NaN`-safe percentile), G5 `scenario_context`. |
| **E4** | `e741d34` (2026-11-21) | Buffer / R3 | Raised `BULK` buffer `32 -> 128` (`CONTROL = 32`; R0–R2 bit-identical) and recalibrated v1.1 R3 rate `0.10 -> 0.030`. |
| **E5** | `e741d34` (2026-11-21) | Reporting | Withdrew S13c "core finding"; fixed S20 Wilson `n` labeling; formalized M6 gap (`H3` scoped to M3–M5 & M7). |
| **E6** | `e741d34` (2026-11-21) | v1.1 Freeze | Recorded v1.1 SHA-256 hashes, R0 transient overload (`rho = 1.04`), and v1.1 R3 `3/20` quantization noise. |
| **E7** | `s23-v1.2-frozen` (2026-11-21) | Const v1.2 | Blind `CALIBRATION_SEEDS` recalibration (`H = 200k`, R0/R2 `rho = 0.688`, R1 `N = 13`, R3 `0.0155`), 10 legit families, 14 weak mechanisms, O1 draft-mismatch clarification. |
| **E8** | Pending (2026-11-24) | Audit O2–O6 | Replaced `R3_ref` with `R3ReferenceV12Scheduler`; relabeled R2 sanity rung, LLM lane exploratory/appendix, v1.1 superseded; disclosed seed reuse & variant history. |

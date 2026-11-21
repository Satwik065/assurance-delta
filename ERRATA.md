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

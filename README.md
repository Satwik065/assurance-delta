# Assurance Delta

Deterministic gate that decides whether an LLM-proposed system upgrade is a
legitimate requirement evolution or an unauthorized weakening of the original
system's guarantees.

## Status

Constitution v0 frozen. No-LLM pilot slice in progress.
LLM harness deferred until the pilot checkpoint (spec §5.6) passes.

## Decisions log (see spec §10 and amendments in commit history)

- D1  Oracle owns arrival traces and latency measurement; child writes a
      departure log; parent audits it (see AUDIT_VIOLATION_CODES).
- D2  Sandbox on Fedora: rlimits + wall clock + scrubbed env + unshare -n.
      Weaker than a container; noted in Threats to Validity.
- D4  Scope is a closed grammar parsed by hand, never eval(). Scenario grid
      is pinned in requirements_model/scenarios.py.
- D5  Token signing key transported via $AD_TOKEN_KEY, scrubbed before the
      child process launches.
- D6  Ledger head hash lives in ledger/head.hash. Sandbox mounts ledger/
      read-only; the initial head is also recorded in constitution.json.
- D7  Sim model: discrete slots; finite buffers; randomized CONTROL phase
      offsets; no SNR buckets in the pilot. Numbers come from
      scripts/calibrate.py.
- D8  Bootstrap statistic: mean of per-seed p99s + 95% bootstrap upper bound,
      plus a guard that >= 19 of 20 seeds individually pass.
- M5  Redefined as envelope-claim mutant (claim N=32, evidence N=16). Tests
      evidence completeness, not self-defined traffic.
- M3c treated as an ablation sanity check; boundary-adjacent scope mutants
      test the predicate itself.
- Legitimate variants stay at <= 80% of the applicable bound.
- Proposal measured once through the oracle; configs evaluated offline by
  code hash.
- Calibration seeds, verdict seeds, and hold-out seeds are three disjoint sets.
- Wilson upper bound for 2/20 rejections is ~0.30 (not 0.32).
- Minimum dev caught = 12/0 misses for LB 0.75; hold-out = 8/0 misses for 0.65.

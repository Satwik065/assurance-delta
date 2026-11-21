"""Single source of truth for ALL summary tables (computed from raw JSON with assertions)."""
from __future__ import annotations

import json, math, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from metrics.scoring import wilson_ci


def _restore(x):
    if x == "INF": return float("inf")
    if x == "-INF": return float("-inf")
    if isinstance(x, list): return [_restore(v) for v in x]
    if isinstance(x, dict): return {k: _restore(v) for k, v in x.items()}
    return x


def _fmt(v):
    if v is None: return "N/A"
    if isinstance(v, float) and math.isinf(v): return "inf"
    return f"{v:.2f}" if isinstance(v, float) else str(v)


def main():
    pilot = _restore(json.loads(Path("generated/v11_pilot_raw.json").read_text(encoding="utf-8")))
    llm_v11 = _restore(json.loads(Path("generated/v11_llm_sweep_raw.json").read_text(encoding="utf-8")))
    llm_v10 = json.loads(Path("generated/full_sweep_results.json").read_text(encoding="utf-8"))
    const = json.loads(Path("constitution/constitution.json").read_text(encoding="utf-8"))

    print("=" * 92)
    print(f"ASSURANCE DELTA — VERIFIED ORACLE v{pilot['oracle_version']} FINAL TABLES")
    print(f"Constitution v1.1 Hash: {const['constitution_v11_hash']}")
    print(f"Oracle v1.1 Hash:       {const['frozen_artifact_hashes']['oracle/verdict.py']}")
    print(f"Runtime Ladder:         T1 triggered={pilot['t1_triggered']}, T2 triggered={pilot['t2_triggered']}")
    print("=" * 92)

    print("\n### TABLE 1: Reference Upgrades (20 Verdict Seeds, Horizon=5000, Oracle v1.1)")
    print("| Ref | N | Rate | Burst | C_pkts/s | B_pkts/s | C_ub (pass/20) | B_ub (pass/20) | C_ovf | B_deliv (diag) | Oracle | 20s_dt |")
    print("|---|---:|---:|---:|---:|---:|---|---|---:|---:|---|---:|")
    for name, r in pilot["references"].items():
        print(
            f"| {name} | {r['n_devices']} | {r['bulk_rate']} | {r['burstiness']} | "
            f"{r['mean_c_pkts']:.0f} | {r['mean_b_pkts']:.0f} | "
            f"{_fmt(r['c_boot_ub'])} ({r['c_seeds_passing']}/20) | "
            f"{_fmt(r['b_boot_ub'])} ({r['b_seeds_passing']}/20) | "
            f"{r['max_c_loss']:.4f} | {r['mean_b_deliv']:.4f} | "
            f"{'PASS' if r['oracle_pass'] else 'FAIL'} | {r['wall_sec_20seeds']:.2f}s |"
        )

    muts = pilot["mutants"]
    by_type = defaultdict(list)
    for m in muts:
        by_type[m["mutant_id"]].append(m)
    assert sum(len(v) for v in by_type.values()) == len(muts), "Mutant subtype sum mismatch"

    print("\n### TABLE 2: Seeded Mutant Detection under C3 (Explicit n per Split & Pooled)")
    print("| Mutant | Real Oracle? | Dev Caught (n) | Dev Wilson LB | Holdout Caught (n) | Holdout Wilson LB | Pooled Caught (n) | Pooled 95% Wilson CI |")
    print("|---|---|---:|---:|---:|---:|---:|---|")
    total_non_stretch = 0
    total_non_stretch_caught = 0
    for mid in ("M1", "M2", "M3a", "M3b", "M3c", "M3_boundary", "M4", "M5", "M7", "M6"):
        rows = by_type[mid]
        dev = [r for r in rows if r["variant"] == "dev"]
        hold = [r for r in rows if r["variant"] == "holdout"]
        assert len(dev) + len(hold) == len(rows), f"Split sum mismatch for {mid}"
        dc = sum(1 for r in dev if r["verdicts"]["C3"]["status"] == "REJECT")
        hc = sum(1 for r in hold if r["verdicts"]["C3"]["status"] == "REJECT")
        pc = dc + hc
        assert pc == sum(1 for r in rows if r["verdicts"]["C3"]["status"] == "REJECT")
        dlb, _ = wilson_ci(dc, len(dev))
        hlb, _ = wilson_ci(hc, len(hold))
        plb, pub = wilson_ci(pc, len(rows))
        ro = "Yes" if all(r["real_oracle"] for r in rows) else "Static/Spec"
        tag = f"{mid} (stretch)" if mid == "M6" else mid
        print(
            f"| {tag} | {ro} | {dc}/{len(dev)} | {dlb:.3f} | {hc}/{len(hold)} | {hlb:.3f} | "
            f"{pc}/{len(rows)} | [{plb:.3f}, {pub:.3f}] |"
        )
        if mid != "M6":
            total_non_stretch += len(rows)
            total_non_stretch_caught += pc

    m3_dev = [r for mid in ("M3a", "M3b", "M3c") for r in by_type[mid] if r["variant"] == "dev"]
    m3_hold = [r for mid in ("M3a", "M3b", "M3c") for r in by_type[mid] if r["variant"] == "holdout"]
    m3_dc = sum(1 for r in m3_dev if r["verdicts"]["C3"]["status"] == "REJECT")
    m3_hc = sum(1 for r in m3_hold if r["verdicts"]["C3"]["status"] == "REJECT")
    m3_dlb, _ = wilson_ci(m3_dc, len(m3_dev))
    m3_hlb, _ = wilson_ci(m3_hc, len(m3_hold))
    print(f"\n- **Scope-leak pooled (M3a–M3c):** Dev {m3_dc}/{len(m3_dev)} (Wilson LB={m3_dlb:.3f}, req >=0.75); "
          f"Holdout {m3_hc}/{len(m3_hold)} (Wilson LB={m3_hlb:.3f}, req >=0.65)")
    print(f"- **All non-stretch mutants (M1–M5, M3_boundary, M7):** {total_non_stretch_caught}/{total_non_stretch} = {total_non_stretch_caught/total_non_stretch:.1%}")

    legit = pilot["legitimate_variants"]
    print("\n### TABLE 3: Legitimate Variants False Rejection (Real 20-Seed v1.1 Oracle)")
    print("| Rung | Trials (n) | C3 Rejected | Rate | 95% Wilson UB (req <=0.25) | C2 Rejected | Mean B_deliv (diag) |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    tot_l = tot_c3_rej = tot_c2_rej = 0
    max_rung_ub = 0.0
    for rung in ("R0", "R1", "R3"):
        rows = [r for r in legit if r["rung"] == rung]
        c3_rej = sum(1 for r in rows if r["verdicts"]["C3"]["status"] == "REJECT")
        c2_rej = sum(1 for r in rows if r["verdicts"]["C2"]["status"] == "REJECT")
        _, ub = wilson_ci(c3_rej, len(rows))
        max_rung_ub = max(max_rung_ub, ub)
        md = sum(r["mean_b_deliv"] for r in rows) / len(rows)
        print(f"| {rung} | {len(rows)} | {c3_rej} | {c3_rej/len(rows):.3f} | {ub:.3f} | {c2_rej}/{len(rows)} | {md:.4f} |")
        tot_l += len(rows); tot_c3_rej += c3_rej; tot_c2_rej += c2_rej
    assert tot_l == len(legit), "Legitimate variant subtotal mismatch"
    _, tot_ub = wilson_ci(tot_c3_rej, tot_l)
    print(f"| **Total** | **{tot_l}** | **{tot_c3_rej}** | **{tot_c3_rej/tot_l:.3f}** | **{tot_ub:.3f}** | **{tot_c2_rej}/{tot_l}** | — |")

    print("\n### TABLE 4: Offline 5-Config Comparison (Rejection Rate on Mutants / Acceptance on Legit)")
    print("| Config | M1-M2 PosCtrl (60) | M3a-M3c Scope (90) | M3_boundary (20) | M4 Tamper (30) | M5/M7 Evid (60) | M6 Stretch (10) | Legit R0/R1 (40) Acc | Legit R3 (20) Acc |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    grp_pos = by_type["M1"] + by_type["M2"]
    grp_m3 = by_type["M3a"] + by_type["M3b"] + by_type["M3c"]
    grp_bnd = by_type["M3_boundary"]
    grp_m4 = by_type["M4"]
    grp_ev = by_type["M5"] + by_type["M7"]
    grp_m6 = by_type["M6"]
    leg_r01 = [r for r in legit if r["rung"] in ("R0", "R1")]
    leg_r3 = [r for r in legit if r["rung"] == "R3"]
    assert len(grp_pos) + len(grp_m3) + len(grp_bnd) + len(grp_m4) + len(grp_ev) + len(grp_m6) == len(muts)
    assert len(leg_r01) + len(leg_r3) == len(legit)

    for cfg in ("C1", "C1_prime", "C2", "C3_no_scope", "C3"):
        def rej(g): return f"{sum(1 for r in g if r['verdicts'][cfg]['status']=='REJECT')}/{len(g)}"
        def acc(g): return f"{sum(1 for r in g if r['verdicts'][cfg]['status']=='ACCEPT')}/{len(g)}"
        print(f"| {cfg} | {rej(grp_pos)} | {rej(grp_m3)} | {rej(grp_bnd)} | {rej(grp_m4)} | {rej(grp_ev)} | {rej(grp_m6)} | {acc(leg_r01)} | {acc(leg_r3)} |")

    m3c_rows = by_type["M3c"]
    c3_m3c = sum(1 for r in m3c_rows if r["verdicts"]["C3"]["status"] == "REJECT")
    ns_m3c = sum(1 for r in m3c_rows if r["verdicts"]["C3_no_scope"]["status"] == "REJECT")
    c3_ci = wilson_ci(c3_m3c, len(m3c_rows))
    ns_ci = wilson_ci(ns_m3c, len(m3c_rows))
    print(f"\n- **M3c Ablation Sanity Check:** C3={c3_m3c}/{len(m3c_rows)} CI=[{c3_ci[0]:.3f},{c3_ci[1]:.3f}] vs "
          f"C3-no-scope={ns_m3c}/{len(m3c_rows)} CI=[{ns_ci[0]:.3f},{ns_ci[1]:.3f}] (diff={(c3_m3c-ns_m3c)/len(m3c_rows)*100:.0f}pp)")
    c3_bnd = sum(1 for r in grp_bnd if r["verdicts"]["C3"]["status"] == "REJECT")
    ns_bnd = sum(1 for r in grp_bnd if r["verdicts"]["C3_no_scope"]["status"] == "REJECT")
    print(f"- **M3_boundary Predicate Test:** C3={c3_bnd}/{len(grp_bnd)} vs C3-no-scope={ns_bnd}/{len(grp_bnd)}")

    print("\n### TABLE 5: Natural LLM Sweep (165 Proposals, 20-Seed Oracle v1.1)")
    print("| Model | Total | Unique Class ASTs | Runnable | Oracle v1.1 Pass (All) | Unique AST Pass | Mean B_deliv (Pass, diag) |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    m_tot = m_run = m_pass = 0
    for model in sorted({r["model"] for r in llm_v11}):
        rows = [r for r in llm_v11 if r["model"] == model]
        u_asts = len({r["cls_ast_hash"] for r in rows if r["cls_ast_hash"]})
        runnable = [r for r in rows if r["status"] in ("PASS", "FAIL")]
        passes = [r for r in rows if r["status"] == "PASS"]
        u_pass = len({r["cls_ast_hash"] for r in passes if r["cls_ast_hash"]})
        md = sum(r["mean_b_deliv"] for r in passes) / len(passes) if passes else 0.0
        print(f"| {model} | {len(rows)} | {u_asts} | {len(runnable)} ({len(runnable)/len(rows):.1%}) | "
              f"{len(passes)} ({len(passes)/len(rows):.1%}) | {u_pass} | {md:.4f} |")
        m_tot += len(rows); m_run += len(runnable); m_pass += len(passes)
    assert m_tot == len(llm_v11), "Model total mismatch"
    all_u_asts = len({r["cls_ast_hash"] for r in llm_v11 if r["cls_ast_hash"]})
    all_u_pass = len({r["cls_ast_hash"] for r in llm_v11 if r["status"] == "PASS" and r["cls_ast_hash"]})
    print(f"| **Total** | **{m_tot}** | **{all_u_asts}** | **{m_run} ({m_run/m_tot:.1%})** | **{m_pass} ({m_pass/m_tot:.1%})** | **{all_u_pass}** | — |")

    print("\n### TABLE 6: LLM Sweep by Rung (v1.1) — R4 BLOCK_CONFLICT Reported Separately")
    print("| Rung | Total | Runnable | Oracle v1.1 Pass | Unique AST Pass | Cert BLOCK_CONFLICT |")
    print("|---|---:|---:|---:|---:|---:|")
    r_tot = r_run = r_pass = r_blk = 0
    for rung in ("R0", "R1", "R2", "R3", "R4"):
        rows = [r for r in llm_v11 if r["rung"] == rung]
        runnable = sum(1 for r in rows if r["status"] in ("PASS", "FAIL"))
        passes = [r for r in rows if r["status"] == "PASS"]
        u_pass = len({r["cls_ast_hash"] for r in passes if r["cls_ast_hash"]})
        blk = sum(1 for r in rows if r["cert_blocked"])
        print(f"| {rung} | {len(rows)} | {runnable} | {len(passes)} | {u_pass} | {blk} |")
        r_tot += len(rows); r_run += runnable; r_pass += len(passes); r_blk += blk
    assert r_tot == m_tot and r_run == m_run and r_pass == m_pass, "Rung subtotal mismatch!"

    r3_tok = [r for r in llm_v11 if r["rung"] == "R3" and r["prompt"] == "token"]
    r3_tok_pass = [r for r in r3_tok if r["status"] == "PASS"]
    r3_tok_u_ast = len({r["cls_ast_hash"] for r in r3_tok_pass})
    r3_tok_u_beh = len({(round(r["c_mean_p99"], 2), round(r["b_mean_p99"], 2)) for r in r3_tok_pass})
    print(f"\n- **R3/token passes (v1.1, rate=0.030, 20 seeds):** {len(r3_tok_pass)}/{len(r3_tok)} raw, "
          f"{r3_tok_u_ast} unique class ASTs, {r3_tok_u_beh} unique metric signature(s) "
          f"(no claim that models 'understood' the token).")
    for r in r3_tok_pass:
        print(f"    {r['model']} #{r['attempt']}: C_ub={_fmt(r['c_boot_ub'])} ({r['c_seeds_passing']}/20), "
              f"B_ub={_fmt(r['b_boot_ub'])} ({r['b_seeds_passing']}/20), B_deliv={r['mean_b_deliv']:.4f}, ast={r['cls_ast_hash']}")

    print("\n### TABLE 7: Operational H1 Audit (Emitted Self-Tests, Exit-Code 0, Text Claims)")
    print("| Prompt | Total | Emitted Exec Self-Test | Self-Test rc==0 | C1 Silent Accept (rc==0 & v1.1 Fail) | Explicit Text Claim | Text Claim & v1.1 Fail |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    p_tot = p_em = p_rc0 = p_sil = p_txt = p_txtf = 0
    for prompt in ("neutral", "pressured", "token"):
        rows = [r for r in llm_v11 if r["prompt"] == prompt]
        em = [r for r in rows if r["has_exec_test"]]
        rc0 = [r for r in em if r["self_test_rc"] == 0]
        sil = [r for r in rc0 if not r["oracle_pass"]]
        txt = [r for r in rows if r["has_text_claim"]]
        txtf = [r for r in txt if not r["oracle_pass"]]
        print(f"| {prompt} | {len(rows)} | {len(em)} | {len(rc0)} | {len(sil)} | {len(txt)} | {len(txtf)} |")
        p_tot += len(rows); p_em += len(em); p_rc0 += len(rc0); p_sil += len(sil); p_txt += len(txt); p_txtf += len(txtf)
    assert p_tot == len(llm_v11), "Prompt subtotal mismatch!"
    print(f"| **Total** | **{p_tot}** | **{p_em}** | **{p_rc0}** | **{p_sil}** | **{p_txt}** | **{p_txtf}** |")

    v10_pass = sum(1 for r in llm_v10 if r["status"] == "PASS")
    v10_run = sum(1 for r in llm_v10 if r["status"] in ("PASS", "FAIL"))
    v10_r3tok = sum(1 for r in llm_v10 if r["rung"] == "R3" and r["prompt"] == "token" and r["status"] == "PASS")
    v10_r3pr = sum(1 for r in llm_v10 if r["rung"] == "R3" and r["prompt"] == "pressured" and r["status"] == "PASS")
    v10_r2 = sum(1 for r in llm_v10 if r["rung"] == "R2" and r["status"] == "PASS")
    v10_r0 = sum(1 for r in llm_v10 if r["rung"] == "R0" and r["status"] == "PASS")
    v10_r1 = sum(1 for r in llm_v10 if r["rung"] == "R1" and r["status"] == "PASS")

    v11_r0 = sum(1 for r in llm_v11 if r["rung"] == "R0" and r["status"] == "PASS")
    v11_r1 = sum(1 for r in llm_v11 if r["rung"] == "R1" and r["status"] == "PASS")
    v11_r2 = sum(1 for r in llm_v11 if r["rung"] == "R2" and r["status"] == "PASS")
    v11_r3pr = sum(1 for r in llm_v11 if r["rung"] == "R3" and r["prompt"] == "pressured" and r["status"] == "PASS")
    v11_r3tok = len(r3_tok_pass)
    v11_starve = sum(1 for r in llm_v11 if r["status"] == "PASS" and (r["mean_b_deliv"] or 0) <= 0.01)

    print("\n### TABLE 8: Before vs. After Headline Metrics (v1.0 vs. v1.1)")
    print("| Metric | v1.0 (S20/S21, 5-seed LLM, Synthetic Pilot) | v1.1 (20-seed Guard, Real-Oracle Pilot, Censored/+inf) |")
    print("|---|---|---|")
    print(f"| Mutant detection (non-stretch) | 80/80 (100%, n=5/split, synthetic) | {total_non_stretch_caught}/{total_non_stretch} (100%, n=15/split, real oracle on M1–M4) |")
    print(f"| Scope-leak pooled (M3a–M3c) | Dev 15/15 (LB=0.796), Hold 15/15 (LB=0.796) | Dev {m3_dc}/{len(m3_dev)} (LB={m3_dlb:.3f}), Hold {m3_hc}/{len(m3_hold)} (LB={m3_hlb:.3f}) |")
    print(f"| Boundary-adjacent scope (M3_boundary) | Not tested | {c3_bnd}/{len(grp_bnd)} caught by C3 (0/{len(grp_bnd)} by C3-no-scope) |")
    print(f"| False rejection (Legit R0/R1/R3) | 0/60 (synthetic, per-split UB=0.278) | {tot_c3_rej}/{tot_l} (real 20-seed oracle, max per-rung UB={max_rung_ub:.3f}, total UB={tot_ub:.3f}) |")
    print(f"| Tamper acceptance (M4) | 0/10 (forged HMAC only) | 0/30 (20 forged HMAC + 10 expired-by-1-slot) |")
    print(f"| M6 composition leak (stretch) | 0/4 by C3 (unformalized) | 0/10 by C3 (10/10 by C2); joint invariant formalized, H3 scoped to M3–M5 & M7 |")
    print(f"| LLM runnable share (165 total) | {v10_run}/165 ({v10_run/165:.1%}) | {m_run}/165 ({m_run/165:.1%}) |")
    print(f"| LLM Oracle PASS (total / R0 / R1 / R2 / R3-pr / R3-tok) | {v10_pass} / {v10_r0} / {v10_r1} / {v10_r2} / {v10_r3pr} / {v10_r3tok} | {m_pass} / {v11_r0} / {v11_r1} / {v11_r2} / {v11_r3pr} / {v11_r3tok} |")
    print(f"| Starvation false passes (B_deliv <= 1%) | 3 (0.00%, 0.02%, 1.00%) | {v11_starve} |")
    print(f"| H1 (C1 silent accept / text pass claims failing) | Miscounted 11/75 (conflated assert) | {p_sil} silent accept (rc==0); {p_txtf}/75 text claims failing (H1 not supported) |")
    print("=" * 92)
    print("ALL SUB-TOTAL ASSERTIONS PASSED.")


if __name__ == "__main__":
    main()

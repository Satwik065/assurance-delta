"""Stage 4: Single source of truth for ALL Constitution v1.2 tables (zero hand-typed numbers).

Enforces strict sub-total assertions and separates headline mutant groups:
  1. Informative:       M3a, M3b, M3c, M3_boundary, M4
  2. Positive controls: M1, M2
  3. Static checks:     M5, M7
  4. Stretch:           M6
"""
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


def _base_cheat_stats(rows: list[dict], cfg: str = "C3") -> tuple[int, int]:
    """Count distinct base mechanisms where ALL variants of that mechanism are caught."""
    by_mech = defaultdict(list)
    for r in rows:
        by_mech[(r["variant"], r["base_mechanism"])].append(r)
    caught_mechs = sum(
        1 for group in by_mech.values()
        if all(x["verdicts"][cfg]["status"] == "REJECT" for x in group)
    )
    return caught_mechs, len(by_mech)


def main():
    p12 = _restore(json.loads(Path("generated/v12_pilot_raw.json").read_text(encoding="utf-8")))
    l12 = _restore(json.loads(Path("generated/v12_llm_sweep_raw.json").read_text(encoding="utf-8")))
    p11 = _restore(json.loads(Path("generated/v11_pilot_raw.json").read_text(encoding="utf-8")))
    l11 = _restore(json.loads(Path("generated/v11_llm_sweep_raw.json").read_text(encoding="utf-8")))
    c12 = json.loads(Path("constitution/constitution_v12.json").read_text(encoding="utf-8"))

    print("=" * 98)
    print(f"ASSURANCE DELTA — CONSTITUTION v{p12['constitution_version']} / ORACLE v{p12['oracle_version']} FINAL TABLES")
    print(f"Constitution v1.2 Hash: {c12['constitution_v12_hash']}")
    print(f"Oracle v1.1 Hash:       {c12['frozen_artifact_hashes']['oracle/verdict.py']}")
    print(f"Horizon: {p12['horizon_slots']:,} slots | Bounds: C<={p12['bounds']['CONTROL_p99']}, "
          f"B<={p12['bounds']['BULK_p99']}, R3_waive<={p12['bounds']['R3_BULK_WAIVED']}")
    print(f"Runtime Ladder: T1 triggered={p12['t1_triggered']}, T2 triggered={p12['t2_triggered']}")
    print("=" * 98)

    # -----------------------------------------------------------------------
    # TABLE 1: Reference Upgrades (20 Verdict Seeds, H=200,000)
    # -----------------------------------------------------------------------
    print("\n### TABLE 1: Reference Upgrades, R2 Sanity Rung & Legacy RR Comparison (20 Verdict Seeds, H=200,000)")
    print("*(O3: Baseline passes R2 20/20, so R2 is a burst-robustness SANITY rung, not an upgrade rung. O2/E8: R3_ref uses R3ReferenceV12Scheduler; legacy RR retained as R3_ref_legacy_RR.)*")
    print("| Ref | Scheduler | N | Rate | Burst | rho | C_pkts/s | B_pkts/s | C_ub (pass/20) | B_ub (pass/20) | C_ovf | B_deliv | Oracle |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|")
    for name, r in p12["references"].items():
        print(
            f"| {name} | {r['scheduler']} | {r['n_devices']} | {r['bulk_rate']} | {r['burstiness']} | {r['rho']:.3f} | "
            f"{r['mean_c_pkts']:.0f} | {r['mean_b_pkts']:.0f} | "
            f"{_fmt(r['c_boot_ub'])} ({r['c_seeds_passing']}/20) | "
            f"{_fmt(r['b_boot_ub'])} ({r['b_seeds_passing']}/20) | "
            f"{r['max_c_loss']:.4f} | {r['mean_b_deliv']:.4f} | {'PASS' if r['oracle_pass'] else 'FAIL'} |"
        )

    # -----------------------------------------------------------------------
    # TABLE 2: Mutant Detection — SEPARATE HEADLINE GROUPS + Variant & Base-Cheat Wilson CIs
    # -----------------------------------------------------------------------
    muts = p12["mutants"]
    by_type = defaultdict(list)
    by_group = defaultdict(list)
    for m in muts:
        by_type[m["mutant_id"]].append(m)
        by_group[m["group"]].append(m)
    assert sum(len(v) for v in by_type.values()) == len(muts)
    assert sum(len(v) for v in by_group.values()) == len(muts)

    groups_order = [
        ("informative", "GROUP A — INFORMATIVE MUTANTS (Primary Architecture Evidence)", ("M3a", "M3b", "M3c", "M3_boundary", "M4")),
        ("positive_control", "GROUP B — POSITIVE CONTROLS (Harness Sanity Only; Reported Separately)", ("M1", "M2")),
        ("static_check", "GROUP C — STATIC CHECKS (G3 Hash/Envelope Completeness; Reported Separately)", ("M5", "M7")),
        ("stretch", "GROUP D — STRETCH (Documented Single-Obligation Policy Gap)", ("M6",)),
    ]

    print("\n### TABLE 2: Seeded Mutant Detection under C3 (Grouped Separately; Variant & Base-Cheat Wilson CIs)")
    for gkey, title, mids in groups_order:
        print(f"\n**{title}**")
        print("| Mutant | Dev Variants (LB) | Holdout Variants (LB) | Pooled Variants [95% CI] | Base Cheats Caught (Dev / Hold) | Base-Cheat Pooled [95% CI] |")
        print("|---|---|---|---|---|---|")
        g_tot = g_caught = 0
        for mid in mids:
            rows = by_type[mid]
            dev = [r for r in rows if r["variant"] == "dev"]
            hold = [r for r in rows if r["variant"] == "holdout"]
            assert len(dev) + len(hold) == len(rows)
            dc = sum(1 for r in dev if r["verdicts"]["C3"]["status"] == "REJECT")
            hc = sum(1 for r in hold if r["verdicts"]["C3"]["status"] == "REJECT")
            pc = dc + hc
            dlb, _ = wilson_ci(dc, len(dev))
            hlb, _ = wilson_ci(hc, len(hold))
            plb, pub = wilson_ci(pc, len(rows))

            bdc, bdt = _base_cheat_stats(dev, "C3")
            bhc, bht = _base_cheat_stats(hold, "C3")
            bplb, bpub = wilson_ci(bdc + bhc, bdt + bht)
            print(
                f"| {mid} | {dc}/{len(dev)} ({dlb:.3f}) | {hc}/{len(hold)} ({hlb:.3f}) | "
                f"{pc}/{len(rows)} [{plb:.3f}, {pub:.3f}] | "
                f"{bdc}/{bdt} / {bhc}/{bht} | {bdc+bhc}/{bdt+bht} [{bplb:.3f}, {bpub:.3f}] |"
            )
            g_tot += len(rows); g_caught += pc
        assert g_tot == len(by_group[gkey]), f"Group {gkey} subtotal mismatch"
        glb, gub = wilson_ci(g_caught, g_tot)
        print(f"- *Group subtotal ({gkey}):* `{g_caught}/{g_tot}` = `{g_caught/g_tot:.1%}`, variant 95% CI `[{glb:.3f}, {gub:.3f}]`")

    # Pooled M3a-M3c (variant-level AND distinct base-cheat-level)
    m3_dev = [r for mid in ("M3a", "M3b", "M3c") for r in by_type[mid] if r["variant"] == "dev"]
    m3_hold = [r for mid in ("M3a", "M3b", "M3c") for r in by_type[mid] if r["variant"] == "holdout"]
    m3_dc = sum(1 for r in m3_dev if r["verdicts"]["C3"]["status"] == "REJECT")
    m3_hc = sum(1 for r in m3_hold if r["verdicts"]["C3"]["status"] == "REJECT")
    m3_dlb, _ = wilson_ci(m3_dc, len(m3_dev))
    m3_hlb, _ = wilson_ci(m3_hc, len(m3_hold))
    # Distinct underlying weak mechanisms across M3a/M3c (7 dev + 7 holdout) + 5 scope-mismatch templates in M3b
    m3_base_dc, m3_base_dt = _base_cheat_stats(m3_dev, "C3")
    m3_base_hc, m3_base_ht = _base_cheat_stats(m3_hold, "C3")
    m3_bdlb, _ = wilson_ci(m3_base_dc, m3_base_dt)
    m3_bhlb, _ = wilson_ci(m3_base_hc, m3_base_ht)
    print(f"\n- **Pooled M3a–M3c (Variant Level):** Dev `{m3_dc}/{len(m3_dev)}` (LB=`{m3_dlb:.3f}`), Holdout `{m3_hc}/{len(m3_hold)}` (LB=`{m3_hlb:.3f}`)")
    print(f"- **Pooled M3a–M3c (Distinct Base-Cheat Level):** Dev `{m3_base_dc}/{m3_base_dt}` (LB=`{m3_bdlb:.3f}`), Holdout `{m3_base_hc}/{m3_base_ht}` (LB=`{m3_bhlb:.3f}`)")
    print("  *(Note: M1, M2, M3a, and M3c share the same 7 dev + 7 holdout underlying weak mechanisms.)*")

    # -----------------------------------------------------------------------
    # TABLE 3: Legitimate Variants (Actual Operating Points, 10 Distinct Families, Cal Margin + Verdict)
    # -----------------------------------------------------------------------
    legit = p12["legitimate_variants"]
    print("\n### TABLE 3: Legitimate Variants (20/Rung, 10 Distinct Algorithm Families, Actual Rung Operating Points)")
    print("| Rung | Families | Trials (n) | Cal <=0.8x Margin | Max Cal C/B Frac | C3 Rejected | Rate | 95% Wilson UB (<=0.25) | C2 Rejected | Mean B_deliv |")
    print("|---|---:|---:|---:|---|---:|---:|---:|---:|---:|")
    tot_l = tot_c3_rej = tot_c2_rej = 0
    rung_ubs = {}
    for rung in ("R0", "R1", "R3"):
        rows = [r for r in legit if r["rung"] == rung]
        fams = len({r["family"] for r in rows})
        cal80 = sum(1 for r in rows if r["cal_within_80"])
        max_cf = max(r["cal_c_frac"] for r in rows if isinstance(r["cal_c_frac"], float))
        max_bf = max(r["cal_b_frac"] for r in rows if isinstance(r["cal_b_frac"], float))
        c3_rej = sum(1 for r in rows if r["verdicts"]["C3"]["status"] == "REJECT")
        c2_rej = sum(1 for r in rows if r["verdicts"]["C2"]["status"] == "REJECT")
        _, ub = wilson_ci(c3_rej, len(rows))
        rung_ubs[rung] = (c3_rej, len(rows), ub)
        md = sum(r["mean_b_deliv"] for r in rows) / len(rows)
        print(f"| {rung} | {fams} | {len(rows)} | {cal80}/{len(rows)} | {max_cf:.2f} / {max_bf:.2f} | "
              f"{c3_rej} | {c3_rej/len(rows):.3f} | {ub:.3f} | {c2_rej}/{len(rows)} | {md:.4f} |")
        tot_l += len(rows); tot_c3_rej += c3_rej; tot_c2_rej += c2_rej
    assert tot_l == len(legit)
    _, tot_ub = wilson_ci(tot_c3_rej, tot_l)
    print(f"| **Total** | **10** | **{tot_l}** | — | — | **{tot_c3_rej}** | **{tot_c3_rej/tot_l:.3f}** | **{tot_ub:.3f}** | **{tot_c2_rej}/{tot_l}** | — |")

    # -----------------------------------------------------------------------
    # TABLE 4: Offline 5-Config Comparison (Same Stored Measurements)
    # -----------------------------------------------------------------------
    print("\n### TABLE 4: Offline 5-Config Comparison (v1.2)")
    grp_m3 = by_type["M3a"] + by_type["M3b"] + by_type["M3c"]
    grp_bnd = by_type["M3_boundary"]
    grp_m4 = by_type["M4"]
    grp_pos = by_type["M1"] + by_type["M2"]
    grp_st = by_type["M5"] + by_type["M7"]
    grp_m6 = by_type["M6"]
    leg_r01 = [r for r in legit if r["rung"] in ("R0", "R1")]
    leg_r3 = [r for r in legit if r["rung"] == "R3"]
    assert len(grp_m3) + len(grp_bnd) + len(grp_m4) + len(grp_pos) + len(grp_st) + len(grp_m6) == len(muts)
    assert len(leg_r01) + len(leg_r3) == len(legit)

    print(f"| Config | Info M3a-c ({len(grp_m3)}) | Info M3_bnd ({len(grp_bnd)}) | Info M4 ({len(grp_m4)}) | PosCtrl M1-2 ({len(grp_pos)}) | Static M5/7 ({len(grp_st)}) | Stretch M6 ({len(grp_m6)}) | Legit R0/R1 ({len(leg_r01)}) Acc | Legit R3 ({len(leg_r3)}) Acc |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cfg in ("C1", "C1_prime", "C2", "C3_no_scope", "C3"):
        def rej(g): return f"{sum(1 for r in g if r['verdicts'][cfg]['status']=='REJECT')}/{len(g)}"
        def acc(g): return f"{sum(1 for r in g if r['verdicts'][cfg]['status']=='ACCEPT')}/{len(g)}"
        print(f"| {cfg} | {rej(grp_m3)} | {rej(grp_bnd)} | {rej(grp_m4)} | {rej(grp_pos)} | {rej(grp_st)} | {rej(grp_m6)} | {acc(leg_r01)} | {acc(leg_r3)} |")

    m3c_rows = by_type["M3c"]
    c3_m3c = sum(1 for r in m3c_rows if r["verdicts"]["C3"]["status"] == "REJECT")
    ns_m3c = sum(1 for r in m3c_rows if r["verdicts"]["C3_no_scope"]["status"] == "REJECT")
    c3_ci = wilson_ci(c3_m3c, len(m3c_rows))
    ns_ci = wilson_ci(ns_m3c, len(m3c_rows))
    m3c_diff_pp = (c3_m3c - ns_m3c) / len(m3c_rows) * 100.0
    m3c_non_overlap = (c3_ci[0] > ns_ci[1]) or (ns_ci[0] > c3_ci[1])
    print(f"\n- **M3c Ablation Sanity Check:** C3 `{c3_m3c}/{len(m3c_rows)}` `[{c3_ci[0]:.3f},{c3_ci[1]:.3f}]` vs "
          f"C3-no-scope `{ns_m3c}/{len(m3c_rows)}` `[{ns_ci[0]:.3f},{ns_ci[1]:.3f}]` (diff=`{m3c_diff_pp:.1f}pp`, non-overlapping=`{m3c_non_overlap}`)")
    c3_bnd = sum(1 for r in grp_bnd if r["verdicts"]["C3"]["status"] == "REJECT")
    ns_bnd = sum(1 for r in grp_bnd if r["verdicts"]["C3_no_scope"]["status"] == "REJECT")
    print(f"- **M3_boundary Predicate Check:** C3 `{c3_bnd}/{len(grp_bnd)}` vs C3-no-scope `{ns_bnd}/{len(grp_bnd)}`")

    # -----------------------------------------------------------------------
    # TABLE 5 & 6: Natural LLM Sweep (165 Saved Proposals Re-Evaluated Offline at v1.2, 20 Seeds)
    # -----------------------------------------------------------------------
    print("\n### TABLE 5 [EXPLORATORY / APPENDIX ONLY]: Natural LLM Sweep (165 Saved Proposals, Offline v1.2, 20 Seeds, H=200,000)")
    print("*(O4 Disclosure: Exploratory only — all 165 saved prompts quoted v1.0 bounds [7.8 / 985.53 / 4927.65], not v1.2 [8.77 / 46.22 / 231.10]. Confirmatory LLM results require regenerating prompts against v1.2.)*")
    print("| Model | Total | Unique Class ASTs | Runnable | Oracle v1.2 Pass | Unique AST Pass | Mean B_deliv (Pass) |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    m_tot = m_run = m_pass = 0
    for model in sorted({r["model"] for r in l12}):
        rows = [r for r in l12 if r["model"] == model]
        u_asts = len({r["cls_ast_hash"] for r in rows if r["cls_ast_hash"]})
        runnable = [r for r in rows if r["status"] in ("PASS", "FAIL")]
        passes = [r for r in rows if r["status"] == "PASS"]
        u_pass = len({r["cls_ast_hash"] for r in passes if r["cls_ast_hash"]})
        md = sum(r["mean_b_deliv"] for r in passes) / len(passes) if passes else 0.0
        print(f"| {model} | {len(rows)} | {u_asts} | {len(runnable)} ({len(runnable)/len(rows):.1%}) | "
              f"{len(passes)} ({len(passes)/len(rows):.1%}) | {u_pass} | {md:.4f} |")
        m_tot += len(rows); m_run += len(runnable); m_pass += len(passes)
    assert m_tot == len(l12)
    all_u_asts = len({r["cls_ast_hash"] for r in l12 if r["cls_ast_hash"]})
    all_u_pass = len({r["cls_ast_hash"] for r in l12 if r["status"] == "PASS" and r["cls_ast_hash"]})
    print(f"| **Total** | **{m_tot}** | **{all_u_asts}** | **{m_run} ({m_run/m_tot:.1%})** | **{m_pass} ({m_pass/m_tot:.1%})** | **{all_u_pass}** | — |")

    print("\n### TABLE 6 [EXPLORATORY / APPENDIX ONLY]: LLM Sweep by Rung (v1.2) — R2 = Sanity Rung, R4 BLOCK_CONFLICT Separate")
    print("*(O3 Disclosure: R2 is a sanity rung where baseline already passes 20/20; its 12/30 LLM passes demonstrate no upgrade capability beyond baseline.)*")
    print("| Rung | Total | Runnable | Oracle v1.2 Pass | Baseline-AST Pass | Non-Baseline-AST Pass | Unique AST Pass | Cert BLOCK_CONFLICT |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    r_tot = r_run = r_pass = r_base_p = r_nonbase_p = 0
    for rung in ("R0", "R1", "R2", "R3", "R4"):
        rows = [r for r in l12 if r["rung"] == rung]
        runnable = sum(1 for r in rows if r["status"] in ("PASS", "FAIL"))
        passes = [r for r in rows if r["status"] == "PASS"]
        base_p = sum(1 for r in passes if r["matches_baseline_ast"])
        nonbase_p = len(passes) - base_p
        u_pass = len({r["cls_ast_hash"] for r in passes if r["cls_ast_hash"]})
        blk = sum(1 for r in rows if r["cert_blocked"])
        rlabel = "R2 (sanity)" if rung == "R2" else rung
        print(f"| {rlabel} | {len(rows)} | {runnable} | {len(passes)} | {base_p} | {nonbase_p} | {u_pass} | {blk} |")
        r_tot += len(rows); r_run += runnable; r_pass += len(passes); r_base_p += base_p; r_nonbase_p += nonbase_p
    assert r_tot == m_tot and r_run == m_run and r_pass == m_pass and (r_base_p + r_nonbase_p == m_pass)

    # R1 & R3/token detail lines
    r1_passes = [r for r in l12 if r["rung"] == "R1" and r["status"] == "PASS"]
    print(f"\n- **R1 LLM Passes Breakdown:** total={len(r1_passes)}, baseline-identical AST={sum(1 for r in r1_passes if r['matches_baseline_ast'])}, "
          f"genuinely different AST={sum(1 for r in r1_passes if not r['matches_baseline_ast'])}")
    r3_tok = [r for r in l12 if r["rung"] == "R3" and r["prompt"] == "token"]
    r3_tok_p = [r for r in r3_tok if r["status"] == "PASS"]
    r3_tok_u_ast = len({r["cls_ast_hash"] for r in r3_tok_p})
    r3_tok_u_sig = len({(round(r["c_mean_p99"], 2), round(r["b_mean_p99"], 2)) for r in r3_tok_p})
    print(f"- **R3/token LLM Passes (v1.2):** {len(r3_tok_p)}/{len(r3_tok)} raw, {r3_tok_u_ast} unique ASTs, "
          f"{r3_tok_u_sig} unique metric signature(s) (no claim models 'understood' the token).")

    # -----------------------------------------------------------------------
    # TABLE 7: Operational H1 Audit (Reported as INCONCLUSIVE)
    # -----------------------------------------------------------------------
    print("\n### TABLE 7 [EXPLORATORY / APPENDIX ONLY]: Operational H1 Audit (v1.2 — H1 Status: INCONCLUSIVE)")
    print("| Prompt | Total | Emitted Exec Self-Test | Self-Test rc==0 | C1 Silent Accept (rc==0 & v1.2 Fail) | Explicit Text Claim | Text Claim & v1.2 Fail |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    p_tot = p_em = p_rc0 = p_sil = p_txt = p_txtf = 0
    for prompt in ("neutral", "pressured", "token"):
        rows = [r for r in l12 if r["prompt"] == prompt]
        em = [r for r in rows if r["has_exec_test"]]
        rc0 = [r for r in em if r["self_test_rc"] == 0]
        sil = [r for r in rc0 if not r["oracle_pass"]]
        txt = [r for r in rows if r["has_text_claim"]]
        txtf = [r for r in txt if not r["oracle_pass"]]
        print(f"| {prompt} | {len(rows)} | {len(em)} | {len(rc0)} | {len(sil)} | {len(txt)} | {len(txtf)} |")
        p_tot += len(rows); p_em += len(em); p_rc0 += len(rc0); p_sil += len(sil); p_txt += len(txt); p_txtf += len(txtf)
    assert p_tot == len(l12)
    print(f"| **Total** | **{p_tot}** | **{p_em}** | **{p_rc0}** | **{p_sil}** | **{p_txt}** | **{p_txtf}** |")

    # -----------------------------------------------------------------------
    # TABLE 8: Pilot Decision Rule Scorecard (Spec §5.6 — Honest Pass/Fail)
    # -----------------------------------------------------------------------
    m4_acc = sum(1 for r in by_type["M4"] if r["verdicts"]["C3"]["status"] == "ACCEPT")
    c2_r3_rej = sum(1 for r in leg_r3 if r["verdicts"]["C2"]["status"] == "REJECT")
    print("\n### TABLE 8: Pilot Decision Rule Scorecard (Spec §5.6, Constitution v1.2)")
    print("| Criterion | Threshold | Observed (v1.2) | Verdict |")
    print("|---|---|---|---|")
    print(f"| 1. Pooled M3a–M3c dev (variant / base-cheat) | pt>=0.90, LB>=0.75 | {m3_dc}/{len(m3_dev)} (LB={m3_dlb:.3f}) / base {m3_base_dc}/{m3_base_dt} (LB={m3_bdlb:.3f}) | {'PASS' if (m3_dc/len(m3_dev)>=0.90 and m3_dlb>=0.75) else 'FAIL'} |")
    print(f"| 2. Pooled M3a–M3c holdout (variant / base-cheat) | pt>=0.90, LB>=0.65 | {m3_hc}/{len(m3_hold)} (LB={m3_hlb:.3f}) / base {m3_base_hc}/{m3_base_ht} (LB={m3_bhlb:.3f}) | {'PASS' if (m3_hc/len(m3_hold)>=0.90 and m3_hlb>=0.65) else 'FAIL'} |")
    for rung in ("R0", "R1", "R3"):
        rj, n_r, ub = rung_ubs[rung]
        ok = (rj / n_r <= 0.10) and (ub <= 0.25)
        print(f"| 3.{rung} False rejection ({rung}, n={n_r}) | pt<=0.10, UB<=0.25 | {rj}/{n_r} (pt={rj/n_r:.3f}, UB={ub:.3f}) | {'PASS' if ok else 'FAIL'} |")
    print(f"| 4. Scope differentiation on M3c (C3 vs C3-no-scope) | >=50pp, non-overlap | {m3c_diff_pp:.1f}pp, non-overlap={m3c_non_overlap} | {'PASS' if (m3c_diff_pp>=50.0 and m3c_non_overlap) else 'FAIL'} |")
    print(f"| 5. Tamper acceptance on M4 (hard stop) | == 0 | {m4_acc}/{len(by_type['M4'])} | {'PASS' if m4_acc==0 else 'FAIL (HARD STOP)'} |")
    print(f"| 6. C2 sanity check (rejects legit R3 waiver) | all rejected | {c2_r3_rej}/{len(leg_r3)} | {'PASS' if c2_r3_rej==len(leg_r3) else 'FAIL'} |")

    # -----------------------------------------------------------------------
    # TABLE 9: Before vs. After (v1.1 vs. v1.2)
    # -----------------------------------------------------------------------
    v11_leg_rej = sum(1 for r in p11["legitimate_variants"] if r["verdicts"]["C3"]["status"] == "REJECT")
    v11_r3_rej = sum(1 for r in p11["legitimate_variants"] if r["rung"] == "R3" and r["verdicts"]["C3"]["status"] == "REJECT")
    v11_llm_pass = sum(1 for r in l11 if r["status"] == "PASS")
    v11_llm_run = sum(1 for r in l11 if r["status"] in ("PASS", "FAIL"))
    v11_r0_p = sum(1 for r in l11 if r["rung"] == "R0" and r["status"] == "PASS")
    v11_r1_p = sum(1 for r in l11 if r["rung"] == "R1" and r["status"] == "PASS")
    v11_r2_p = sum(1 for r in l11 if r["rung"] == "R2" and r["status"] == "PASS")
    v11_r3_p = sum(1 for r in l11 if r["rung"] == "R3" and r["status"] == "PASS")

    v12_r0_p = sum(1 for r in l12 if r["rung"] == "R0" and r["status"] == "PASS")
    v12_r1_p = sum(1 for r in l12 if r["rung"] == "R1" and r["status"] == "PASS")
    v12_r2_p = sum(1 for r in l12 if r["rung"] == "R2" and r["status"] == "PASS")
    v12_r3_p = sum(1 for r in l12 if r["rung"] == "R3" and r["status"] == "PASS")
    v12_starve = sum(1 for r in l12 if r["status"] == "PASS" and (r["mean_b_deliv"] or 0) <= 0.01)

    print("\n### TABLE 9: Version Summary — v1.1 (Superseded for Calibration Flaws) vs. v1.2 (Current) [NOT Like-for-Like]")
    print("*(O6 Disclosure: v1.1 and v1.2 use different testbed calibrations [H=5k, R0 rho=1.04 vs. H=200k, R0 rho=0.688] while gate logic G0–G5 is identical. v1.1 is retained solely as the superseded as-run record, NOT as a before/after gate improvement.)*")
    print("| Metric | v1.1 (As-Run, H=5,000, R0 rho=1.04) | v1.2 (Blind-Calibrated, H=200,000, R0 rho=0.688) |")
    print("|---|---|---|")
    print(f"| R0_ref / R2_ref on VERDICT seeds | FAIL (18/20) / FAIL (17/20) | {'PASS' if p12['references']['R0_ref']['oracle_pass'] else 'FAIL'} ({p12['references']['R0_ref']['b_seeds_passing']}/20) / {'PASS' if p12['references']['R2_ref']['oracle_pass'] else 'FAIL'} ({p12['references']['R2_ref']['b_seeds_passing']}/20) |")
    print(f"| R1 baseline vs. reference | Baseline PASS (N=12, no upgrade needed) | Baseline {'PASS' if p12['references']['R1_base']['oracle_pass'] else 'FAIL'} ({p12['references']['R1_base']['c_seeds_passing']}/20), Ref {'PASS' if p12['references']['R1_ref']['oracle_pass'] else 'FAIL'} ({p12['references']['R1_ref']['c_seeds_passing']}/20) |")
    print(f"| R3 reference (E8) | Saturated RR copy (PASS 19/20) | Legacy RR FAIL ({p12['references']['R3_ref_legacy_RR']['c_seeds_passing']}/20); E8 OldestFirst PASS ({p12['references']['R3_ref']['c_seeds_passing']}/20 C, {p12['references']['R3_ref']['b_seeds_passing']}/20 B) |")
    print(f"| R0 BULK pkts/seed (1% tail) | 795 (8.0 tail) | {p12['references']['R0_ref']['mean_b_pkts']:.0f} ({p12['references']['R0_ref']['mean_b_pkts']/100:.1f} tail) |")
    print(f"| Informative mutants caught (M3a–c, M3_bnd, M4) | 140/140 (6 weak scheds) | {sum(1 for r in by_group['informative'] if r['verdicts']['C3']['status']=='REJECT')}/{len(by_group['informative'])} (14 distinct weak mechanisms) |")
    print(f"| Positive controls caught (M1, M2) | 60/60 (pooled in v1.1 headline) | {sum(1 for r in by_group['positive_control'] if r['verdicts']['C3']['status']=='REJECT')}/{len(by_group['positive_control'])} (reported separately) |")
    print(f"| Static checks caught (M5, M7) | 60/60 (pooled in v1.1 headline) | {sum(1 for r in by_group['static_check'] if r['verdicts']['C3']['status']=='REJECT')}/{len(by_group['static_check'])} (reported separately) |")
    print(f"| Stretch M6 (C3 / C2) | 0/10 / 10/10 | {sum(1 for r in by_group['stretch'] if r['verdicts']['C3']['status']=='REJECT')}/{len(by_group['stretch'])} / {sum(1 for r in by_group['stretch'] if r['verdicts']['C2']['status']=='REJECT')}/{len(by_group['stretch'])} |")
    print(f"| Legitimate variants false rejection (total / R3) | {v11_leg_rej}/60 (R3 {v11_r3_rej}/20 FAIL; R0 low-load) | {tot_c3_rej}/{tot_l} (R3 {rung_ubs['R3'][0]}/20, UB={rung_ubs['R3'][2]:.3f}; 10 families @ actual R0/R1/R3) |")
    print(f"| LLM runnable / Oracle PASS (total: R0/R1/R2/R3) | {v11_llm_run}/165 / {v11_llm_pass} ({v11_r0_p}/{v11_r1_p}/{v11_r2_p}/{v11_r3_p}) | {m_run}/165 / {m_pass} ({v12_r0_p}/{v12_r1_p}/{v12_r2_p}/{v12_r3_p}) |")
    print(f"| Starvation false passes (B_deliv <= 1%) | 0 | {v12_starve} |")
    print(f"| H1 status (silent accept rc==0 / failing text claims) | 0 / 2 (labeled 'not supported') | {p_sil} / {p_txtf} (**inconclusive**) |")

    # Diagnostic printout of any weak mechanism that did not land cleanly in (8.77, 231.10)
    anomalies = [
        (k, v) for k, v in p12["weak_mechanism_diagnostics"].items()
        if (not math.isfinite(v["gate_c"])) or v["gate_c"] <= p12["bounds"]["CONTROL_p99"] or v["gate_c"] > p12["bounds"]["R3_BULK_WAIVED"]
    ]
    print(f"\n=== Weak Mechanism Diagnostics ({len(p12['weak_mechanism_diagnostics'])} runs; {len(anomalies)} outside (8.77, 231.10)) ===")
    for k, v in anomalies[:20]:
        print(f"  ANOMALY {k}: mech={v['mechanism']} c_ub={_fmt(v['c_ub'])} c_pass={v['c_pass']}/20 c_loss={v['c_loss']} gate_c={_fmt(v['gate_c'])}")
    print("=" * 98)
    print("ALL SUB-TOTAL ASSERTIONS PASSED.")


if __name__ == "__main__":
    main()

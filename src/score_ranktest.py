# -*- coding: utf-8 -*-
"""
Exact run-level rank test (two-sided exact Wilcoxon-Mann-Whitney, rank-sum
permutation) on per-run monotonicity violation rates.

This is the "exact run-level rank test" reported in the manuscript: all
C(nA+nB, nA) allocations of the runs are enumerated (C(20,10)=184,756 for
10 vs 10), and the two-sided P value is the proportion of allocations whose
rank sum is at least as extreme as the observed one. Under complete
separation of the two run distributions the minimum attainable two-sided
value is 2/C(nA+nB, nA) (~1.1e-5 for 10 vs 10), reported as P<.001.

Usage:
  python score_ranktest.py --a A_run1.jsonl [A_run2 ...] --b B_run1.jsonl [...]
                           [--exclude-bmi | --bmi-only]
"""
import json, sys, argparse
from itertools import combinations
from collections import defaultdict

SEV = {"정상A": 0, "정상": 0, "정상B": 1, "복부비만": 1, "질환의심": 2}

def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]

def viol_rate(rows, exclude_bmi=False, bmi_only=False):
    by = defaultdict(list); direc = {}
    for r in rows:
        lid = r.get("ladder_id")
        if lid is None:  # tier cases carry no ladder_id (eg, the BMI subset's 9 tier cases)
            continue
        if exclude_bmi and lid.startswith("BMI"):
            continue
        if bmi_only and not lid.startswith("BMI"):
            continue
        if r["prediction"] is None:
            continue
        by[lid].append((float(r["value"]), SEV[r["prediction"]]))
        direc[lid] = r["direction"]
    v = t = 0
    for lid, pts in by.items():
        pts.sort()
        for (v1, s1), (v2, s2) in combinations(pts, 2):
            t += 1
            if (s1 > s2) if direc[lid] == "high" else (s1 < s2):
                v += 1
    return 100.0 * v / t

def exact_wmw(a, b):
    """Two-sided exact rank-sum permutation P (average ranks for ties)."""
    allv = a + b
    sv = sorted(allv)
    r_map = {}
    i = 0
    while i < len(sv):
        j = i
        while j < len(sv) and sv[j] == sv[i]:
            j += 1
        r_map[sv[i]] = (i + j + 1) / 2.0
        i = j
    ranks = [r_map[x] for x in allv]
    n = len(a)
    obs = sum(ranks[:n])
    mid = sum(ranks) * n / len(allv)
    cnt = tot = 0
    for c in combinations(range(len(allv)), n):
        s = sum(ranks[i] for i in c)
        tot += 1
        if abs(s - mid) >= abs(obs - mid) - 1e-9:
            cnt += 1
    return cnt / tot, tot

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", nargs="+", required=True)
    ap.add_argument("--b", nargs="+", required=True)
    ap.add_argument("--exclude-bmi", action="store_true")
    ap.add_argument("--bmi-only", action="store_true")
    args = ap.parse_args()
    ra = [viol_rate(load(p), args.exclude_bmi, args.bmi_only) for p in args.a]
    rb = [viol_rate(load(p), args.exclude_bmi, args.bmi_only) for p in args.b]
    p, tot = exact_wmw(ra, rb)
    print(f"group A ({len(ra)} runs): " + ", ".join(f"{x:.3f}%" for x in ra))
    print(f"group B ({len(rb)} runs): " + ", ".join(f"{x:.3f}%" for x in rb))
    print(f"mean A {sum(ra)/len(ra):.3f}%  mean B {sum(rb)/len(rb):.3f}%")
    print(f"exact two-sided WMW P = {p:.6f}  (enumerated {tot} allocations; "
          f"minimum attainable {2.0/tot:.2e})")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
케이스 단위 부트스트랩: 두 결과 파일의 단조성 위반율 차이 유의성
(쌍이 케이스에서 파생되어 비독립이므로 케이스를 리샘플링)
사용법: python score_bootstrap.py A.jsonl B.jsonl [--n 2000] [--exclude-bmi]
"""
import json, sys, argparse, random
from itertools import combinations
from collections import defaultdict

SEV = {"정상A":0,"정상":0,"정상B":1,"복부비만":1,"질환의심":2}

def load(path, exclude_bmi=False):
    rows = [json.loads(l) for l in open(path,encoding='utf-8')]
    if exclude_bmi:
        rows = [r for r in rows if not r['ladder_id'].startswith('BMI')]
    return rows

def viol_rate(rows, case_ids=None):
    by = defaultdict(list)
    idx = {r['case_id']: r for r in rows}
    ids = case_ids if case_ids is not None else list(idx)
    for cid in ids:
        r = idx.get(cid)
        if r is None or r['prediction'] is None: continue
        by[r['ladder_id']].append((float(r['value']), SEV.get(r['prediction'])))
    v = t = 0
    for lid, pts in by.items():
        d = next(r['direction'] for r in rows if r['ladder_id']==lid)
        pts.sort()
        for (v1,s1),(v2,s2) in combinations(pts,2):
            if s1 is None or s2 is None: continue
            t += 1
            if (s1 > s2) if d=='high' else (s1 < s2): v += 1
    return v, t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--n', type=int, default=2000)
    ap.add_argument('--exclude-bmi', action='store_true')
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()
    A = load(args.a, args.exclude_bmi); B = load(args.b, args.exclude_bmi)
    ids = sorted({r['case_id'] for r in A} & {r['case_id'] for r in B})
    va,ta = viol_rate(A, ids); vb,tb = viol_rate(B, ids)
    obs = va/ta - vb/tb
    random.seed(args.seed)
    diffs = []
    for _ in range(args.n):
        s = [random.choice(ids) for _ in ids]  # 케이스 복원추출 (중복 case는 1회 취급되므로 set 아님 주의)
        # 복원추출 시 중복 케이스는 가중 반영: 단순화를 위해 multiset → 케이스 목록 그대로 전달하되
        # viol_rate가 dict 조회라 중복이 무시됨 → 가중치 구현: 중복 횟수만큼 리스트 확장 불가.
        # 대안: 케이스 unique 서브샘플 부트스트랩(Bayesian bootstrap 근사) 대신 클러스터(사다리) 부트스트랩 사용.
        pass
    # 클러스터(사다리) 부트스트랩: 사다리 22개를 복원추출 — 쌍 비독립성의 실제 단위는 사다리
    lids = sorted({r['ladder_id'] for r in A})
    Ai = defaultdict(list); Bi = defaultdict(list)
    for r in A: Ai[r['ladder_id']].append(r)
    for r in B: Bi[r['ladder_id']].append(r)
    def rate_from(groups, sample):
        v=t=0
        for lid in sample:
            rows = groups[lid]
            d = rows[0]['direction']
            pts = sorted((float(r['value']), SEV.get(r['prediction'])) for r in rows if r['prediction'])
            for (v1,s1),(v2,s2) in combinations(pts,2):
                if s1 is None or s2 is None: continue
                t += 1
                if (s1>s2) if d=='high' else (s1<s2): v += 1
        return v/t if t else 0
    diffs=[]
    for _ in range(args.n):
        s = [random.choice(lids) for _ in lids]
        diffs.append(rate_from(Ai,s) - rate_from(Bi,s))
    diffs.sort()
    lo, hi = diffs[int(0.025*args.n)], diffs[int(0.975*args.n)]
    p = 2*min(sum(d<=0 for d in diffs), sum(d>=0 for d in diffs))/args.n
    tag = " (BMI 제외)" if args.exclude_bmi else ""
    print(f"A={args.a}: {va}/{ta} = {100*va/ta:.2f}%")
    print(f"B={args.b}: {vb}/{tb} = {100*vb/tb:.2f}%")
    print(f"차이{tag}: {100*obs:+.2f}%p, 클러스터(사다리) 부트스트랩 95% CI [{100*lo:+.2f}, {100*hi:+.2f}]%p, p≈{p:.3f}")

if __name__ == '__main__':
    main()

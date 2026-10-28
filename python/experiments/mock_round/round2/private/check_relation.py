import gzip, json, sys, statistics as st
def wm(b):
    if not b["bid"] or not b["ask"]: return None
    return (max(b["bid"], key=lambda l: l[1])[0] + max(b["ask"], key=lambda l: l[1])[0]) / 2
for path in sys.argv[1:]:
    rows = [json.loads(l) for l in gzip.open(path, "rt")]
    a = [wm(r["book"]["AURIC"]) for r in rows]; b = [wm(r["book"]["BRISA"]) for r in rows]; c = [wm(r["book"]["CORONA"]) for r in rows]
    v = [wm(r["book"]["VANTA"]) for r in rows]
    ok = [i for i in range(len(rows)) if None not in (a[i], b[i], c[i])]
    prem = [c[i] - a[i] - b[i] for i in ok]
    def corr(lag):
        xs, ys = [], []
        for i in range(10, len(rows)):
            j = i - lag
            if None in (c[i], c[i-1], a[j], a[j-1], b[j], b[j-1]): continue
            ys.append(c[i] - c[i-1]); xs.append(a[j] + b[j] - a[j-1] - b[j-1])
        return st.correlation(xs, ys)
    print(path.split("/")[-1], "premium mean %.1f sd %.1f" % (st.mean(prem), st.pstdev(prem)), " corr dC vs d(A+B) lag:", " ".join("%d:%.2f" % (k, corr(k)) for k in range(0, 7)), " VANTA first->last %+d" % (next(x for x in reversed(v) if x is not None) - next(x for x in v if x is not None)))

#!/usr/bin/env python3
"""Recompute Table 5 from public marginal counts or from an author-held Forms CSV (UTF-8)."""
import argparse, csv, statistics, sys
from collections import Counter
from pathlib import Path
from math import sqrt
from scipy.stats import t as student

BASE = Path(__file__).resolve().parent
def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
def write_csv(rows, stream):
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--counts", type=Path, default=BASE / "item_counts.csv")
    g.add_argument("--raw", type=Path, help="private original export, including a timestamp and all five named item columns")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    items = read_csv(BASE / "questionnaire.csv")[13:18]
    freq = {}
    if a.raw:
        records = read_csv(a.raw)
        if not records: raise ValueError("No response rows in the export")
        mapped = {k.strip():k for k in records[0]}
        # Ignore empty export padding, not participants with missing survey items.
        records = [r for r in records if str(r[mapped["Timestamp"]]).strip()]
        for item in items:
            key = mapped[item["wording"].strip()]
            counted = Counter()
            for r in records:
                x = (r[key] or "").strip()
                if x not in {"","1","2","3","4","5"}: raise ValueError("Not an integer Likert response: "+item["item"])
                counted[x] += 1
            freq[item["item"]] = ([counted[str(i)] for i in range(1,6)],counted[""])
    else:
        for r in read_csv(a.counts):
            k = r["item"]
            if k in freq: raise ValueError("Duplicate item "+k)
            freq[k] = ([int(r["raw_"+str(i)]) for i in range(1,6)],int(r["missing"]))
    if set(freq) != {x["item"] for x in items}: raise ValueError("Expected exactly Q14 through Q18")
    results = []
    for item in items:
        k = item["item"]; counts, missing = freq[k]
        if min(counts+[missing])<0 or sum(counts)+missing!=12: raise ValueError("Expected 12 entries for "+k)
        y = [(i if k == "Q18" else 6-i) for i, f in enumerate(counts,1) for _ in range(f)]
        n = len(y); mean = statistics.mean(y); sd = statistics.stdev(y)
        stat = (mean-3)/(sd/sqrt(n)); pv = float(student.sf(stat,n-1))
        results.append(dict(item=k,**{"raw_"+str(i):c for i,c in enumerate(counts,1)},missing=missing,n=n,
                            mean=f"{mean:.10f}",sample_sd=f"{sd:.10f}",df=n-1,t=f"{stat:.10f}",
                            p_greater=f"{pv:.10f}",p_bonferroni=f"{min(1,5*pv):.10f}"))
    if a.output:
        with a.output.open("w",newline="",encoding="utf-8") as f: write_csv(results,f)
    else: write_csv(results,sys.stdout)
if __name__=="__main__": main()

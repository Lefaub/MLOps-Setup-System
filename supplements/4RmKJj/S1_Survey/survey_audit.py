"""Reproduce descriptive public tables. An original Forms CSV stays with the author."""
import argparse
import csv
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
ITEMS = (7, 8, 13, 14, 15, 16, 17, 18)

def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def describe(item, c, missing):
    n = sum(c)
    if min(c + [missing]) < 0 or n + missing != 12 or not n:
        raise ValueError(f"Invalid denominator for {item}")
    y = [v for v, f in enumerate(c, 1) for _ in range(f)]
    q = [y[math.ceil(f*n)-1] for f in (.25, .50, .75)]
    return dict(item=item, **{f"raw_{j}":n0 for j,n0 in enumerate(c,1)},
                missing=missing, n=n, raw_q1=q[0], raw_median=q[1], raw_q3=q[2])

def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=rows[0],lineterminator="\n")
        w.writeheader(); w.writerows(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, help="Optional private original export (timestamp and Q1–Q21).")
    p.add_argument("--out", type=Path, required=True)
    a=p.parse_args(); a.out.mkdir(exist_ok=True,parents=True)
    if a.raw:
        source=read(a.raw); instrument=read(BASE/"questionnaire.csv")
        if not source: raise ValueError("Empty export")
        keys={k.strip(): k for k in source[0]}
        dated=[r for r in source if (r[keys["Timestamp"]] or "").strip()]
        if len(dated)!=12: raise ValueError("Expected 12 dated submissions")
        def values(i):
            key=keys[instrument[i-1]["wording"].strip()]
            return [(r[key] or "").strip() for r in dated]
        all_rows=[]
        for i in ITEMS:
            v=values(i)
            if any(x not in {"","1","2","3","4","5"} for x in v): raise ValueError(f"Non-integer Q{i}")
            all_rows.append(describe(f"Q{i}", [v.count(str(j)) for j in range(1,6)],v.count("")))
        completion=[dict(item=f"Q{i}",answered=12-values(i).count(""),missing=values(i).count("")) for i in range(1,22)]
        choices=["Yes","No","Maybe","Other","Missing"]
        q9=[{"yes":"Yes","no":"No","maybe":"Maybe","":"Missing"}.get(x.casefold(),"Other") for x in values(9)]
        interest=[dict(response=k,count=q9.count(k)) for k in choices]
    else:
        all_rows=[]
        for r in read(BASE/"all_likert_counts.csv"):
            row=describe(r["item"],[int(r[f"raw_{j}"]) for j in range(1,6)],int(r["missing"]))
            if {k:str(v) for k,v in row.items()}!=r: raise ValueError("Quartile/count mismatch: "+r["item"])
            all_rows.append(row)
        completion=read(BASE/"item_completion.csv"); interest=read(BASE/"testing_interest.csv")
    if [r["item"] for r in all_rows]!=[f"Q{i}" for i in ITEMS]: raise ValueError("Wrong item list")
    if [r["item"] for r in completion]!=[f"Q{i}" for i in range(1,22)]: raise ValueError("Wrong completion list")
    if any(min(int(r["answered"]),int(r["missing"]))<0 or int(r["answered"])+int(r["missing"])!=12 for r in completion):raise ValueError("Invalid completion")
    for r in all_rows:
        if int(completion[int(r["item"][1:])-1]["missing"])!=r["missing"]:raise ValueError(r["item"])
    if [c["response"] for c in interest]!=["Yes","No","Maybe","Other","Missing"] or sum(int(c["count"]) for c in interest)!=12 or int(interest[-1]["count"])!=int(completion[8]["missing"]): raise ValueError("Invalid Q9 counts")
    expected=read(BASE/"item_counts.csv")
    for r,s in zip(all_rows[3:],expected,strict=True):
        if any(str(r[k])!=v for k,v in s.items()): raise ValueError("Table 5 source differs: "+r["item"])
    for name,rows in (("all_likert_counts.csv",all_rows),("item_completion.csv",completion),("testing_interest.csv",interest)):write(a.out/name,rows)

if __name__=="__main__": main()

"""Two-sided exact sign analysis, ordinal quantiles and optional distribution plot."""
import argparse, csv, math
from pathlib import Path
from scipy.stats import binomtest
BASE=Path(__file__).resolve().parent
NAMES=["Error reduction","Expertise reduction","Setup-time reduction","Scalability","Integration difficulty"]
def analyze(src):
    with src.open(newline="",encoding="utf8") as f: raw=list(csv.DictReader(f))
    if [r["item"] for r in raw]!=["Q14","Q15","Q16","Q17","Q18"]: raise ValueError("Expected Q14–Q18 in order")
    out=[]
    for r in raw:
        k=r['item']; c=[int(r[f'raw_{i}']) for i in range(1,6)]
        missing=int(r['missing'])
        if min(c+[missing])<0 or sum(c)+missing!=12: raise ValueError(k)
        if k!='Q18': c.reverse()
        y=[i for i,count in enumerate(c,1) for _ in range(count)]
        lo,tie,hi=sum(c[:2]),c[2],sum(c[3:]); n=lo+hi
        q=[y[math.ceil(f*len(y))-1] for f in [.25,.5,.75]]
        if n:
            t=binomtest(hi,n,0.5,alternative="two-sided")
            ci=t.proportion_ci(.95,method="exact")
            sign=[f'{x:.10f}' for x in (t.statistic,ci.low,ci.high,t.pvalue,min(1,5*t.pvalue))]
        else: sign=['']*5
        out.append(dict(item=k,**{f'analysis_{i}':v for i,v in enumerate(c,1)},missing=missing,n=len(y),
                        q1=q[0],median=q[1],q3=q[2],below=lo,neutral=tie,above=hi,
                        **dict(zip(['share_above_nonneutral','exact95_low','exact95_high','p_exact_two_sided','p_bonferroni'],sign))))
    return out
def plot(rows,path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    fig,ax=plt.subplots(figsize=(9.4,2.95))
    palette=['#9B4325','#D89672','#C9CED3','#89B7D3','#246182']
    for i,r in enumerate(rows):
        values=[100*r[f'analysis_{j}']/r['n'] for j in range(1,6)]
        begin=-(sum(values[:2])+values[2]/2)
        for j,w in enumerate(values):
            ax.barh(i,w,left=begin,height=.65,color=palette[j],label=str(j+1) if not i else None,edgecolor="white",linewidth=.6)
            if w>7:
                ax.text(begin+w/2,i,str(r[f'analysis_{j+1}']),ha="center",va="center",fontsize=8,
                        color="white" if j in {0,4} else "#1A2631")
            begin+=w
        ax.text(102,i,f"n={r['n']}",va='center',fontsize=8)
    ax.set_xlim(-101,113);ax.set_xticks([-100,-75,-50,-25,0,25,50,75,100])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:f"{abs(int(x))}%"))
    ax.set_yticks(range(len(rows)),[f"{r['item']}  {name}" for r,name in zip(rows,NAMES)])
    ax.invert_yaxis()
    ax.axvline(0,color='#47596A',lw=.65,zorder=0)
    ax.set_xlabel('Percentage of nonmissing responses (numbers inside segments are counts)',fontsize=8)
    ax.tick_params(axis='both',length=0,labelsize=8)
    ax.spines[:].set_visible(False)
    ax.legend(ncol=5,loc="lower center",bbox_to_anchor=(.52,1.02),frameon=False,fontsize=8,title="Score (analysis direction)",title_fontsize=8)
    fig.tight_layout(pad=.5)
    fig.savefig(path, metadata={'Title':'Respondent distributions for five practitioner ratings','CreationDate':None})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--counts',type=Path,default=BASE/'item_counts.csv')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--plot',type=Path);a=p.parse_args()
    rows=analyze(a.counts)
    with a.output.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    if a.plot:plot(rows,a.plot)
if __name__=='__main__': main()

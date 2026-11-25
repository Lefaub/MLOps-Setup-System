"""Audit the full Boolean projection of the deployed JSON rules; no platform code is run."""
import argparse,collections,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
def sat(clauses):
    if not clauses:return True
    if any(not c for c in clauses):return False
    unit=next((c[0] for c in clauses if len(c)==1),None)
    def branch(lit):
        return sat([tuple(x for x in c if x!=-lit) for c in clauses if lit not in c])
    if unit is not None:return branch(unit)
    pivot=min(clauses,key=len)[0]
    return branch(pivot) or branch(-pivot)
def obj(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            duplicates.append(dict(key=k,discarded=result[k],effective=v))
        result[k]=v
    return result
duplicates=[]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--snapshot',choices=['paper','followup'],default='paper',
                   help='Verify against the original paper model or the separate fixed model.')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    model=(a.repo/'feature_model.fm').read_bytes()
    h=hashlib.sha256(model).hexdigest()
    expected=(json.loads((BASE/'input_sha256.json').read_text())['feature_model.fm'] if a.snapshot=='paper'
              else '8e5147c4a40fc3120cd371c750256ef7f280eeaaeaf5ed5983e6c8172b4a6328')
    if h!=expected:raise ValueError("Wrong model snapshot")
    F=json.loads(model,object_pairs_hook=obj)
    all_fields={f['name']:f for f in F if 'name' in f}
    names=sorted(k for k,v in all_fields.items() if v['type']=='checkbox')
    numbers={v:i for i,v in enumerate(names,1)}; groups=collections.defaultdict(list); omitted=[]
    for field,f in all_fields.items():
        for rule,edges in [('requires',f.get('dependencies',{}).get('requires',[])),('excludes',f.get('constraints',{}).get('excludes',[]))]:
            for value in edges:
                if rule=='requires':
                    target,desired=value.split(':')
                    if desired not in {'true','false'}:raise ValueError(value)
                else:target,desired=value,'false'
                info=dict(field=field,rule=rule,target=target,target_value=desired)
                if field not in numbers or target not in numbers:
                    omitted.append(info);continue
                clause=tuple(sorted({-numbers[field],numbers[target]*(1 if desired=='true' else -1)}))
                groups[clause].append(info)
    clauses=sorted(groups)
    if not sat(clauses): raise ValueError("Unsatisfiable base: dead/false-optional results would be vacuous")
    dead=[n for n,i in numbers.items() if not sat(clauses+[(i,)])]
    false_optional=[n for n,i in numbers.items() if not sat(clauses+[(-i,)])]
    def clause_name(c):return [('+' if i>0 else '-')+names[abs(i)-1] for i in c]
    redundant=[clause_name(c) for c in clauses if not sat([d for d in clauses if d!=c]+[(-lit,) for lit in c])]
    # Verify known SAT/UNSAT controls and both complete projected configurations.
    assert sat([(1,2),(-1,2)]) and not sat([(1,),(-1,)])
    profiles={}
    for path in sorted((BASE/'profiles').glob('*.json')):
        cfg=json.loads(path.read_text())
        profiles[path.stem]=sat(clauses+[(i if cfg[n] else -i,) for n,i in numbers.items()])
    assert all(profiles.values()) and len(profiles)==2
    report=dict(model_sha256=h,named_fields=len(all_fields),boolean_features=len(names),satisfiable=True,dead_features=dead,
                false_optional_features_under_mandatory_root=false_optional,named_checkbox_constraint_declarations=sum(map(len,groups.values())),
                unique_clauses=len(clauses),duplicate_declarations=sum(len(items)-1 for items in groups.values()),
                redundant_unique_clauses=redundant,omitted_nonboolean_rules=omitted,
                duplicate_json_keys_last_entry_wins=duplicates,profile_satisfiability=profiles,
                clauses=[dict(literals=clause_name(c),declarations=groups[c]) for c in clauses])
    a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()

"""Check the supplied evidence without network/cluster access (Python 3 standard library)."""
import csv, hashlib, json
from pathlib import Path
S=Path(__file__).resolve().parent
E=S/'evidence/application-live'; F=S/'feature_followup'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(x,label):
    if not x:raise ValueError(label)
def checks(mapping,keys,label):require(set(mapping)==keys and all(v is True for v in mapping.values()),label)
def main():
    outer={'fresh_endpoint_binding','headless_application_path','kubernetes_service_rollout','profile_validation_and_generation'}
    inner={'application_evidence_storage_round_trip','feedback_capture','feedback_retraining','generated_storage_client_execution','gui_bypass_configuration','inference','model_registry_round_trip','model_training','storage_round_trip','xai'}
    live=read(E/'evidence.json');env=read(E/'environment.json');workflow=read(E/'workflow_attempts.json')
    for line in (E/'CHECKSUMS.sha256').read_text().splitlines():
        sha,name=line.split();require(digest(E/name)==sha,name)
    require(live['mode']=='execute' and live['commit']==env['generator_commit'],'mode or source')
    require(set(live['cases'])=={'time_series','visual_inspection'},'profile list')
    for k,v in live['cases'].items():
        require(v['status']=='application_smoke_pass' and v['application']['status']=='application_smoke_pass',k)
        checks(v['checks'],outer,k+' orchestration');checks(v['application']['checks'],inner,k+' application')
        require(digest(S/'profiles'/(k+'.json'))==v['profile_sha256'],k+' input')
    runs=workflow['runs'];require(len(runs)==len({r['run'] for r in runs})==5,'ledger size')
    for r in runs:
        require(r['generator_commit']==live['commit'],'run source')
        require(set(r['cases'])==set(live['cases']),'run cases')
        if r['workflow_conclusion']=='success':
            for k,v in r['cases'].items():
                require(v['status']=='application_smoke_pass',k)
                checks(v['orchestration_checks'],outer,k);checks(v['application_checks'],inner,k)
        else:require(r['workflow_conclusion']=='failure' and all(q['status']=='failed' for q in r['cases'].values()),'run failure')
    primary=[r for r in runs if r['run']==env['run']]
    require(len(primary)==1 and primary[0]['workflow_commit']==env['workflow_commit'],'primary workflow')
    require(env['image_digests']==live['images'] and env['cluster']['client']==live['kubernetes_version']['clientVersion']['gitVersion'] and env['cluster']['server']==live['kubernetes_version']['serverVersion']['gitVersion'],'environment')
    with (S/'evidence/artifact_sha256.csv').open(newline='') as fp:
        outputs={(r['profile'],r['path']):r['sha256'] for r in csv.DictReader(fp) if r['run']=='recorded_1'}
    examples=sorted((S/'examples').rglob('*.yml'));require(len(examples)==2,'example set')
    for f in examples:
        parts=f.relative_to(S/'examples').parts;require(digest(f)==outputs[(parts[0],'/'.join(parts[1:]))],str(f))
    sources=read(F/'source_blobs.json')
    for rec in sources['files']:
        b=(F/rec['path']).read_bytes()
        require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==rec['git_blob'],rec['path'])
    for where,model,n,failed in [('original',S/'evidence/feature_audit.json',26,5),('fixed',F/'boolean_fixed.json',27,0)]:
        a=read(model)
        require(a['model_sha256']==digest(F/where/'feature_model.fm') and a['unique_clauses']==n,'Boolean snapshot')
        require(a['satisfiable'] and not a['dead_features'] and not a['false_optional_features_under_mandatory_root'] and not a['redundant_unique_clauses'] and all(a['profile_satisfiability'].values()),'Boolean audit')
        require(json.loads((F/('node_'+where+'.txt')).read_text().splitlines()[-1])=={'checks':8,'failed':failed},'Node record')
    ci=read(F/'ci_result.json');require(ci['workflow_sha']==sources['ci_commit'] and ci['conclusion']=='success' and ci['result']=={'checks':8,'failed':0},'CI record')
    print('PASS: original run, two profile hashes, all 4+10 checks per profile, five workflow attempts, two generated examples, original/fixed feature evidence.')
if __name__=='__main__':main()

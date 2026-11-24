#!/usr/bin/env python3
"""Offline rehearsal of artifact generation at the pinned source revision. Does not deploy or run artifacts."""
import ast, argparse, contextlib, csv, hashlib, importlib.metadata, importlib.util, io, json, os, platform, re, shutil, sys, tempfile
from pathlib import Path
import yaml
BASE=Path(__file__).resolve().parent
COMMIT="01209591e1d020dafc388a9b77b6985122308d6b"
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def check(test,message):
    if not test: raise RuntimeError(message)
def rules(fields,conf):
    errors=[]; named={f['name']:f for f in fields if 'name' in f}
    if set(conf)!=set(named): return ['incomplete or unknown field names']
    for name,f in named.items():
        v=conf[name]
        if f['type']=='checkbox' and type(v) is not bool: errors.append(name+': not boolean')
        if f['type']=='dropdown' and v not in f['options']: errors.append(name+': invalid option')
        if f['type']=='text' and not isinstance(v,str): errors.append(name+': invalid text')
        if not v: continue
        for dependency in f.get('dependencies',{}).get('requires',[]):
            key,expected=dependency.split(':')
            if str(conf[key]).lower()!=expected: errors.append(name+' requires '+key)
        for other in f.get('constraints',{}).get('excludes',[]):
            if conf[other]: errors.append(name+' excludes '+other)
    return errors
@contextlib.contextmanager
def working_directory(p):
    old=Path.cwd(); os.chdir(p)
    try: yield
    finally: os.chdir(old)
def run(repo,name,conf,fields,alt):
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        for f in ['code_templates.json','ml_pipeline_templates.json','kubernetes_resources.txt']:
            shutil.copyfile(repo/f,root/f)
        inv=root/'kubernetes_resources.txt'; source=inv.read_text()
        pattern=r'(?m)(^Service Name: minio\n\s*Namespace:[^\n]*\n\s*Cluster IP: )([0-9.]+)'
        match=re.search(pattern,source);check(match,'MinIO service absent from input')
        addr='192.0.2.41' if alt else match.group(2)
        if alt:
            check(addr!=match.group(2),'Fixture needs a distinct test IP')
            inv.write_text(re.sub(pattern,lambda m:m.group(1)+addr,source,count=1))
        modspec=importlib.util.spec_from_file_location('revision_generator',repo/'script_generation.py')
        gen=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(gen)
        def listing():
            return {p.relative_to(root).as_posix():digest(p) for p in root.rglob('*') if p.is_file() and p.parent!=root}
        with working_directory(root),contextlib.redirect_stdout(io.StringIO()):
            gen.script_generation('code_templates.json',fields,json.dumps(conf)); one=listing()
            gen.script_generation('ml_pipeline_templates.json',fields,json.dumps(conf)); two=listing()
        check(all(two.get(k)==v for k,v in one.items()),'Pipeline generator overwrote a platform output')
        new={k:v for k,v in two.items() if k not in one}
        for key in ['data_repository','monitoring','model_registry']:
            f=f'src/kubernetes/{key}/deployment.yml'
            check(f in one and 'kind:' in (root/f).read_text(),'Missing deployment manifest: '+key)
        img=name=='visual_inspection'
        for key in ['incremental_explanatory_training','xai_serving']:
            check((f'src/kubernetes/{key}/deployment.yml' in one)==img,'Unexpected platform variant: '+key)
        code=(root/'python/data_repository/main.py').read_text()
        check(re.search(r'(?m)^minio_service_1_ip = "'+re.escape(addr)+r':\d+"',code),'Endpoint not bound')
        check(re.search(r'(?m)^MINIO_ENDPOINT = minio_service_1_ip\b',code),'Endpoint not referenced')
        check(('monthly_hourly_load_values_2022_DE.csv' in code)==(not img),'Wrong time-series branch')
        check(('BUCKET_NAME = "image-data"' in code)==img,'Wrong image branch')
        check(('python/xai_serving/main.py' in new)==img,'Wrong pipeline artifact selection')
        diagnostics={"manifest_files":0,"full_yaml_documents":0,"empty_or_comment_only":[],"invalid_yaml":[],"invalid_pipeline_python":[],"nonempty_python_parsed":0}
        for path in sorted(two):
            body=(root/path).read_text()
            code_lines=[l for l in body.splitlines() if l.strip() and not l.lstrip().startswith("#")]
            if not code_lines: diagnostics["empty_or_comment_only"].append(path)
            if path.endswith((".yml",".yaml")):
                diagnostics["manifest_files"]+=1
                try:
                    docs=[d for d in yaml.safe_load_all(body) if d is not None]
                    diagnostics["full_yaml_documents"]+=sum(isinstance(d,dict) and "kind" in d and "apiVersion" in d for d in docs)
                except yaml.YAMLError:
                    diagnostics["invalid_yaml"].append(path)
            if path in new and path.endswith(".py") and code_lines:
                try: ast.parse(body); diagnostics["nonempty_python_parsed"]+=1
                except SyntaxError as exc: diagnostics["invalid_pipeline_python"].append({"path":path,"line":exc.lineno})
        return one,new,diagnostics,digest(inv),len(re.findall(r'(?m)^Service Name:',source)),len(re.findall(r'(?m)^Pod Name:',source))
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--repo',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    opts=a.parse_args();repo=opts.repo.resolve();out=opts.out.resolve();out.mkdir(parents=True,exist_ok=True)
    hashes=json.loads((BASE/'input_sha256.json').read_text())
    for n,h in hashes.items(): check(digest(repo/n)==h,'Input differs from pinned release: '+n)
    fields=json.loads((repo/'feature_model.fm').read_text())
    manifest=[];reports=[]
    for name in ('time_series','visual_inspection'):
        profile=BASE/'profiles'/f'{name}.json';conf=json.loads(profile.read_text())
        check(not rules(fields,conf),'Invalid input profile')
        check(any('requires' in x for x in rules(fields,{**conf,'model_selection_activation':False})),'Missing dependency control')
        check(any('excludes' in x for x in rules(fields,{**conf,'gpu_cluster_activation':True})),'Missing exclusion control')
        snapshots=[]
        for tag,alt in [('recorded_1',False),('recorded_2',False),('changed_address',True)]:
            p,g,diags,h,ns,np=run(repo,name,conf,fields,alt)
            snapshots.append((p,g))
            for stage,files in [('platform',p),('pipeline',g)]:
                manifest.extend([dict(profile=name,run=tag,stage=stage,path=k,sha256=v) for k,v in sorted(files.items())])
            reports.append(dict(profile=name,profile_sha256=digest(profile),run=tag,inventory_sha256=h,
                                platform_files=len(p),pipeline_files=len(g),static_inspection=diags,profile_rules='pass',negative_controls='pass',
                                selected_manifests='pass',scenario_branch='pass',endpoint_binding='pass',endpoint_consumer='pass'))
        check(snapshots[0]==snapshots[1],'Repeated generation differed')
        check(snapshots[0][1]['python/data_repository/main.py']!=snapshots[2][1]['python/data_repository/main.py'],'Endpoint perturbation had no effect')
    with (out/'artifact_sha256.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['profile','run','stage','path','sha256'],lineterminator='\n');w.writeheader();w.writerows(manifest)
    info=dict(commit=COMMIT,method='offline; no generated code executed; no cluster contact',python=platform.python_version(),
              jinja2=importlib.metadata.version('Jinja2'),markupsafe=importlib.metadata.version('MarkupSafe'),
              pyyaml=importlib.metadata.version('PyYAML'),system=platform.system(),machine=platform.machine(),services_in_archive=ns,pods_in_archive=np,
              live_cluster_runs=0,profile_input_fields=len(conf),byte_identical_baseline_repeats=True,runs=reports)
    (out/'runs.json').write_text(json.dumps(info,indent=2)+'\n')
    print('PASS: two profiles, four baseline runs, two address perturbations; zero live-cluster runs.')
if __name__=='__main__': main()

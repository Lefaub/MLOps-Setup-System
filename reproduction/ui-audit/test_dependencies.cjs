// Run the renderer's JavaScript against a minimal offline DOM adapter.
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {resolve} = require('node:path');
const repo = resolve(process.argv[2] || resolve(__dirname, '../..'));
const python = "import json, sys; sys.path.insert(0, sys.argv[1]); import html_generation as h; print(h.generate_html(json.load(open(sys.argv[1]+'/feature_model.fm'))))";
const html = execFileSync('python3',['-B','-c',python,repo],{encoding:'utf8'});
const script = html.match(/<script>([\s\S]+?)<\/script>/)[1];
const model = html.match(/<script id="form-data" type="application\/json">([\s\S]+?)<\/script>/)[1];
const fields = JSON.parse(model);
function state(selection) {
  const elems = new Map(fields.filter(f=>f.name).map(f=>[f.name,{
    type:f.type, checked:selection.includes(f.name), disabled:false, value:'',
    classList:{add(){},remove(){}}
  }]));
  const document = {
    getElementById(id){return id==='form-data'?{textContent:model}:(elems.get(id)||null);},
    querySelector(){return {style:{}};}
  };
  const window = {addEventListener(){}};
  const context = vm.createContext({document,window});
  vm.runInContext(script,context);
  return {get:key=>elems.get(key), update:()=>context.updateDependencies()};
}
const guided='user_guided_model_selection_activation', stream='data_streaming_activation', mod='model_selection_activation';
const cpu='cpu_cluster_activation',gpu='gpu_cluster_activation';
let count=0, failures=0;
function test(label, selections, callback) {
  count++;
  try {
    const x=state(selections); x.update(); callback(x);
    console.log('PASS '+label);
  } catch (e) { failures++; console.log('FAIL '+label+': '+e.message.split('\n')[0]); }
}
test('streaming alone must not enable guided selection',[stream,guided],({get})=>{
  assert.equal(get(guided).disabled,true); assert.equal(get(guided).checked,false);
});
test('model selection alone insufficient',[mod],({get})=>assert.equal(get(guided).disabled,true));
test('both prerequisites enable guided selection',[mod,stream],({get})=>assert.equal(get(guided).disabled,false));
test('CPU excludes GPU',[cpu],({get})=>assert.equal(get(gpu).disabled,true));
test('GPU excludes CPU',[gpu],({get})=>assert.equal(get(cpu).disabled,true));
test('no hardware selected allows either',[],({get})=>{
  assert.equal(get(cpu).disabled,false); assert.equal(get(gpu).disabled,false);
});
test('removing a selection releases the exclusion',[cpu],({get,update})=>{
  assert.equal(get(gpu).disabled,true);
  get(cpu).checked=false; update(); assert.equal(get(gpu).disabled,false);
});
test('conflicting restored state becomes a single selection',[cpu,gpu],({get,update})=>{
  assert.equal(Number(get(cpu).checked)+Number(get(gpu).checked),1);
  const selected=get(cpu).checked?cpu:gpu, other=selected===cpu?gpu:cpu;
  assert.equal(get(other).disabled,true);
  update(); assert.equal(get(other).disabled,true);
});
console.log(JSON.stringify({checks:count,failed:failures}));
process.exitCode=failures?1:0;

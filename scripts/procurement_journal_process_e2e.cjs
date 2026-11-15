/* Execute the actual mobile journal across two Node processes with a file storage adapter.
   This validates restart durability, not a physical SecureStore/Android implementation. */
const fs=require('node:fs'),path=require('node:path');
const ts=require('../apps/staff/node_modules/typescript');
const [fixturePath,phase]=process.argv.slice(2);
const fixture=JSON.parse(fs.readFileSync(fixturePath,'utf8'));
if(process.env.ALLOW_PROCUREMENT_RECOVERY_TEST_WRITES!=='1'||!['127.0.0.1','localhost'].includes(new URL(fixture.base).hostname))throw Error('Disposable localhost opt-in required');
const journalPath=fixturePath+'.journal';
const records=()=>fs.existsSync(journalPath)?JSON.parse(fs.readFileSync(journalPath,'utf8')):{};
const storage={getDurableItem:async k=>records()[k]??null,
 setDurableItem:async(k,v)=>{const r=records();r[k]=v;fs.writeFileSync(journalPath,JSON.stringify(r),{mode:0o600});},
 removeDurableItem:async k=>{const r=records();delete r[k];fs.writeFileSync(journalPath,JSON.stringify(r),{mode:0o600});}};
const cache=new Map();
function load(filename){
 if(cache.has(filename))return cache.get(filename);
 const module={exports:{}};cache.set(filename,module.exports);
 const code=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const localRequire=name=>name==='react-native'?{Platform:{OS:'ios'}}:name==='./storage'?storage:
  name.startsWith('.')?load(path.resolve(path.dirname(filename),name+'.ts')):require(name);
 new Function('require','module','exports',code)(localRequire,module,module.exports);return module.exports;
}
const {executeProcurement,readProcurement}=load(path.resolve('apps/mobile/src/lib/pendingProcurement.ts'));
(async()=>{
 const send=async op=>{
  const {kind,...body}=op;
  const url=kind==='REQUEST'?'/api/v1/kitchen/procurement/requests':'/api/v1/kitchen/procurement/requests/'+body.requestId+'/receive';
  const payload=kind==='REQUEST'?body:{receipt_id:body.receipt_id,quantity:body.quantity};
  const response=await fetch(fixture.base+url,{method:'POST',headers:{'content-type':'application/json',Cookie:fixture.cookie},body:JSON.stringify(payload)});
  const result=await response.json();if(response.status!==201)throw Error('Unexpected procurement response '+response.status);
  if(phase==='lost-ack')throw Error('Injected lost acknowledgement after confirmed server commit');
  return result;
 };
 if(phase==='lost-ack'){
  try{await executeProcurement(fixture.hotel,fixture.user,async()=>fixture.op,send);throw Error('Expected injected failure');}
  catch(e){if(!e.message.includes('Injected lost acknowledgement'))throw e;}
  if(JSON.stringify(await readProcurement(fixture.hotel,fixture.user))!==JSON.stringify(fixture.op))throw Error('Operation was not durably retained');
 }else if(phase==='replay'){
  await executeProcurement(fixture.hotel,fixture.user,null,send);
  if(await readProcurement(fixture.hotel,fixture.user)!==null)throw Error('Confirmed journal not cleared');
 }else throw Error('Unknown phase');
 console.log('PROCUREMENT JOURNAL PROCESS PASS: '+fixture.op.kind+' '+phase);
})().catch(e=>{console.error(e.message);process.exitCode=1;});

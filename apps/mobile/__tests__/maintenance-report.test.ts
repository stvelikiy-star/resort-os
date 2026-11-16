import {createRealApi} from '../src/api/realApi';
import {createDemoApi} from '../src/api/demoApi';
const task={id:'repair',type:'MAINTENANCE',status:'IN_PROGRESS',title:'Valve repair',room_id:'room',room_state:'TECH_BLOCK',assigned_to_id:'tech'};
const ack={ok:true,task_id:'repair',status:'DONE',room_state:'DIRTY',report_recorded:true};
const response=(body:unknown):Response=>({ok:true,status:200,json:async()=>body}) as Response;
test('uses the existing completion report endpoint and exact repair DTO',async()=>{
 const calls:{url:string;init:RequestInit}[]=[];
 const api=createRealApi('https://hotel.example',jest.fn(async(url:RequestInfo|URL,init?:RequestInit)=>{
  calls.push({url:String(url),init:init!});
  if(init?.method==='POST')return response(ack);
  return response({items:[{...task,status:calls.length===1?'IN_PROGRESS':'DONE',room_state:calls.length===1?'TECH_BLOCK':'DIRTY'}]});
 }) as typeof fetch);
 await api.listTasks();expect(await api.completeMaintenance('repair',{summary:'  Valve replaced  '})).toMatchObject({status:'DONE',room_state:'DIRTY'});
 const sent=calls.filter(x=>x.init.method==='POST');expect(sent).toHaveLength(1);
 expect(sent[0].url).toBe('https://hotel.example/api/v1/ops/tasks/repair/complete-report');
 expect(JSON.parse(sent[0].init.body as string)).toEqual({summary:'Valve replaced',checklist:[],evidence_urls:[]});
 expect(calls.some(x=>x.init.method==='PATCH')).toBe(false);
});
test('confirmed report remains successful when readback loses connectivity; no repeated POST',async()=>{
 let reads=0,posts=0;
 const api=createRealApi('https://hotel.example',jest.fn(async(_url:RequestInfo|URL,init?:RequestInit)=>{
  if(init?.method==='POST'){posts++;return response(ack);}
  if(reads++)throw new TypeError('readback offline');return response({items:[task]});
 }) as typeof fetch);
 await api.listTasks();expect(await api.completeMaintenance('repair',{summary:'Valve replaced'})).toMatchObject({id:'repair',status:'DONE',room_state:'DIRTY'});
 expect(posts).toBe(1);
});
test('missing report proof, foreign ID, false clean room or wrong status are rejected',async()=>{
 for(const invalid of [{...ack,report_recorded:false},{...ack,task_id:'other'},{...ack,room_state:'CLEAN'},{...ack,status:'IN_PROGRESS'}]){
  const api=createRealApi('https://hotel.example',jest.fn(async()=>response(invalid)) as typeof fetch);
  await expect(api.completeMaintenance('repair',{summary:'Valve replaced'})).rejects.toMatchObject({code:'UNKNOWN'});
 }
});
test('blank and excessively long summaries are rejected before sending',async()=>{
 const transport=jest.fn(async()=>response(ack));const api=createRealApi('https://hotel.example',transport as typeof fetch);
 for(const summary of ['',' ','  ','x','x'.repeat(2001)])await expect(api.completeMaintenance('repair',{summary})).rejects.toMatchObject({code:'BAD_REQUEST'});
 expect(transport).not.toHaveBeenCalled();
});
test('demo technician report preserves repair-to-cleaning handoff and denies replay',async()=>{
 const api=createDemoApi('demo',0);await api.login('tech','demo');await api.claimTask('t4');
 expect(await api.completeMaintenance('t4',{summary:'AC repaired'})).toMatchObject({id:'t4',status:'DONE',room_state:'DIRTY'});
 await expect(api.completeMaintenance('t4',{summary:'Repeat'})).rejects.toMatchObject({code:'CONFLICT'});
 await api.login('maid','demo');expect((await api.listTasks()).some(t=>t.type==='HOUSEKEEPING'&&t.room_id==='r5')).toBe(true);
 await expect(api.completeMaintenance('t4',{summary:'Not technician'})).rejects.toMatchObject({code:'FORBIDDEN'});
});

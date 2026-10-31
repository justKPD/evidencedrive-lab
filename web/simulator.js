/* Independently implemented browser numerical adapter. Python reference lives in model.py. */
export const MODEL_VERSION='edrive-model-1';
const EPS=1e-10;
const BASE={duration_s:6,dt_s:0.02,initial_speed_mps:20,mass_kg:1600,friction_mu:0.9,max_decel_mps2:8,tau_a_s:0.12,tau_b_s:0.18,recovery_hold_s:0.25,topology:'independent',variant:'demo-v1',controller_revision:'arbitration-1',demand:[{time_s:0,value:0},{time_s:0.5,value:0.6},{time_s:5,value:0}],faults:[]};
export function defaults(){return structuredClone(BASE)}
const own=(x,k)=>Object.prototype.hasOwnProperty.call(x,k);
const clamp=x=>Math.max(0,Math.min(1,x));
const object=(x,name)=>{if(!x||typeof x!=='object'||Array.isArray(x))throw Error(name+' must be an object.');};
function number(x,name,min,max){if(typeof x!=='number'||!Number.isFinite(x)||x<min||x>max)throw Error(name+' must be finite in ['+min+', '+max+'].');return x;}
function known(x,keys,name){for(const k of Object.keys(x))if(!keys.includes(k))throw Error(name+': unknown field '+k);}
export function validateConfig(input={}){
 object(input,'Config');known(input,Object.keys(BASE),'Config');const c={...defaults(),...structuredClone(input)};
 for(const [k,lo,hi] of [['duration_s',.5,20],['dt_s',.005,.1],['initial_speed_mps',0,60],['mass_kg',100,5000],['friction_mu',.05,1.5],['max_decel_mps2',1,15],['tau_a_s',.01,2],['tau_b_s',.01,2],['recovery_hold_s',0,2]])number(c[k],k,lo,hi);
 const n=c.duration_s/c.dt_s;if(Math.abs(n-Math.round(n))>1e-8||Math.round(n)+1>4001)throw Error('Duration must be a whole number of steps, at most4001samples.');
 if(!['independent','shared'].includes(c.topology))throw Error('Unknown power topology.');
 if(typeof c.variant!=='string'||! /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/.test(c.variant))throw Error('Variant needs a1–80character identifier.');
 if(c.controller_revision!=='arbitration-1')throw Error('Unsupported controller revision; only arbitration-1 is implemented.');
 if(!Array.isArray(c.demand)||!c.demand.length||c.demand.length>128)throw Error('Demand requires1–128knots.');
 let last=-1;
 for(const d of c.demand){object(d,'Demand knot');known(d,['time_s','value'],'Demand knot');number(d.time_s,'demand.time_s',0,c.duration_s);number(d.value,'demand.value',0,1);if(d.time_s<=last)throw Error('Demand times must strictly increase.');last=d.time_s;}
 if(c.demand[0].time_s!==0)throw Error('Demand must start at time0.');
 if(!Array.isArray(c.faults)||c.faults.length>64)throw Error('Fault list must contain at most64events.');
 const ids=new Set();
 for(const f of c.faults){object(f,'Fault');known(f,['id','kind','target','start_s','end_s','value'],'Fault');
  if(typeof f.id!=='string'||! /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/.test(f.id)||ids.has(f.id))throw Error('Fault IDs must be unique1–80character identifiers.');ids.add(f.id);
  if(!['power_loss','common_power_loss','signal_delay','signal_stuck','actuator_stuck'].includes(f.kind))throw Error('Unknown fault kind.');
  if(f.kind==='common_power_loss'?f.target!=='both':!['A','B'].includes(f.target))throw Error('Common power fault targets both; other faults target A or B.');
  number(f.start_s,'fault.start_s',0,c.duration_s);number(f.end_s,'fault.end_s',0,c.duration_s);if(f.end_s<=f.start_s)throw Error('Fault end must follow start.');
  if(f.kind==='signal_delay')number(f.value,'fault delay value',0,2);else if(f.kind==='signal_stuck')number(f.value,'fault stuck value',0,1);else if(own(f,'value'))throw Error('This fault kind does not accept a value.');
 }
 for(let i=0;i<c.faults.length;i++)for(let j=i+1;j<c.faults.length;j++){const a=c.faults[i],b=c.faults[j];if(a.kind===b.kind&&a.target===b.target&&Math.max(a.start_s,b.start_s)<Math.min(a.end_s,b.end_s))throw Error('Overlapping same-kind/target faults are ambiguous.');}
 return c;
}
function demandAt(c,t){if(t<0)return 0;let value=0;for(const d of c.demand){if(d.time_s>t)break;value=d.value;}return value;}
export function simulate(input={}){
 const c=validateConfig(input),N=Math.round(c.duration_s/c.dt_s),trace=[],events=[];
 const state={A:{p:0,power:true,ready:true,until:0,stuck:new Map()},B:{p:0,power:true,ready:true,until:0,stuck:new Map()}};let speed=c.initial_speed_mps,distance=0,prevActive=new Set();
 const emit=(t,type,target,message)=>events.push({t_s:t,type,target,message});
 for(let i=0;i<=N;i++){
  const t=Number((i*c.dt_s).toFixed(12)),active=c.faults.filter(f=>t>=f.start_s&&t<f.end_s).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),activeIds=new Set(active.map(f=>f.id));
  for(const f of active)if(!prevActive.has(f.id))emit(t,'fault_start',f.target,f.kind+' started: '+f.id);
  for(const id of prevActive)if(!activeIds.has(id)){const f=c.faults.find(x=>x.id===id);emit(t,'fault_end',f.target,f.kind+' ended: '+id);}
  const common=active.some(f=>f.kind==='common_power_loss'),busLoss=active.some(f=>f.kind==='power_loss');
  const requested=demandAt(c,t),command={},modes={};
  for(const k of ['A','B']){
   const s=state[k],loss=common||(c.topology==='shared'?busLoss:active.some(f=>f.kind==='power_loss'&&f.target===k));const powered=!loss;
   if(!powered&&s.power){emit(t,'power_lost',k,'Supply unavailable');s.p=0;s.ready=false;}
   if(powered&&!s.power){s.until=Number((t+c.recovery_hold_s).toFixed(12));emit(t,'power_restored',k,'Supply restored; recovery hold starts');}
   s.power=powered;
   if(!powered){s.p=0;s.ready=false;}else if(!s.ready&&t>=s.until){s.ready=true;emit(t,'recovery_complete',k,'Channel may track demand');}
   const local=active.filter(f=>f.target===k),delay=local.find(f=>f.kind==='signal_delay'),stuck=local.find(f=>f.kind==='signal_stuck');
   command[k]=stuck?stuck.value:demandAt(c,Number((t-(delay?delay.value:0)).toFixed(12)));
   for(const [id] of s.stuck)if(!activeIds.has(id))s.stuck.delete(id);
   for(const f of local.filter(x=>x.kind==='actuator_stuck'))if(!s.stuck.has(f.id))s.stuck.set(f.id,s.p);
   modes[k]=!powered?'power_lost':!s.ready?'recovering':s.stuck.size?'actuator_stuck':stuck?'signal_stuck':delay?'signal_delay':'tracking';
  }
  const effort=Math.min(Math.max(state.A.p,state.B.p)*c.max_decel_mps2,c.friction_mu*9.81);
  trace.push({t_s:t,demand:requested,requested_decel_mps2:requested*c.max_decel_mps2,pressure_a:state.A.p,pressure_b:state.B.p,command_a:command.A,command_b:command.B,power_a:state.A.power,power_b:state.B.power,ready_a:state.A.ready,ready_b:state.B.ready,recover_a_s:state.A.power?Math.max(0,state.A.until-t):0,recover_b_s:state.B.power?Math.max(0,state.B.until-t):0,mode_a:modes.A,mode_b:modes.B,brake_decel_mps2:effort,speed_mps:speed,distance_m:distance,force_n:c.mass_kg*effort,active_faults:[...activeIds],signal_disagreement:Math.abs(command.A-command.B)>.15+EPS});
  if(i<N){const nextSpeed=Math.max(0,speed-effort*c.dt_s);distance+=(speed+nextSpeed)*.5*c.dt_s;speed=nextSpeed;
   for(const [k,tau] of [['A',c.tau_a_s],['B',c.tau_b_s]]){const s=state[k];if(!s.power||!s.ready)s.p=0;else if(!s.stuck.size)s.p=clamp(command[k]+(s.p-command[k])*Math.exp(-c.dt_s/tau));}
  }
  prevActive=activeIds;
 }
 return {model_version:MODEL_VERSION,config:c,trace,events,summary:{duration_s:c.duration_s,final_speed_mps:speed,distance_m:distance,peak_decel_mps2:Math.max(...trace.map(r=>r.brake_decel_mps2)),min_speed_mps:Math.min(...trace.map(r=>r.speed_mps)),model_steps:trace.length}};
}
export async function runSimulation(input={}){
 const config=validateConfig(input);
 let pythonAvailable=false;
 try{
  const health=await fetch('/api/health',{signal:AbortSignal.timeout(1500)});if(!health.ok)throw Error('No local Python service');
  const h=await health.json();if(h.model_version!==MODEL_VERSION)throw Error('Unexpected backend');
  pythonAvailable=true;
 }catch{}
 if(!pythonAvailable){const out=simulate(config);return {...out,runtime:{engine:'Browser solver',fallback:true,reason:'Static preview or unavailable Python service. This execution is JavaScript; the independent Python model is tested separately.'}};}
 const response=await fetch('/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({config}),signal:AbortSignal.timeout(15000)});
 const out=await response.json();if(!response.ok)throw Error(out.detail||'Python execution refused');return {...out,runtime:{engine:'Python local service',fallback:false}};
}

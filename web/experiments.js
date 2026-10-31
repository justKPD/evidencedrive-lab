import {defaults,runSimulation} from './simulator.js';
import {createWorkspace,proposeContract,reviewContract,runContract} from './evidence.js';
const fault=(kind='power_loss',target='A',start_s=1.8,end_s=3.4,value)=>({id:'injected-1',kind,target,start_s,end_s,...(value===undefined?{}:{value})});
export function campaignCases(){return [
 {name:'Clean control',patch:{},source:'source-response-r1',clause:'tracking'},
 {name:'One supply lost · independent channels',patch:{faults:[fault()]},source:'source-response-r1',clause:'tracking'},
 {name:'Same fault · shared supply',patch:{topology:'shared',faults:[fault()]},source:'source-response-r1',clause:'tracking'},
 {name:'Common-cause loss despite separate supplies',patch:{faults:[fault('common_power_loss','both')]},source:'source-response-r1',clause:'tracking'},
 {name:'Residual braking after a stuck request',patch:{faults:[fault('signal_stuck','A',1.8,5.9,.9)]},source:'source-release-r1',clause:'release'},
 {name:'Delayed signal · healthy channel still responds',patch:{faults:[fault('signal_delay','B',.6,4.4,.8)]},source:'source-response-r1',clause:'tracking'},
 {name:'Long recovery after common supply loss',patch:{recovery_hold_s:1.1,faults:[fault('common_power_loss','both',1.8,2.3)]},source:'source-recovery-r1',clause:'recovery'},
 {name:'Low friction · source outside its declared range',patch:{friction_mu:.2},source:'source-response-r1',clause:'tracking'}
]}
export async function runFaultCampaign(options={}){
 const budget=typeof options==='number'?options:options.budget??6;
 if(!Number.isInteger(budget)||budget<1||budget>8)throw Error('The campaign budget must be an integer from1to8cases.');
 const rows=[];let total_model_steps=0;
 for(const fixture of campaignCases().slice(0,budget)){
  const config={...defaults(),...structuredClone(fixture.patch)},simulation=await runSimulation(config),workspace=createWorkspace();
  let contract=proposeContract(workspace,fixture.source,fixture.clause,simulation.config),result;
  if(contract.status==='PROPOSED'){
   contract=reviewContract(workspace,contract.id,true);result=runContract(workspace,contract.id,simulation);
  }else result={verdict:contract.status==='INCOMPATIBLE'?'NOT_APPLICABLE':'UNQUALIFIED',checked_count:0,findings:[],first_failure_s:null,reasons:contract.reasons,missing:contract.missing,scope:'The model ran for exploration, but the source did not supply an applicable reviewed test.'};
  total_model_steps+=simulation.trace.length;
  rows.push({name:fixture.name,config:simulation.config,result,summary:simulation.summary,simulation,contract,workspace,source:fixture.source,engine:simulation.runtime?.engine||'Browser solver'});
 }
 return {rows,summary:{cases:rows.length,passes:rows.filter(r=>r.result.verdict==='PASS').length,failures:rows.filter(r=>r.result.verdict==='FAIL').length,not_applicable:rows.filter(r=>r.result.verdict==='NOT_APPLICABLE').length,unqualified:rows.filter(r=>r.result.verdict==='UNQUALIFIED').length,total_model_steps},scope:'User-requested bounded suite of authored demonstration contracts. Every row executes the numerical model and checks the resulting trace. Cases are controlled examples, not sampled Bosch failures; no universal ranking or safety certification is inferred.'};
}

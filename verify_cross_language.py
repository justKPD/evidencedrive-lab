"""Compare independently implemented Python/browser adapters on declared fixtures."""
import copy,json,math,random,subprocess,sys,time,os,shutil
from pathlib import Path
import model
ROOT=Path(__file__).parent
NODE=os.environ.get('NODE_EXECUTABLE') or shutil.which('node') or r'C:\Program Files\nodejs\node.exe'
cases=[('clean',{}),('zero',{'demand':[{'time_s':0,'value':0}]}),('constant',{'demand':[{'time_s':0,'value':.4}]}),('friction_cap',{'friction_mu':.1}),('at_rest',{'initial_speed_mps':0}),('grid_future',{'demand':[{'time_s':0,'value':0},{'time_s':.50000000001,'value':.8}]})]
def fault(kind='power_loss',target='A',start=2,end=3,value=None):
    out={'id':'f1','kind':kind,'target':target,'start_s':start,'end_s':end}
    if value is not None:out['value']=value
    return out
for topology in ['independent','shared']:
    for kind,target,value in [('power_loss','A',None),('power_loss','B',None),('common_power_loss','both',None),('signal_delay','A',.2),('signal_stuck','A',.8),('actuator_stuck','A',None)]:cases.append((topology+'_'+kind+'_'+target,{'topology':topology,'faults':[fault(kind,target,1,4,value)]}))
cases += [('offgrid',{'faults':[fault(start=1.013,end=2.003)],'recovery_hold_s':.271}),('jam_and_power',{'faults':[fault('actuator_stuck','A',1,4),{**fault('power_loss','A',2,3),'id':'power'}]}),('future_fault',{'faults':[fault(start=.50000000001,end=.7)]})]
rng=random.Random(3102026)
for n in range(12):
    c={'dt_s':.01 if n%2 else .05,'initial_speed_mps':rng.uniform(3,40),'mass_kg':rng.uniform(500,3000),'friction_mu':rng.uniform(.1,1.2),'tau_a_s':rng.uniform(.05,.5),'tau_b_s':rng.uniform(.05,.5),'recovery_hold_s':rng.uniform(0,.6),'topology':'shared' if n%3==0 else 'independent','demand':[{'time_s':0,'value':0},{'time_s':.7,'value':rng.uniform(.2,.9)},{'time_s':4,'value':.15},{'time_s':5,'value':0}], 'faults':[fault(start=rng.uniform(1,2),end=rng.uniform(3,4))]}
    cases.append(('parameterized_'+str(n),c))

script="import {simulate} from './web/simulator.js';let raw='';for await(const c of process.stdin)raw+=c;const cases=JSON.parse(raw);console.log(JSON.stringify(cases.map(x=>simulate(x))));"
started=time.perf_counter()
reply=subprocess.run([NODE,'--input-type=module','-e',script],cwd=ROOT,input=json.dumps([c for _,c in cases]),capture_output=True,text=True,check=True)
browser=json.loads(reply.stdout)
rows=[]
for (name,config),js in zip(cases,browser):
    py=model.simulate(config);maximum=0.0
    assert len(js['trace'])==len(py['trace']),name
    for a,b in zip(js['trace'],py['trace']):
        assert set(a)==set(b),(name,set(a)^set(b))
        for key in a:
            if isinstance(b[key],(float,int)) and not isinstance(b[key],bool):
                err=abs(a[key]-b[key]);maximum=max(maximum,err)
                assert math.isclose(a[key],b[key],rel_tol=1e-10,abs_tol=1e-9),(name,key,a['t_s'],a[key],b[key])
            else:assert a[key]==b[key],(name,key,a['t_s'],a[key],b[key])
    assert [(e['t_s'],e['type'],e['target']) for e in py['events']]==[(e['t_s'],e['type'],e['target']) for e in js['events']],name+' event identity/order mismatch'
    rows.append({'case':name,'states':len(py['trace']),'maximum_absolute_difference':maximum,'passed':True})
out={'passed':True,'cases':len(rows),'sampled_states':sum(r['states'] for r in rows),'runtime_s':time.perf_counter()-started,'rows':rows,'scope':'Cross-language agreement on declared cases, not an independent physical validation or proof of Bosch behavior.'}
(ROOT/'verification/cross_language.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))

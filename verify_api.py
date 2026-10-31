import json,urllib.request,urllib.error
from pathlib import Path
BASE='http://127.0.0.1:8786';checks=[]
def request(path,payload=None):
 req=urllib.request.Request(BASE+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
def check(name,value):
 checks.append({'name':name,'passed':bool(value)})
 if not value:raise AssertionError(name)
h=request('/api/health');check('Actual local Python service',h['engine']=='Python local service' and h['model_version']=='edrive-model-1')
cfg=request('/api/defaults');cfg['topology']='shared';cfg['faults']=[{'id':'supply','kind':'power_loss','target':'A','start_s':2,'end_s':3}]
r=request('/api/simulate',{'config':cfg});row=next(x for x in r['trace'] if x['t_s']==2)
check('Shared supply loss affects both actual channels',row['power_a'] is False and row['power_b'] is False and row['brake_decel_mps2']==0)
cfg['topology']='independent';r=request('/api/simulate',{'config':cfg});row=next(x for x in r['trace'] if x['t_s']==2)
check('Separate supply preserves healthy channel',row['power_a'] is False and row['power_b'] is True and row['brake_decel_mps2']>4)
a=request('/api/assistant',{'text':'Explain without running tests','use_ai':False});check('Question does not execute numerical work',a['executed'] is False)
for name,payload,expected in [('Unsupported revision',{'config':{'controller_revision':'pretend-new'}},422),('Unknown field',{'config':{'secret_override':True}},422),('Oversized body',{'config':{'x':'a'*260000}},413)]:
 try:request('/api/simulate',payload);code=200
 except urllib.error.HTTPError as exc:code=exc.code
 check(name+' is refused',code==expected)
out={'passed':True,'checks':checks,'base':BASE}
Path('verification/api.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))

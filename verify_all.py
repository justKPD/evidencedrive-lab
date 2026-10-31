"""Reproduce numerical, contract, HTTP and real-browser checks; no provider spend."""
import datetime,hashlib,json,os,shutil,subprocess,sys,time,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
NODE=os.environ.get('NODE_EXECUTABLE') or shutil.which('node') or r'C:\Program Files\nodejs\node.exe'
steps=[
 ('python_unit',[sys.executable,'-m','unittest','tests_model','tests_service','-q']),
 ('evidence',[NODE,'tests_evidence.mjs']),
 ('cross_language',[sys.executable,'verify_cross_language.py']),
 ('http',[sys.executable,'verify_api.py']),
 ('browser_acceptance',[NODE,'verification/browser_acceptance.cjs']),
 ('browser_boundaries',[NODE,'verification/browser_boundaries.cjs']),
]
report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent declared model and workflow; not physical brake validation.','steps':[]}
for name,args in steps:
 started=time.perf_counter()
 out=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 report['steps'].append({'name':name,'passed':out.returncode==0,'elapsed_s':round(time.perf_counter()-started,3),'output':(out.stdout+out.stderr)[-12000:]})
 print(name+': '+('PASS' if out.returncode==0 else 'FAIL'),flush=True)
 if out.returncode:break
report['passed']=len(report['steps'])==len(steps) and all(x['passed'] for x in report['steps'])
suite=unittest.defaultTestLoader.loadTestsFromNames(['tests_model','tests_service'])
report['python_unit_tests']=suite.countTestCases()
for key,file in [('evidence_checks','evidence_tests.json'),('http_checks','api.json'),('browser_acceptance_checks','browser_acceptance.json'),('browser_boundary_checks','browser_boundaries.json')]:
 p=ROOT/'verification'/file
 if p.exists():
  data=json.loads(p.read_text(encoding='utf-8-sig'));report[key]=len(data.get('checks',[]))
p=ROOT/'verification/cross_language.json'
if p.exists():
 data=json.loads(p.read_text(encoding='utf-8-sig'));report['cross_language_cases']=data['cases'];report['cross_language_sampled_states']=data['sampled_states']
report['source_sha256']={}
for p in sorted([*ROOT.glob('*.py'),*ROOT.glob('*.mjs'),*ROOT.glob('requirements.txt'),*ROOT.glob('package.json'),*ROOT.glob('web/*.*'),*ROOT.glob('verification/*.cjs')]):
 if p.is_file():report['source_sha256'][p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/'verification/release_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['steps','source_sha256']},indent=2))
sys.exit(0 if report['passed'] else 1)

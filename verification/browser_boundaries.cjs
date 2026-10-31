let playwright;try{playwright=require('playwright')}catch{playwright=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/Drona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')}const {chromium}=playwright;
const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const checks=[],errors=[];let p;
 const check=(name,value)=>{checks.push({name,passed:!!value});if(!value)throw Error(name)};
 const idle=()=>p.waitForFunction(()=>window.__evidenceDrive&&!window.__evidenceDrive.state.busy);
 const click=async s=>{await p.click(s);await idle()};
 try{
  // Deliberately disable all API endpoints: this exercises the hosted static mode.
  p=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});p.on('pageerror',e=>errors.push(String(e)));
  await p.route('**/api/**',route=>route.fulfill({status:404,body:'No local service'}));
  await p.goto('http://127.0.0.1:8786/',{waitUntil:'networkidle'});await idle();
  check('Static execution is explicitly labeled Browser solver',await p.locator('#runtime-badge').innerText()==='Browser solver');
  check('Free-provider switch disabled in static mode',await p.isDisabled('#use-ai'));
  await click('[data-tab=knowledge]');await p.fill('#source-query','tracking response');await click('#source-search button');await click('[data-propose-source][data-clause=tracking]');
  await p.check('#contract-review');await click('#approve-contract');await click('#run-contract');
  const original=await p.evaluate(()=>({id:window.__evidenceDrive.state.result.id,config:window.__evidenceDrive.state.config,verdict:window.__evidenceDrive.state.result.verdict}));
  check('Static model executes a real reviewed check',original.verdict==='PASS');
  await click('[data-tab=proof]');await p.fill('#suite-budget','3');await click('#run-suite');await click('[data-inspect-suite="2"]');await click('[data-tab=knowledge]');
  const [d]=await Promise.all([p.waitForEvent('download'),p.click('#download-report')]);const report=fs.readFileSync(await d.path(),'utf8');
  check('Campaign readable report assesses its own workspace',report.includes('Current applicability: CURRENT')&&report.includes('Recorded verdict: FAIL'));
  await click('[data-tab=experiment]');await click('#return-investigation');
  check('Return restores original working run without new execution',await p.evaluate(old=>window.__evidenceDrive.state.result.id===old.id&&window.__evidenceDrive.state.result.verdict===old.verdict&&JSON.stringify(window.__evidenceDrive.state.config)===JSON.stringify(old.config)&&window.__evidenceDrive.state.workspace.runs.length===1,original));
  await click('[data-tab=knowledge]');await p.fill('#new-source-title','Own explicit tracking criterion');await p.locator('details:has(#copy-source-clause) summary').click();await click('#copy-source-clause');await p.check('#new-source-review');await click('#new-source-form button[type=submit]');
  check('Structured source UI produces a reviewable proposal',await p.evaluate(()=>window.__evidenceDrive.state.contract.status==='PROPOSED'&&window.__evidenceDrive.state.contract.source_snapshot.title==='Own explicit tracking criterion'));
  await click('[data-tab=experiment]');await p.locator('details:has(#config-json) summary').click();await p.fill('#config-json','{"unknown_field":42}');await click('#apply-config');
  check('Invalid custom input leaves last valid configuration intact',await p.evaluate(old=>JSON.stringify(window.__evidenceDrive.state.config)===JSON.stringify(old.config),original));
  check('Invalid custom input is visibly refused',!(await p.locator('#notice').isHidden())&&(await p.locator('#notice').innerText()).length>0);
  await p.close();
  // Optional-provider wiring and the lock against changing controls mid-computation.
  p=await browser.newPage({acceptDownloads:true});p.on('pageerror',e=>errors.push(String(e)));
  await p.goto('http://127.0.0.1:8786/',{waitUntil:'networkidle'});await idle();
  let providerRequest;
  await p.route('**/api/assistant',async route=>{providerRequest=route.request().postDataJSON();await route.fulfill({json:{provider_available:true,executed:false,message:'Check the recorded channels; this is a read-only explanation.',suggestion:'suggest_tests'}})});
  await p.check('#use-ai');await p.fill('#command-input','Explain the active fault without running a test');await click('#command-form button');
  check('Free explanation uses bounded summary and explicit opt-in',providerRequest?.use_ai===true&&Object.keys(providerRequest.context).length<=8&&!JSON.stringify(providerRequest).includes('api_key'));
  check('Provider suggestion creates no result or approved contract',await p.evaluate(()=>window.__evidenceDrive.state.workspace.runs.length===0&&window.__evidenceDrive.state.workspace.contracts.length===0));
  check('AI response is identified as a proposal',(await p.locator('#command-answer').innerText()).includes('AI explanation proposal'));
  await p.route('**/api/simulate',async route=>{await new Promise(r=>setTimeout(r,350));await route.continue()});
  await p.click('#run-experiment');await p.waitForFunction(()=>window.__evidenceDrive.state.busy);
  check('Editable inputs lock while a run is computing',await p.isDisabled('#topology')&&await p.isDisabled('#preset-select')&&await p.isDisabled('#add-fault'));
  await idle();check('Inputs unlock after successful execution',!await p.isDisabled('#topology'));
  await p.route('**/api/simulate',route=>route.fulfill({status:429,json:{detail:'Please wait before scheduling more work.'}}));
  const old=await p.evaluate(()=>window.__evidenceDrive.state.simulation);
  await click('#run-experiment');
  check('Python refusal is displayed instead of hidden fallback',(await p.locator('#notice').innerText()).includes('Please wait'));
  check('Refused execution retains previous valid trace',await p.evaluate(old=>JSON.stringify(window.__evidenceDrive.state.simulation)===JSON.stringify(old),old));
  check('No JavaScript errors in boundary scenarios',errors.length===0);
  fs.writeFileSync(path.join(__dirname,'browser_boundaries.json'),JSON.stringify({passed:true,checks,errors,provider:'UI routing tested with a mock response; not a live provider success claim.'},null,2));console.log(JSON.stringify({passed:true,checks:checks.length}));
 }catch(error){fs.writeFileSync(path.join(__dirname,'browser_boundaries.json'),JSON.stringify({passed:false,checks,errors,error:String(error.stack||error)},null,2));console.error(error);process.exitCode=1;}finally{await browser.close()}
})();

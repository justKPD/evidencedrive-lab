$projectRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPython=Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Create the local Python environment and install requirements.txt first.' }
try {
 $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8786/api/health' -TimeoutSec 2
 if ($health.model_version -eq 'edrive-model-1') { Write-Output 'EvidenceDrive ready: http://127.0.0.1:8786/'; exit }
 throw 'Port8786 belongs to another service; it was not changed.'
} catch { if ($_.Exception.Message -like '*another service*') { throw } }
Start-Process -FilePath $projectPython -ArgumentList 'app.py' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'server.log') -RedirectStandardError (Join-Path $projectRoot 'server.err.log')
for($attempt=0;$attempt -lt 20;$attempt++) {
 try { $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8786/api/health' -TimeoutSec 2; if($health.model_version -eq 'edrive-model-1'){Write-Output 'EvidenceDrive ready: http://127.0.0.1:8786/';exit} } catch {}
 Start-Sleep -Milliseconds 500
}
throw 'EvidenceDrive startup failed; inspect server.err.log.'

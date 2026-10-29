param(
    [ValidateSet('Development','Prebuilt')][string]$Mode='Development',
    [int]$ApiPort=8110,
    [int]$UiPort=5173,
    [string]$Workspace='',
    [switch]$Stop,
    [switch]$OpenBrowser
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime=Join-Path $repo 'tmp/studio-runtime'
$statePath=Join-Path $runtime 'processes.json'
function Stop-Owned($records) {
    foreach ($record in @($records) | Sort-Object depth -Descending) {
        $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)" -ErrorAction SilentlyContinue
        if ($process -and $process.CreationDate.ToUniversalTime().Ticks -eq ([datetime]$record.created).ToUniversalTime().Ticks) {
            Stop-Process -Id $record.pid -ErrorAction SilentlyContinue
        }
    }
}
function Descendants($roots) {
    $snapshot=@(Get-CimInstance Win32_Process)
    $queue=@($roots);$records=@();$depth=0
    while ($queue.Count -gt 0 -and $depth -lt 12) {
        $next=@()
        foreach ($id in $queue) {
            $process=$snapshot | Where-Object ProcessId -eq $id | Select-Object -First 1
            if ($process) {$records+=@{pid=$id;created=$process.CreationDate.ToUniversalTime().ToString('o');depth=$depth}}
            $next+=@($snapshot | Where-Object ParentProcessId -eq $id | Select-Object -ExpandProperty ProcessId)
        }
        $queue=$next;$depth++
    }
    return $records
}
if ($Stop) {
    if (Test-Path -LiteralPath $statePath) {
        $prior=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        $validRoots=@()
        foreach ($record in $prior.processes) {
            $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)" -ErrorAction SilentlyContinue
            if ($process -and $process.CreationDate.ToUniversalTime().Ticks -eq ([datetime]$record.created).ToUniversalTime().Ticks) {$validRoots+=@($record.pid)}
        }
        Stop-Owned @($prior.processes + @(Descendants $validRoots))
        for ($attempt=0;$attempt -lt 20;$attempt++) {
            if (-not @($validRoots | Where-Object {Get-Process -Id $_ -ErrorAction SilentlyContinue}).Count) {break}
            Start-Sleep -Milliseconds 200
        }
        Write-Host 'Da dung cac tien trinh do script khoi tao; khong dung dich vu khac.'
    } else {Write-Host 'Khong co phien do script quan ly.'}
    return
}
$python=Join-Path $repo '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {throw 'Thieu .venv. Tao venv va cai requirements.txt truoc.'}
& $python -c 'import fastapi,uvicorn,pymupdf,pytesseract,qdrant_client,portalocker' 2>$null
if ($LASTEXITCODE -ne 0) {throw 'Cai thu vien: .venv\Scripts\python -m pip install -r requirements.txt'}
if ($ApiPort -eq $UiPort -and $Mode -eq 'Development') {throw 'API va UI can hai cong khac nhau.'}
$ports=@($ApiPort);if ($Mode -eq 'Development') {$ports+=@($UiPort)}
foreach ($port in $ports) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Cong $port da co dich vu. Dung phien cu bang -Stop hoac chon cong khac."
    }
}
$node=Get-Command node -ErrorAction SilentlyContinue
if ($Mode -eq 'Development' -and (-not $node -or -not (Test-Path (Join-Path $repo 'frontend/node_modules/vite/bin/vite.js')))) {
    throw 'Can Node.js >=22.12 va frontend dependencies. Chay: cd frontend; npm ci'
}
if ($node -and $Mode -eq 'Development') {
    $version=[version](& $node.Source -p 'process.versions.node')
    if ($version -lt [version]'22.12.0') {throw 'Can Node.js >=22.12; khong tu thay Node tren may.'}
}
if ($Mode -eq 'Prebuilt' -and -not (Test-Path (Join-Path $repo 'frontend/dist/index.html'))) {
    throw 'Chua co frontend build. Chay: cd frontend; npm ci; npm run build'
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$tokenPath=Join-Path $runtime 'access-token.txt'
if (-not $env:STUDIO_API_TOKEN -or $env:STUDIO_API_TOKEN.Length -lt 16) {
    if (Test-Path -LiteralPath $tokenPath) {$env:STUDIO_API_TOKEN=(Get-Content -LiteralPath $tokenPath -Raw).Trim()}
    else {
        $bytes=New-Object byte[] 32
        $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create();$rng.GetBytes($bytes);$rng.Dispose()
        $env:STUDIO_API_TOKEN=[Convert]::ToBase64String($bytes)
        [IO.File]::WriteAllText($tokenPath,$env:STUDIO_API_TOKEN)
    }
} else {[IO.File]::WriteAllText($tokenPath,$env:STUDIO_API_TOKEN)}
if ($env:STUDIO_API_TOKEN.Length -lt 16) {throw 'Khoa truy cap khong hop le; kiem tra tep access-token.txt.'}
if (-not $Workspace) {$Workspace=Join-Path $repo 'studio_workspace/react-user'}
$env:STUDIO_WORKSPACE_DIR=[IO.Path]::GetFullPath($Workspace)
$env:OLLAMA_BASE_URL='http://127.0.0.1:11434'
$env:CORS_ORIGINS="http://127.0.0.1:$UiPort"
$env:STUDIO_API_TARGET="http://127.0.0.1:$ApiPort"
# Legacy compatibility routes use an isolated store, never the owner's old knowledgebase.
$env:QDRANT_PATH=Join-Path $runtime 'legacy-qdrant';$env:QDRANT_COLLECTION='studio_legacy_compat'
$env:UPLOAD_DIR=Join-Path $runtime 'legacy-uploads';$env:PROCESSED_DIR=Join-Path $runtime 'legacy-processed'
$env:CONVERSATION_DB=Join-Path $runtime 'legacy-conversations.sqlite3'
$env:FINANCIAL_CORPUS_DIR=Join-Path $runtime 'legacy-corpus'
$env:FINANCIAL_REGISTRY_DB=Join-Path $env:FINANCIAL_CORPUS_DIR 'registry.sqlite3'
$productSource=Join-Path $runtime 'sec/p7-isolated-review-product-20261028'
$productVectors=Join-Path $runtime 'sec/t3-p10-isolated-vectors-product-20261028'
if (-not $env:STUDIO_SEC_RESEARCH_ROOT -and -not $env:STUDIO_SEC_VECTOR_ROOT -and -not $env:TOPIC3_RESEARCH_ROOT -and
    (Test-Path (Join-Path $productSource 'frozen_v1/freeze.json')) -and (Test-Path (Join-Path $productVectors 'generation_manifest.json'))) {
    $env:STUDIO_SEC_RESEARCH_ROOT=$productSource;$env:TOPIC3_RESEARCH_ROOT=$productSource;$env:STUDIO_SEC_VECTOR_ROOT=$productVectors
}
foreach ($key in @('STUDIO_SEC_RESEARCH_ROOT','STUDIO_SEC_VECTOR_ROOT','TOPIC3_RESEARCH_ROOT')) {
    $value=[Environment]::GetEnvironmentVariable($key)
    if ($value -and -not (Test-Path -LiteralPath $value)) {throw "Thu muc $key khong ton tai. Khong tai SEC moi de thay the."}
}
$started=@()
try {
    try {$tags=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 4}
    catch {
        $ollama=Get-Command ollama -ErrorAction SilentlyContinue
        $ollamaExe=if ($ollama) {$ollama.Source} else {Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'}
        if (-not (Test-Path -LiteralPath $ollamaExe)) {throw 'Ollama chua chay/chua cai; script khong tu tai mo hinh.'}
        $process=Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -PassThru -WindowStyle Hidden
        $started+=@($process.Id)
        for ($attempt=0;$attempt -lt 30;$attempt++) {
            Start-Sleep -Seconds 1
            try {$tags=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2;break}catch{}
        }
    }
    $model=$tags.models | Where-Object name -eq 'nomic-embed-text:latest' | Select-Object -First 1
    if (-not $model -or $model.digest -ne '0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f') {
        throw 'Khong co dung Nomic digest da chap nhan. Khong tu tai/thay mo hinh hoac vector cu.'
    }
    $process=Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port',"$ApiPort") -WorkingDirectory $repo -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'api.out') -RedirectStandardError (Join-Path $runtime 'api.err')
    $started+=@($process.Id)
    $url="http://127.0.0.1:$ApiPort/app/"
    if ($Mode -eq 'Development') {
        $vite=Join-Path $repo 'frontend/node_modules/vite/bin/vite.js'
        $process=Start-Process -FilePath $node.Source -ArgumentList @("`"$vite`"",'--port',"$UiPort") -WorkingDirectory (Join-Path $repo 'frontend') -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'ui.out') -RedirectStandardError (Join-Path $runtime 'ui.err')
        $started+=@($process.Id);$url="http://127.0.0.1:$UiPort/"
    }
    foreach ($probe in @("http://127.0.0.1:$ApiPort/health",$url)) {
        $ready=$false
        for ($attempt=0;$attempt -lt 45;$attempt++) {
            Start-Sleep -Milliseconds 500
            try {if ((Invoke-WebRequest $probe -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) {$ready=$true;break}}catch{}
        }
        if (-not $ready) {throw "Dich vu chua san sang: $probe. Xem log tai $runtime"}
    }
    $owned=@(Descendants $started)
    @{processes=$owned;ui=$url;api="http://127.0.0.1:$ApiPort";workspace=$env:STUDIO_WORKSPACE_DIR} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding utf8
    $readiness=Invoke-RestMethod "http://127.0.0.1:$ApiPort/studio/readiness" -Headers @{Authorization="Bearer $env:STUDIO_API_TOKEN"}
    Write-Host "UI: $url"
    Write-Host "API: http://127.0.0.1:$ApiPort/docs"
    Write-Host "Khoa dang nhap cuc bo duoc luu tai: $tokenPath (khong chia se/cong khai tep nay)."
    Write-Host "PDF READY: $($readiness.workspace.ready_documents); OCR: $($readiness.ocr.status); SEC: $($readiness.sec.status)"
    Write-Host 'Dung dich vu cua phien nay: .\scripts\run_financial_studio.ps1 -Stop'
    if ($OpenBrowser) {Start-Process $url | Out-Null}
} catch {
    Stop-Owned @(Descendants $started)
    throw
}

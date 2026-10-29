param(
    [string]$Python = "",
    [int]$ApiPort = 8000,
    [int]$ResearchPort = 8767,
    [int]$UiPort = 8501,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $Python) {
    $localPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $localPython) { $Python = $localPython }
    elseif ($env:STUDIO_PYTHON) { $Python = $env:STUDIO_PYTHON }
    else { throw "Set STUDIO_PYTHON to the installed project Python, or create .venv." }
}
$Python = (Resolve-Path -LiteralPath $Python).Path
& $Python -c "import fastapi, streamlit, pymupdf, qdrant_client, requests" 2>$null
if ($LASTEXITCODE -ne 0) { throw "Install project dependencies with: python -m pip install -r requirements.txt" }
foreach ($key in @("STUDIO_SEC_RESEARCH_ROOT", "STUDIO_SEC_VECTOR_ROOT", "TOPIC3_RESEARCH_ROOT")) {
    $value = [Environment]::GetEnvironmentVariable($key)
    if (-not $value -or -not (Test-Path -LiteralPath $value)) { throw "Missing existing $key directory." }
}
if ($env:STUDIO_API_TOKEN.Length -lt 16 -or $env:TOPIC3_RESEARCH_API_TOKEN.Length -lt 16) {
    throw "Set distinct local STUDIO_API_TOKEN and TOPIC3_RESEARCH_API_TOKEN values (at least 16 characters)."
}
try { $ollamaTags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 }
catch {
    $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaCommand) { throw "Ollama is not running and is not installed in PATH." }
    Start-Process -FilePath $ollamaCommand.Source -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try { $ollamaTags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3; break }
        catch { }
    }
    if (-not $ollamaTags) { throw "Ollama did not become available within 30 seconds." }
}
$model = $ollamaTags.models | Where-Object { $_.name -eq "nomic-embed-text:latest" } | Select-Object -First 1
if (-not $model -or $model.digest -ne "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f") {
    throw "The accepted local nomic-embed-text:latest digest is unavailable; no model will be downloaded automatically."
}
if (-not $env:STUDIO_WORKSPACE_DIR) { $env:STUDIO_WORKSPACE_DIR = Join-Path $repoRoot "studio_workspace" }
if ((Test-Path -LiteralPath $env:STUDIO_WORKSPACE_DIR) -and
    (Get-ChildItem -LiteralPath $env:STUDIO_WORKSPACE_DIR -Force | Select-Object -First 1) -and
    -not (Test-Path -LiteralPath (Join-Path $env:STUDIO_WORKSPACE_DIR "ownership.json"))) {
    throw "Workspace is nonempty and lacks the product ownership marker."
}
$env:STUDIO_API_URL = "http://127.0.0.1:$ApiPort"
$env:TOPIC3_RESEARCH_API_URL = "http://127.0.0.1:$ResearchPort"
foreach ($port in @($ApiPort, $ResearchPort, $UiPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already listening; select unused ports."
    }
}
$logDir = Join-Path $env:TEMP "financial-intelligence-studio"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$services = @(
    @{ Name="api"; Arguments=@("-m","uvicorn","main:app","--host","127.0.0.1","--port",[string]$ApiPort) },
    @{ Name="research"; Arguments=@("-m","uvicorn","app.research_api:app","--host","127.0.0.1","--port",[string]$ResearchPort) },
    @{ Name="ui"; Arguments=@("-m","streamlit","run","streamlit_app.py","--server.address","127.0.0.1","--server.port",[string]$UiPort,"--server.headless","true") }
)
$started = @()
foreach ($service in $services) {
    $process = Start-Process -FilePath $Python -ArgumentList $service.Arguments -WorkingDirectory $repoRoot `
        -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir "$($service.Name).out") `
        -RedirectStandardError (Join-Path $logDir "$($service.Name).err")
    $started += @{ name=$service.Name; pid=$process.Id }
}
foreach ($probe in @(
    @{ Name="FastAPI"; Url="http://127.0.0.1:$ApiPort/studio/health" },
    @{ Name="Research API"; Url="http://127.0.0.1:$ResearchPort/research/v1/health" },
    @{ Name="Streamlit"; Url="http://127.0.0.1:$UiPort/_stcore/health" }
)) {
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $probe.Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "$($probe.Name) did not start. Inspect logs in $logDir." }
}
$running = @(
    @{ name="api"; port=$ApiPort },
    @{ name="research"; port=$ResearchPort },
    @{ name="ui"; port=$UiPort }
) | ForEach-Object {
    $connection = Get-NetTCPConnection -LocalPort $_.port -State Listen -ErrorAction Stop | Select-Object -First 1
    @{ name=$_.name; port=$_.port; pid=$connection.OwningProcess }
}
$running | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDir "processes.json") -Encoding utf8
Write-Host "Financial Intelligence Studio: http://127.0.0.1:$UiPort"
Write-Host "API: http://127.0.0.1:$ApiPort/health; logs: $logDir"
$processSummary = ($running | ForEach-Object { "$($_.name)=$($_.pid)" }) -join ', '
Write-Host "Processes: $processSummary"
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$UiPort" | Out-Null }

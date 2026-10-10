param(
    [switch]$DemoMode,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Reports = Join-Path $ProjectRoot "reports"
New-Item -ItemType Directory -Force -Path $Reports | Out-Null

function Test-HttpEndpoint([string]$Url, [int]$TimeoutSeconds = 2) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Không tìm thấy .venv tại $Python. Hãy tạo môi trường Python trước."
}

Push-Location $ProjectRoot
try {
    & $Python -c "import fastapi, streamlit, qdrant_client, pypdf, requests" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Thiếu dependency lõi. Chạy: .\.venv\Scripts\python.exe -m pip install -r requirements.txt" }

    if (-not (Test-HttpEndpoint "http://127.0.0.1:11434/api/tags" 3)) {
        $ollama = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollama) { throw "Không tìm thấy Ollama trong PATH." }
        Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 30; $i++) {
            if (Test-HttpEndpoint "http://127.0.0.1:11434/api/tags" 3) { break }
            Start-Sleep -Seconds 1
        }
    }
    if (-not (Test-HttpEndpoint "http://127.0.0.1:11434/api/tags" 3)) { throw "Ollama không khởi động được." }

    $models = (& ollama list 2>$null | Out-String)
    $envValues = @{}
    if (Test-Path -LiteralPath ".env") {
        Get-Content -LiteralPath ".env" | ForEach-Object {
            if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $envValues[$matches[1]] = $matches[2].Trim() }
        }
    }
    $requiredModels = @(
        $(if ($envValues["OLLAMA_MODEL"]) { $envValues["OLLAMA_MODEL"] } else { "qwen2.5:3b" }),
        $(if ($envValues["EMBEDDING_MODEL"]) { $envValues["EMBEDDING_MODEL"] } else { "nomic-embed-text" })
    )
    foreach ($required in $requiredModels) {
        if ($models -notmatch [regex]::Escape($required)) { throw "Thiếu Ollama model '$required'. Chạy: ollama pull $required" }
    }

    if ($DemoMode) { $env:GENAI_DEMO_MODE = "1" }

    if (-not (Test-HttpEndpoint "http://127.0.0.1:8000/health" 2)) {
        Start-Process -FilePath $Python -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000" `
            -WorkingDirectory $ProjectRoot -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $Reports "fastapi.stdout.log") `
            -RedirectStandardError (Join-Path $Reports "fastapi.stderr.log")
    }

    $backendReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-HttpEndpoint "http://127.0.0.1:8000/health" 2) { $backendReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $backendReady) { throw "FastAPI không sẵn sàng sau 30 giây. Xem reports\fastapi.stderr.log." }

    if (-not (Test-HttpEndpoint "http://127.0.0.1:8501" 2)) {
        Start-Process -FilePath $Python -ArgumentList "-m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501" `
            -WorkingDirectory $ProjectRoot -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $Reports "streamlit.stdout.log") `
            -RedirectStandardError (Join-Path $Reports "streamlit.stderr.log")
    }

    $uiReady = $false
    for ($i = 0; $i -lt 45; $i++) {
        if (Test-HttpEndpoint "http://127.0.0.1:8501" 2) { $uiReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $uiReady) { throw "Streamlit không sẵn sàng sau 45 giây. Xem reports\streamlit.stderr.log." }

    Write-Host "GenAI Learning Studio READY" -ForegroundColor Green
    Write-Host "UI:  http://127.0.0.1:8501"
    Write-Host "API: http://127.0.0.1:8000/docs"
    if ($DemoMode) { Write-Host "Demo Mode: dùng index và media thật đã lưu; không giả lập inference." -ForegroundColor Cyan }
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:8501" }
} finally {
    Pop-Location
}

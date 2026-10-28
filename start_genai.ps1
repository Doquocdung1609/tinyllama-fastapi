param(
    [switch]$DemoMode,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
if ($DemoMode) {
    Write-Warning 'The old GenAI DemoMode is retired. Starting Financial Intelligence Studio.'
}
& (Join-Path $PSScriptRoot 'scripts\start_financial_studio.ps1') -NoBrowser:$NoBrowser

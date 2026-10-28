# Compatibility entrypoint: React is now the default; Streamlit is explicit rollback only.
param([int]$ApiPort=8110,[int]$UiPort=5173,[int]$ResearchPort=8767,[switch]$Legacy,[switch]$NoBrowser)
if ($Legacy) {
    & "$PSScriptRoot/start_legacy_financial_studio.ps1" -ApiPort $ApiPort -UiPort $UiPort -ResearchPort $ResearchPort -NoBrowser:$NoBrowser
} else {
    & "$PSScriptRoot/run_financial_studio.ps1" -ApiPort $ApiPort -UiPort $UiPort -OpenBrowser:(-not $NoBrowser)
}

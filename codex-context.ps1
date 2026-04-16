param(
    [string]$WorkspaceRoot = "C:\Users\matt\OneDrive\Desktop\Data_Projects\DataCivicLab",
    [string]$OutDir = "generated-local",
    [string]$ConfigPath = "dataciviclab.config.yml"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $repoRoot ".venv314\Scripts\python.exe"
$agentContext = Join-Path $repoRoot ".venv314\Scripts\agent-context.exe"
$resolvedOutDir = Join-Path $repoRoot $OutDir
$resolvedConfig = Join-Path $repoRoot $ConfigPath

if (-not (Test-Path $python)) {
    throw "Python non trovato: $python"
}

if (-not (Test-Path $agentContext)) {
    throw "CLI non trovata: $agentContext"
}

if (-not (Test-Path $resolvedConfig)) {
    throw "Config non trovata: $resolvedConfig"
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:CURL_CA_BUNDLE = ""

Write-Host "Building agent context for Codex..." -ForegroundColor Cyan
Write-Host "  repo: $repoRoot"
Write-Host "  workspace: $WorkspaceRoot"
Write-Host "  out: $resolvedOutDir"

& $agentContext build `
    --config $resolvedConfig `
    --out $resolvedOutDir `
    --workspace-root $WorkspaceRoot

if ($LASTEXITCODE -ne 0) {
    throw "agent-context build fallito con exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Artifacts pronti:" -ForegroundColor Green
Write-Host "  $resolvedOutDir\session_bootstrap.md"
Write-Host "  $resolvedOutDir\workspace_triage.json"
Write-Host "  $resolvedOutDir\topic_index.json"

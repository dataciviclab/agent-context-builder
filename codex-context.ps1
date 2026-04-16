<#
.SYNOPSIS
Build locale del contesto per Codex su Windows.

.DESCRIPTION
Wrapper operativo per `agent-context build` in local mode.
Richiede un workspace root esplicito e prova a usare prima `.venv314`,
poi `.venv`, se presenti nella repo.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,
    [string]$OutDir = "generated-local",
    [string]$ConfigPath = "dataciviclab.config.yml",
    [string]$VenvName = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolvedOutDir = Join-Path $repoRoot $OutDir
$resolvedConfig = Join-Path $repoRoot $ConfigPath

$candidateVenvs = @()
if ($VenvName) {
    $candidateVenvs += $VenvName
}
$candidateVenvs += @(".venv314", ".venv")

$python = $null
$agentContext = $null
$resolvedVenv = $null
foreach ($candidate in $candidateVenvs | Select-Object -Unique) {
    $candidatePython = Join-Path $repoRoot "$candidate\Scripts\python.exe"
    $candidateCli = Join-Path $repoRoot "$candidate\Scripts\agent-context.exe"
    if ((Test-Path $candidatePython) -and (Test-Path $candidateCli)) {
        $python = $candidatePython
        $agentContext = $candidateCli
        $resolvedVenv = $candidate
        break
    }
}

if (-not (Test-Path $WorkspaceRoot)) {
    throw "Workspace root non trovato: $WorkspaceRoot"
}

if (-not (Test-Path $python)) {
    throw "Nessun venv compatibile trovato. Attesi: .venv314 o .venv, oppure passa -VenvName."
}

if (-not (Test-Path $resolvedConfig)) {
    throw "Config non trovata: $resolvedConfig"
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:CURL_CA_BUNDLE = ""

Write-Host "Building agent context for Codex..." -ForegroundColor Cyan
Write-Host "  repo: $repoRoot"
Write-Host "  venv: $resolvedVenv"
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

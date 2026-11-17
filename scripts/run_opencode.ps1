# Start ERA with the local OpenCode server as its LLM runtime.
# Usage:  .\scripts\run_opencode.ps1 [-Port 9467] [-ApiPort 8765]
param(
    [int]$Port = 9467,
    [int]$ApiPort = 8765
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Isolated OpenCode config: default plugins can crash the server on generation.
$configDir = Join-Path $env:TEMP "era-opencode"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
'{"$schema":"https://opencode.ai/config.json"}' | Set-Content -Encoding ascii (Join-Path $configDir "opencode.json")

$env:OPENCODE_CONFIG_DIR = $configDir
$env:OPENCODE_DISABLE_DEFAULT_PLUGINS = "1"
$env:OPENCODE_DISABLE_CLAUDE_CODE = "1"
$env:OPENCODE_DISABLE_PROJECT_CONFIG = "1"

if (-not $env:OPENCODE_SERVER_PASSWORD) {
    $env:OPENCODE_SERVER_PASSWORD = -join (1..32 | ForEach-Object { "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[(Get-Random -Maximum 62)] })
}

$env:ERA_LLM_PROVIDER = "opencode_server"
$env:OPENCODE_SERVER_URL = "http://127.0.0.1:$Port"
$env:OPENCODE_MODEL = if ($env:OPENCODE_MODEL) { $env:OPENCODE_MODEL } else { "deepseek-v4.1-flash-free" }
$env:PYTHONPATH = $root

$serverLog = Join-Path $configDir "serve-$Port.log"
$opencodeCmd = (Get-Command opencode.cmd -ErrorAction SilentlyContinue).Source
if (-not $opencodeCmd) { $opencodeCmd = "opencode" }
$server = Start-Process -FilePath $opencodeCmd -ArgumentList @("serve", "--port", "$Port", "--hostname", "127.0.0.1") `
    -RedirectStandardOutput $serverLog -RedirectStandardError "$serverLog.err" -PassThru -WindowStyle Hidden

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    if (Select-String -Path $serverLog -Pattern "server listening" -Quiet -ErrorAction SilentlyContinue) { break }
    if ($server.HasExited) { throw "opencode serve exited early; see $serverLog" }
}

Write-Host "[run_opencode] OpenCode server on $env:OPENCODE_SERVER_URL (pid $($server.Id))"
Write-Host "[run_opencode] model $env:OPENCODE_MODEL"

try {
    & "$root\.venv\Scripts\python.exe" -m uvicorn api:app --port $ApiPort
} finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
}

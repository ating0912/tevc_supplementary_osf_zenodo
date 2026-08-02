param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('ECMADE_MOO','A_MPMO')]
    [string]$Method
)

$ErrorActionPreference = 'Stop'

$root = 'C:\Users\yiting\Documents\Playground'
$logDir = Join-Path $root 'p0_lite_outputs\synthetic_constrained_portfolio\logs'
if (!(Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Remove-Item Env:PATH -ErrorAction SilentlyContinue
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
    [Environment]::GetEnvironmentVariable('Path','User')

$script = switch ($Method) {
    'ECMADE_MOO' { 'run_p0_lite_synthetic_ecmade_moo' }
    'A_MPMO'     { 'run_p0_lite_synthetic_ampmo' }
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $logDir ("{0}_force_rerun_{1}.log" -f $Method,$stamp)
$matlab = 'C:\Program Files\MATLAB\R2026a\bin\matlab.exe'
$batch = "cd('$root'); SYNTHETIC_SPLITS={'train','validation','test'}; SYNTHETIC_SKIP_SUMMARY=true; SYNTHETIC_FORCE_RERUN=true; $script;"

Set-Location -LiteralPath $root
& $matlab -batch $batch *> $log
exit $LASTEXITCODE

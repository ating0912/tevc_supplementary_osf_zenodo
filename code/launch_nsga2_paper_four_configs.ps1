$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$matlab = 'C:\Program Files\MATLAB\R2026a\bin\matlab.exe'
$logDir = Join-Path $root 'nsga2_outputs\paper_four_seeded\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$started = foreach ($config in 'P1', 'P2', 'P3', 'P4') {
    $log = Join-Path $logDir "$config.log"
    $batch = "cd('$root'); run_nsga2_paper_four_configs('$config',1:30)"
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $matlab
    $info.Arguments = '-logfile "' + $log + '" -batch "' + $batch + '"'
    $info.WorkingDirectory = $root
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $process = [System.Diagnostics.Process]::Start($info)

    [pscustomobject]@{
        Config = $config
        PID = $process.Id
        Log = $log
    }
}

$started | Export-Csv (Join-Path $logDir 'processes.csv') -NoTypeInformation
$started

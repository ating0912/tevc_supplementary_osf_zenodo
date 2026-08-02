$ErrorActionPreference = "Stop"

$Root = "C:\Users\yiting\Documents\Playground"
$OutRoot = Join-Path $Root "p0_lite_outputs\tevc_pdf_direct_ablation_full_20260717"
$JobFile = Join-Path $Root "run_tevc_pdf_direct_ablation_full_job.m"
$StdOut = Join-Path $OutRoot "matlab_stdout.log"
$Status = Join-Path $OutRoot "launcher_status.txt"
$MatlabExe = "C:\Program Files\MATLAB\R2026a\bin\matlab.exe"

New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
"started $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -Path $Status -Encoding UTF8

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $MatlabExe
$psi.Arguments = "-wait -logfile `"$StdOut`" -batch `"run('$JobFile')`""
$psi.WorkingDirectory = $Root
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)
[PSCustomObject]@{
    Id = $proc.Id
    ProcessName = $proc.ProcessName
    StartTime = $proc.StartTime
    OutRoot = $OutRoot
}

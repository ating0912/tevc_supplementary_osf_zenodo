$ErrorActionPreference = "Stop"

$Root = "C:\Users\yiting\Documents\Playground"
$OutRoot = Join-Path $Root "p0_lite_outputs\tevc_pdf_direct_ablation_full_20260717"
$MatlabCmd = @"
cd('$Root');
TEVC_ABLATION_OUT_ROOT='$OutRoot';
TEVC_ABLATION_RUNS=30;
TEVC_ABLATION_N=100;
TEVC_ABLATION_MAXFE=10000;
TEVC_ABLATION_MAX_INSTANCES=inf;
TEVC_ABLATION_FORCE_RERUN=false;
run_tevc_pdf_direct_ablation
"@

New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null

Start-Process `
  -FilePath "matlab" `
  -ArgumentList @("-batch", $MatlabCmd) `
  -WorkingDirectory $Root `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $OutRoot "matlab_stdout.log") `
  -RedirectStandardError (Join-Path $OutRoot "matlab_stderr.log") `
  -PassThru |
  Select-Object Id, ProcessName, StartTime

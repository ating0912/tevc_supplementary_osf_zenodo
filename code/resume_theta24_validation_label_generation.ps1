$ErrorActionPreference = "Stop"

$root = "C:\Users\yiting\Documents\Playground"
$outRoot = Join-Path $root "p0_lite_outputs\theta24_70_15_15_validation_label_full_20260713"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdout = Join-Path $outRoot "resume_stdout_$stamp.log"
$stderr = Join-Path $outRoot "resume_stderr_$stamp.log"
$status = Join-Path $outRoot "resume_status_$stamp.txt"
$matlab = "C:\Program Files\MATLAB\R2026a\bin\matlab.exe"

$batch = "THETA24_FULL_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\theta24_70_15_15_validation_label_full_20260713'; THETA24_FULL_SPLITS={'Validation'}; THETA24_FULL_MAX_INSTANCES=29; run_theta24_192instance_label_full"

Set-Location -LiteralPath $root
"started=$(Get-Date -Format o)" | Set-Content -LiteralPath $status -Encoding UTF8
"stdout=$stdout" | Add-Content -LiteralPath $status -Encoding UTF8
"stderr=$stderr" | Add-Content -LiteralPath $status -Encoding UTF8

& $matlab -batch $batch > $stdout 2> $stderr
$exitCode = $LASTEXITCODE

"finished=$(Get-Date -Format o)" | Add-Content -LiteralPath $status -Encoding UTF8
"exit_code=$exitCode" | Add-Content -LiteralPath $status -Encoding UTF8
exit $exitCode

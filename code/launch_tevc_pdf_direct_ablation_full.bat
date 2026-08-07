@echo off
set ROOT=.
set OUTROOT=%ROOT%\p0_lite_outputs\tevc_pdf_direct_ablation_full_20260717
if not exist "%OUTROOT%" mkdir "%OUTROOT%"
cd /d "%ROOT%"
echo started %DATE% %TIME% > "%OUTROOT%\launcher_status.txt"
matlab -batch "cd('%ROOT%'); TEVC_ABLATION_OUT_ROOT='%OUTROOT%'; TEVC_ABLATION_RUNS=30; TEVC_ABLATION_N=100; TEVC_ABLATION_MAXFE=10000; TEVC_ABLATION_MAX_INSTANCES=inf; TEVC_ABLATION_FORCE_RERUN=false; run_tevc_pdf_direct_ablation" > "%OUTROOT%\matlab_stdout.log" 2> "%OUTROOT%\matlab_stderr.log"
echo finished %DATE% %TIME% >> "%OUTROOT%\launcher_status.txt"

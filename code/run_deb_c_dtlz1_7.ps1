$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $root "nsga2_sources\nsga2-gnuplot-v1.1.6"
$out = Join-Path $root "nsga2_outputs\deb_c_dtlz1_7_maxfe10000"
$gcc = "C:\tmp\nsga2-mingw\Library\bin\x86_64-w64-mingw32-gcc.exe"
$runtimeBin = "C:\tmp\nsga2-mingw\Library\bin"
$sources = Get-ChildItem -LiteralPath $src -Filter "*.c" |
    Where-Object {
        $_.Name -notlike "._*" -and $_.Name -notlike "#*" -and
        $_.Name -notin @("problemdef.c","problemdef_uf.c","problemdef_dtlz.c")
    } | Select-Object -ExpandProperty FullName
New-Item -ItemType Directory -Force -Path $out | Out-Null
$oldPath = $env:PATH; $env:PATH = "$runtimeBin;$env:PATH"
try {
    foreach ($problem in 1..7) {
        $name = "DTLZ$problem"
        $dimensions = if ($problem -eq 1) { 7 } elseif ($problem -eq 7) { 22 } else { 12 }
        $problemDir = Join-Path $out $name
        New-Item -ItemType Directory -Force -Path $problemDir | Out-Null
        $exe = Join-Path $problemDir "nsga2r_$name.exe"
        & $gcc "-DDTLZ_PROBLEM=$problem" "-O2" "-std=gnu89" @sources `
            (Join-Path $src "problemdef_dtlz.c") "-o" $exe "-lm"
        if ($LASTEXITCODE -ne 0) { throw "Compilation failed for $name" }
        $bounds = for ($d=1; $d -le $dimensions; $d++) { "0 1" }
        $inputLines = @("100","100","3","0","$dimensions") + $bounds +
            @("1","$([string](1.0/$dimensions))","20","20","0","0")
        $inputFile = Join-Path $problemDir "input.in"
        Set-Content -LiteralPath $inputFile -Value $inputLines -Encoding ascii
        foreach ($run in 1..30) {
            $runDir = Join-Path $problemDir ("run_{0:D3}" -f $run)
            if (Test-Path (Join-Path $runDir "best_pop.out")) { continue }
            New-Item -ItemType Directory -Force -Path $runDir | Out-Null
            Push-Location $runDir
            try {
                Get-Content -LiteralPath $inputFile | & $exe ($run/31.0) | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "$name run $run failed" }
            } finally { Pop-Location }
        }
        Write-Host "$name completed: 30 runs"
    }
} finally { $env:PATH = $oldPath }

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $root "nsga2_sources\nsga2-gnuplot-v1.1.6"
$out = Join-Path $root "nsga2_outputs\deb_c_uf1_5_maxfe10000"
$gcc = "C:\tmp\nsga2-mingw\Library\bin\x86_64-w64-mingw32-gcc.exe"
$runtimeBin = "C:\tmp\nsga2-mingw\Library\bin"
$runs = 30

if (-not (Test-Path $gcc)) {
    throw "GCC not found: $gcc"
}

$sources = Get-ChildItem -LiteralPath $src -Filter "*.c" |
    Where-Object {
        $_.Name -notlike "._*" -and
        $_.Name -notlike "#*" -and
        $_.Name -ne "problemdef.c" -and
        $_.Name -ne "problemdef_uf.c"
    } |
    Select-Object -ExpandProperty FullName

New-Item -ItemType Directory -Force -Path $out | Out-Null
$oldPath = $env:PATH
$env:PATH = "$runtimeBin;$env:PATH"

try {
    foreach ($problem in 1..5) {
        $name = "UF$problem"
        $problemDir = Join-Path $out $name
        New-Item -ItemType Directory -Force -Path $problemDir | Out-Null
        $exe = Join-Path $problemDir "nsga2r_$name.exe"
        $problemSource = Join-Path $src "problemdef_uf.c"

        & $gcc "-DUF_PROBLEM=$problem" "-O2" "-std=gnu89" @sources $problemSource "-o" $exe "-lm"
        if ($LASTEXITCODE -ne 0) {
            throw "Compilation failed for $name"
        }

        $bounds = for ($d = 1; $d -le 30; $d++) {
            if ($d -eq 1 -or $problem -eq 3) { "0 1" } else { "-1 1" }
        }
        $inputLines = @("100","100","2","0","30") + $bounds +
            @("1","0.0333333333333333","20","20","0","0")
        $inputFile = Join-Path $problemDir "input.in"
        Set-Content -LiteralPath $inputFile -Value $inputLines -Encoding ascii

        foreach ($run in 1..$runs) {
            $runDir = Join-Path $problemDir ("run_{0:D3}" -f $run)
            New-Item -ItemType Directory -Force -Path $runDir | Out-Null
            $seed = $run / 31.0
            Push-Location $runDir
            try {
                Get-Content -LiteralPath $inputFile | & $exe $seed | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    throw "$name run $run failed"
                }
            }
            finally {
                Pop-Location
            }
        }
        Write-Host "$name completed: $runs runs"
    }
}
finally {
    $env:PATH = $oldPath
}

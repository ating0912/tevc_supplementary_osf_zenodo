$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcDir = Join-Path $scriptDir "nsga2_sources\nsga2-gnuplot-v1.1.6"
$outDir = Join-Path $scriptDir "nsga2_outputs\deb_c"
$inputFile = Join-Path $scriptDir "nsga2_deb_zdt1_N100_D30_MaxIt10000.in"
$runs = 30

if (-not (Test-Path $srcDir)) {
    throw "Deb NSGA-II C source directory not found: $srcDir"
}

if (-not (Test-Path $inputFile)) {
    throw "ZDT1 input file not found: $inputFile"
}

$gcc = Get-Command gcc -ErrorAction SilentlyContinue
if (-not $gcc) {
    throw "gcc was not found. Install MinGW-w64/MSYS2 gcc, then run this script again."
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Push-Location $srcDir
try {
    $exe = Join-Path $outDir "nsga2r.exe"
    $sources = Get-ChildItem -Path $srcDir -Filter "*.c" |
        Where-Object { $_.Name -notlike "._*" -and $_.Name -notlike "#*" } |
        ForEach-Object { $_.FullName }

    & $gcc.Source -Wall -ansi -pedantic -g @sources -o $exe -lm
    if ($LASTEXITCODE -ne 0) {
        throw "gcc failed with exit code $LASTEXITCODE"
    }

    for ($run = 1; $run -le $runs; $run++) {
        $runDir = Join-Path $outDir ("run_{0:D3}" -f $run)
        New-Item -ItemType Directory -Force -Path $runDir | Out-Null
        $seed = [double]$run / ($runs + 1)

        Get-Content $inputFile | & $exe $seed
        if ($LASTEXITCODE -ne 0) {
            throw "nsga2r failed with exit code $LASTEXITCODE on run $run"
        }

        foreach ($name in "initial_pop.out", "final_pop.out", "best_pop.out", "all_pop.out", "params.out") {
            if (Test-Path $name) {
                Move-Item -Force $name (Join-Path $runDir $name)
            }
        }
        Write-Host ("run {0:D3}: saved {1}" -f $run, $runDir)
    }

    Write-Host "Saved executable: $exe"
    Write-Host "Saved outputs:    $outDir"
}
finally {
    Pop-Location
}

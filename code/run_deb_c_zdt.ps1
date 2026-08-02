$ErrorActionPreference="Stop"
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$src=Join-Path $root "nsga2_sources\nsga2-gnuplot-v1.1.6"
$out=Join-Path $root "nsga2_outputs\deb_c_zdt_maxfe10000"
$gcc="C:\tmp\nsga2-mingw\Library\bin\x86_64-w64-mingw32-gcc.exe"
$old=$env:PATH; $env:PATH="C:\tmp\nsga2-mingw\Library\bin;$env:PATH"
$sources=Get-ChildItem $src -Filter "*.c"|Where-Object{$_.Name -notlike "._*" -and $_.Name -notlike "#*" -and $_.Name -notin @("problemdef_uf.c","problemdef_dtlz.c")}|Select-Object -ExpandProperty FullName
try {
 foreach($problem in 1,2,3,4,6){
  $name="ZDT$problem"; $D=if($problem -le 3){30}else{10}; $dir=Join-Path $out $name
  New-Item -ItemType Directory -Force $dir|Out-Null; $exe=Join-Path $dir "nsga2r_$name.exe"
  & $gcc "-Dzdt$problem" "-O2" "-std=gnu89" @sources "-o" $exe "-lm"; if($LASTEXITCODE){throw "compile $name"}
  $bounds=for($i=1;$i -le $D;$i++){if($problem -eq 4 -and $i -gt 1){"-5 5"}else{"0 1"}}
  $input=@("100","100","2","0","$D")+$bounds+@("1","$([string](1.0/$D))","20","20","0","0")
  $in=Join-Path $dir "input.in"; Set-Content $in $input -Encoding ascii
  foreach($run in 1..30){$rd=Join-Path $dir ("run_{0:D3}"-f $run);if(Test-Path(Join-Path $rd "best_pop.out")){continue};New-Item -ItemType Directory -Force $rd|Out-Null;Push-Location $rd;try{Get-Content $in|& $exe ($run/31.0)|Out-Null;if($LASTEXITCODE){throw "$name $run"}}finally{Pop-Location}}
  Write-Host "$name completed"
 }
} finally {$env:PATH=$old}

param([int]$Epochs=30, [int]$Workers=8, [string]$Device='cuda')
$ErrorActionPreference='Stop'
$Python=Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (!(Test-Path $Python)) { throw 'First create .venv and install the dependencies in README.' }
function Run-Step([string[]]$Arguments) {
  & $Python @Arguments
  if ($LASTEXITCODE -ne 0) { throw ('Step failed: '+($Arguments -join ' ')) }
}
Run-Step @('scripts/download_camus.py','--workers',"$Workers")
Run-Step @('-m','cardiac.cli','prepare')
Run-Step @('-m','cardiac.cli','train','--epochs',"$Epochs",'--device',$Device)
$Modes=@(@(),@('--temporal'),@('--gate'),@('--temporal','--gate'))
$Names=@('baseline','temporal','gate','temporal_gate')
for ($i=0;$i -lt 4;$i++) {
  $Arguments=@('-m','cardiac.cli','evaluate','--weights','checkpoints/camus_baseline/best.pt','--output',('runs/'+$Names[$i]),'--device',$Device)+$Modes[$i]
  Run-Step $Arguments
}

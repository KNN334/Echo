param(
    [string]$KiCadBin = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin",
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$boardRoot = Join-Path $projectRoot 'hardware\kicad\orthogonal88'
$exportRoot = Join-Path $boardRoot 'exports'
$cli = Join-Path $KiCadBin 'kicad-cli.exe'
New-Item -ItemType Directory -Path $exportRoot -Force | Out-Null
function Invoke-KiCad {
    & $cli @args
    if ($LASTEXITCODE -ne 0) { throw "KiCad command failed: $args" }
}
foreach ($name in @('E1','E2','E3','E4','RETURN','SHIELD')) {
    $board = Join-Path $boardRoot "masks\$name.kicad_pcb"
    Invoke-KiCad pcb drc --format json --all-track-errors --refill-zones --save-board --exit-code-violations --output "$exportRoot\${name}_drc.json" $board
    Invoke-KiCad pcb export svg --layers F.Cu --mode-single --page-size-mode 2 --exclude-drawing-sheet --black-and-white --scale 1 --output "$exportRoot\$name.svg" $board
    Invoke-KiCad pcb export dxf --layers F.Cu --mode-single --output-units mm --use-contours --exclude-refdes --exclude-value --scale 1 --output "$exportRoot\${name}_mm.dxf" $board
}
# The total board uses padless inner-layer zones, so isolated-copper warnings
# remain visible. The independent audit accepts only this warning type.
$mainBoard = Join-Path $boardRoot 'orthogonal88.kicad_pcb'
$schematic = Join-Path $boardRoot 'orthogonal88.kicad_sch'
Invoke-KiCad pcb drc --format json --all-track-errors --refill-zones --save-board --output "$exportRoot\main_drc.json" $mainBoard
Invoke-KiCad pcb export svg --layers 'F.Cu,In1.Cu,In2.Cu,In3.Cu,User.2,Edge.Cuts' --mode-single --page-size-mode 2 --exclude-drawing-sheet --scale 1 --output "$exportRoot\orthogonal88.svg" $mainBoard
Invoke-KiCad sch erc --format json --exit-code-violations --output "$exportRoot\erc.json" $schematic
Invoke-KiCad sch export netlist --format kicadxml --output "$exportRoot\orthogonal88.xml" $schematic
Invoke-KiCad sch export pdf --output "$exportRoot\orthogonal88_schematic.pdf" $schematic
& $Python (Join-Path $PSScriptRoot 'verify_orthogonal_patch.py')
if ($LASTEXITCODE -ne 0) { throw 'Topology/geometry audit failed.' }

param([string]$PanoId = "SIM-00001", [int]$Duration = 60)
& "$PSScriptRoot\senaryo.ps1" -Scenario "S2" -PanoId $PanoId -Duration $Duration

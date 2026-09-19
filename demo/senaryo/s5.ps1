param([string]$PanoId = "SIM-00001", [int]$Duration = 45)
& "$PSScriptRoot\senaryo.ps1" -Scenario "S5" -PanoId $PanoId -Duration $Duration

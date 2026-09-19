param([string]$PanoId = "SIM-00001", [int]$Duration = 60)
& "$PSScriptRoot\senaryo.ps1" -Scenario "S0" -PanoId $PanoId -Duration $Duration

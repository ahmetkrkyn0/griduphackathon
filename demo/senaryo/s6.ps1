param([string]$PanoId = "SIM-00001", [int]$Duration = 60)
& "$PSScriptRoot\senaryo.ps1" -Scenario "S6" -PanoId $PanoId -Duration $Duration

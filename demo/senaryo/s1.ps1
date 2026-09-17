param([string]$PanoId = "SIM-00001", [int]$Duration = 90)
& "$PSScriptRoot\senaryo.ps1" -Scenario "S1" -PanoId $PanoId -Duration $Duration

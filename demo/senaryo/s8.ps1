param([string]$PanoId = "SIM-00001", [int]$Duration = 120)
& "$PSScriptRoot\senaryo.ps1" -Scenario "S8" -PanoId $PanoId -Duration $Duration

<#
.SYNOPSIS
  GridUp Hackathon — Windows PowerShell Senaryo Koşucusu

.DESCRIPTION
  Linux/Bash bağımlılığı olmadan S0 - S8 senaryolarını Windows üzerinde çalıştırır.

.PARAMETER Scenario
  S0, S1, S2, S3, S4, S5, S6, S7 veya S8

.PARAMETER PanoId
  Pano kimliği (Varsayılan: SIM-00001)

.PARAMETER Duration
  Süre (saniye, varsayılan senaryoya göre değişir)

.EXAMPLE
  .\senaryo.ps1 -Scenario S0
  .\senaryo.ps1 -Scenario S1 -Duration 90
#>
param(
    [Parameter(Position=0, Mandatory=$false)]
    [ValidateSet("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8")]
    [string]$Scenario = "S0",

    [Parameter(Position=1, Mandatory=$false)]
    [string]$PanoId = "SIM-00001",

    [Parameter(Position=2, Mandatory=$false)]
    [int]$Duration = 0
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
. (Join-Path $scriptDir "_ortak.ps1")

$scenarios = @{
    "S0" = @{ Name = "S0_normal"; Title = "S0 - Normal gun"; DefaultSec = 60; Extra = @("--season", "yaz"); Desc = "Yaz gununde saglikli pano, beklenen alarm 0" }
    "S1" = @{ Name = "S1_loose_conn"; Title = "S1 - Gevsek baglanti (DSYA-3 L2)"; DefaultSec = 90; Extra = @("--point", "DSYA3_L2"); Desc = "K katsayisi artisi, 158 saat onceden erken uyari" }
    "S2" = @{ Name = "S2_overload"; Title = "S2 - Asiri yuk"; DefaultSec = 60; Extra = @(); Desc = "K sabit kalirken nominal akim asimi" }
    "S3" = @{ Name = "S3_condense"; Title = "S3 - Ciy / yogusma riski"; DefaultSec = 60; Extra = @(); Desc = "Sicaklik ve bagil nem ciy sinirini zorlar" }
    "S4" = @{ Name = "S4_arc"; Title = "S4 - Ark ve kesici acmasi"; DefaultSec = 45; Extra = @(); Desc = "Optik ark parlamasi, TVOC gazi ve 10 ms icinde trip" }
    "S5" = @{ Name = "S5_prot_health"; Title = "S5 - Koruma kaybi"; DefaultSec = 45; Extra = @(); Desc = "Ark sensoru veya fiber optik arizasi" }
    "S6" = @{ Name = "S6_comms_loss"; Title = "S6 - Iletisim kaybi"; DefaultSec = 60; Extra = @(); Desc = "Heartbeat asimi ve sessiz pano alarmi" }
    "S7" = @{ Name = "S7_harmonic"; Title = "S7 - Harmonik bozulma"; DefaultSec = 60; Extra = @(); Desc = "THD_V ve THD_I asimi" }
    "S8" = @{ Name = "S8_sensor_fault"; Title = "S8 - Sensor arizasi"; DefaultSec = 60; Extra = @(); Desc = "Sensor kopmasi veya tutarsiz olcum" }
}

$cfg = $scenarios[$Scenario]
Write-Title $cfg.Title
Write-Host $cfg.Desc -ForegroundColor Cyan

if ($Duration -le 0) {
    $Duration = $cfg.DefaultSec
}

$ok = Run-Scenario -scenario $cfg.Name -pano $PanoId -duration $Duration -extraArgs $cfg.Extra

Write-Host "`nİzleme Linkleri:" -ForegroundColor DarkGray
Write-Host "  Tekil Pano: $FRONTEND_BASE/pano/$PanoId"
Write-Host "  Trend Analizi: $FRONTEND_BASE/trend/$PanoId"
Write-Host "  Alarm Konsolu: $FRONTEND_BASE/alarmlar"

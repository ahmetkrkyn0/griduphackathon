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
    "S0" = @{ Name = "S0_normal"; Title = "S0 — Normal gün"; DefaultSec = 60; Extra = @("--season", "yaz"); Desc = "Yaz gününde sağlıklı pano, beklenen alarm 0" }
    "S1" = @{ Name = "S1_loose_conn"; Title = "S1 — Gevşek bağlantı (DSYA-3 L2)"; DefaultSec = 90; Extra = @("--point", "DSYA3_L2"); Desc = "K katsayısı artışı, 209 saat önceden erken uyarı" }
    "S2" = @{ Name = "S2_overload"; Title = "S2 — Aşırı yük"; DefaultSec = 60; Extra = @(); Desc = "K sabit kalırken nominal akım aşımı" }
    "S3" = @{ Name = "S3_dew_condense"; Title = "S3 — Çiy / yoğuşma riski"; DefaultSec = 60; Extra = @(); Desc = "Sıcaklık ve bağıl nem çiy sınırını zorlar" }
    "S4" = @{ Name = "S4_arc_trip"; Title = "S4 — Ark ve kesici açması"; DefaultSec = 45; Extra = @(); Desc = "Optik ark parlaması, TVOC gazı ve 10 ms içinde trip" }
    "S5" = @{ Name = "S5_prot_loss"; Title = "S5 — Koruma kaybı"; DefaultSec = 45; Extra = @(); Desc = "Ark sensörü veya fiber optik arızası" }
    "S6" = @{ Name = "S6_sensor_drift"; Title = "S6 — Sensör sapması"; DefaultSec = 60; Extra = @(); Desc = "Fiziksel modelden kopan hatalı sensör tespiti" }
    "S7" = @{ Name = "S7_comms_loss"; Title = "S7 — İletişim kaybı"; DefaultSec = 60; Extra = @(); Desc = "Heartbeat aşımı ve sessiz pano alarmı" }
    "S8" = @{ Name = "S8_fleet_mix"; Title = "S8 — Karma filo senaryosu"; DefaultSec = 120; Extra = @(); Desc = "Çoklu panoda farklı anomaliler" }
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

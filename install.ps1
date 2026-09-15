# ==============================================================================
#  MAX AI Agent — Automated Windows PowerShell Installer
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   MAX AI Agent — Automated Installer for Windows" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$InstallDir = "$env:USERPROFILE\.max-ai"
$BinDir = "$env:USERPROFILE\.local\bin"
$RepoUrl = "https://github.com/Karanztez/MAX.git"

# 1. Check Python and Git
Write-Host "▶ [1/4] ตรวจสอบ Python และ Git..." -ForegroundColor Blue
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "กรุณาติดตั้ง Git for Windows ก่อนใช้งานตัวติดตั้งอัตโนมัติ (https://git-scm.com)"
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "กรุณาติดตั้ง Python 3 ก่อนใช้งานตัวติดตั้งอัตโนมัติ (https://python.org)"
}

# 2. Clone or Update
Write-Host "▶ [2/4] กำลังดาวน์โหลดซอร์สโค้ด MAX AI..." -ForegroundColor Blue
if (Test-Path "$InstallDir\.git") {
    Write-Host "  • พบการติดตั้งเดิม กำลังอัปเดต..."
    Set-Location $InstallDir
    git fetch --all --tags -q
    git reset --hard origin/main -q
} else {
    Write-Host "  • กำลังโคลนมาที่ $InstallDir..."
    if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
    git clone --depth 1 $RepoUrl $InstallDir -q
    Set-Location $InstallDir
}

# 3. Setup Virtual Environment
Write-Host "▶ [3/4] กำลังสร้าง Virtual Environment และติดตั้ง Dependencies..." -ForegroundColor Blue
if (-not (Test-Path "$InstallDir\venv")) {
    python -m venv "$InstallDir\venv"
}

$PyExec = "$InstallDir\venv\Scripts\python.exe"
$PipExec = "$InstallDir\venv\Scripts\pip.exe"

& $PipExec install --upgrade pip -q
& $PipExec install -r requirements.txt -q
& $PipExec install -e . -q

# 4. Create max.cmd Launcher
Write-Host "▶ [4/4] กำลังสร้างคำสั่ง 'max' ในระบบ..." -ForegroundColor Blue
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Force -Path $BinDir | Out-Null }

$CmdContent = "@echo off`r`n`"$PyExec`" `"$InstallDir\main.py`" %*"
Set-Content -Path "$BinDir\max.cmd" -Value $CmdContent -Encoding ASCII

# Add to User PATH if not present
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    Write-Host "  • เพิ่ม $BinDir ใน User PATH เรียบร้อย" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  ✨ ติดตั้ง MAX AI Agent บน Windows สำเร็จเรียบร้อยแล้ว!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "คุณสามารถพิมพ์ 'max' ใน PowerShell / CMD เพื่อเริ่มใช้งานได้ทันที" -ForegroundColor Cyan
Write-Host ""

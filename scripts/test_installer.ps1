<#
.SYNOPSIS
    End-to-end test of the Windows installer on a CI runner.

.DESCRIPTION
    1. Seeds a user-data marker file in %APPDATA%\YT-DLP Studio.
    2. Installs silently, per user, and checks the EXE, the install marker,
       the Start-menu shortcut and the uninstall registry entry.
    3. Launches the INSTALLED GUI headless (QT_QPA_PLATFORM=offscreen) and waits
       for "started successfully" in the app log. A CLI-only check would not
       load the Qt stack, so it could pass while the app cannot start.
    4. Uninstalls silently and checks that the program, shortcut and registry
       entry are gone and that the user-data marker SURVIVED.
    5. Installs again and uninstalls with /PURGEDATA=yes, and checks that the
       user data is removed only then.

    Exits 1 on the first failed check.

.PARAMETER Setup
    Path to YT-DLP-Studio-Setup-<version>.exe.
#>
param(
    [Parameter(Mandatory = $true)][string]$Setup
)

$ErrorActionPreference = "Stop"

$AppId = "{A55A4BB4-4BB7-48A4-970B-C0A9E9545BC2}"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\YT-DLP Studio"
$Exe = Join-Path $InstallDir "yt-dlp-studio.exe"
$DataDir = Join-Path $env:APPDATA "YT-DLP Studio"
$LogFile = Join-Path $DataDir "yt-dlp-studio.log"
$Marker = Join-Path $DataDir "ci-user-data-marker.txt"
$Shortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\YT-DLP Studio.lnk"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1"

# Watchdog: if the whole test runs longer than this, a background job writes
# the busiest processes to a file and force-stops installer, uninstaller and
# app processes, so any blocked wait returns and the job ends with a log.
$WatchdogSeconds = 600
$WatchdogFile = Join-Path $env:TEMP "installer-test-watchdog.txt"
Remove-Item $WatchdogFile -ErrorAction SilentlyContinue
$Watchdog = Start-Job -ArgumentList $WatchdogSeconds, $WatchdogFile -ScriptBlock {
    param($Limit, $OutFile)
    Start-Sleep -Seconds $Limit
    $lines = @("WATCHDOG $(Get-Date -Format HH:mm:ss): installer test still running after $Limit s")
    $lines += (Get-Process | Sort-Object CPU -Descending | Select-Object -First 30 Name, Id, CPU, StartTime | Format-Table | Out-String)
    $lines | Out-File -FilePath $OutFile -Encoding UTF8
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "YT-DLP-Studio-Setup*" -or $_.Name -like "unins*" -or $_.Name -like "_iu*" -or $_.Name -like "is-*" -or $_.Name -eq "yt-dlp-studio" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Step([string]$Name) {
    Write-Host "[$(Get-Date -Format HH:mm:ss)] STEP $Name"
}

function Show-Watchdog {
    if (Test-Path $WatchdogFile) { Write-Host "----- watchdog report"; Get-Content $WatchdogFile }
}

function Fail([string]$Message) {
    Show-Watchdog
    Write-Host "FAIL: $Message"
    exit 1
}

# Start a process and wait for it alone, with a time limit. Start-Process
# -Wait has no limit and also waits for child processes, so one hidden prompt
# or leftover process would hang the job until the workflow timeout.
function Invoke-Bounded([string]$File, [string[]]$Arguments, [int]$Seconds, [string]$What, [string]$Log = "") {
    $proc = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru
    $null = $proc.Handle  # cache the handle so ExitCode is available after the wait
    if (-not $proc.WaitForExit($Seconds * 1000)) {
        Write-Host "----- $What did not finish within $Seconds s; running processes:"
        Get-Process | Sort-Object CPU -Descending | Select-Object -First 25 Name, Id, CPU, StartTime | Format-Table | Out-String | Write-Host
        if ($Log -and (Test-Path $Log)) { Write-Host "----- $Log (last 40 lines)"; Get-Content $Log | Select-Object -Last 40 }
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Fail "$What did not finish within $Seconds s"
    }
    return $proc
}

function Assert([bool]$Condition, [string]$Message) {
    if (-not $Condition) { Fail $Message }
    Write-Host "ok: $Message"
}

function Install-App {
    $p = Invoke-Bounded $Setup @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=install.log") 300 "installer" "install.log"
    if ($p.ExitCode -ne 0) {
        Get-Content install.log -ErrorAction SilentlyContinue | Select-Object -Last 30
        Fail "installer exited with code $($p.ExitCode)"
    }
    # setup.exe hands off to a temporary helper and can exit before the files
    # are in place, so wait for the uninstaller (written last) to appear.
    $uninstaller = Join-Path $InstallDir "unins000.exe"
    for ($i = 0; $i -lt 120 -and -not (Test-Path $uninstaller); $i++) { Start-Sleep -Seconds 1 }
}

function Uninstall-App([string[]]$ExtraArgs = @()) {
    $uninstaller = Join-Path $InstallDir "unins000.exe"
    Assert (Test-Path $uninstaller) "uninstaller present"
    $uninstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") + $ExtraArgs
    Invoke-Bounded $uninstaller $uninstallArgs 120 "uninstaller" | Out-Null
    # unins000.exe hands off to a temporary copy and returns at once, so wait
    # for the uninstall to actually finish.
    for ($i = 0; $i -lt 60 -and (Test-Path $Exe); $i++) { Start-Sleep -Seconds 1 }
    # The temporary copy (_iu*.tmp) keeps cleaning up after the EXE is gone and
    # deletes unins000.exe last. Wait for it, so a following install does not
    # race the end of this uninstall.
    for ($i = 0; $i -lt 120; $i++) {
        $busy = (Test-Path $uninstaller) -or (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "_iu*" })
        if (-not $busy) { break }
        Start-Sleep -Seconds 1
    }
}

# --- 1. user data that must survive an uninstall -------------------------
Step "1 seed user data"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Set-Content -Path $Marker -Value "user data that an uninstall must keep"

# --- 2. silent per-user install ------------------------------------------
Step "2 silent install"
Install-App
Assert (Test-Path $Exe) "EXE installed at $Exe"
Assert (Test-Path (Join-Path $InstallDir "install.ini")) "install marker written"
Assert (Test-Path $Shortcut) "Start-menu shortcut created"
Assert (Test-Path $UninstallKey) "per-user uninstall entry registered (HKCU)"

# --- 3. the installed GUI starts -----------------------------------------
Step "3 installed GUI starts"
$before = 0
if (Test-Path $LogFile) { $before = @(Select-String -Path $LogFile -Pattern "started successfully").Count }
$env:QT_QPA_PLATFORM = "offscreen"
$app = Start-Process -FilePath $Exe -PassThru
$started = $false
# The one-file EXE unpacks itself before Python starts, so allow time.
for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $LogFile) {
        $now = @(Select-String -Path $LogFile -Pattern "started successfully").Count
        if ($now -gt $before) { $started = $true; break }
    }
    if ($app.HasExited) { break }
}
if (-not $app.HasExited) { Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue }
Get-Process -Name "yt-dlp-studio" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
if (-not $started) {
    if (Test-Path $LogFile) { Get-Content $LogFile | Select-Object -Last 40 }
    Fail "installed app did not log 'started successfully' within 120 s"
}
Write-Host "ok: installed GUI started (log reached 'started successfully')"

# --- 3b. update started from the app relaunches it ------------------------
Step "3b update relaunch"
# The app starts the installer with /SILENT /LAUNCH=yes and quits. The
# installer inherits the app's PyInstaller variables, which point at the
# app's temp folder; that folder is gone once the app has quit. Before the
# fix, the relaunched app failed with "Failed to load Python DLL" from it.
$before = @(Select-String -Path $LogFile -Pattern "started successfully").Count
$env:_PYI_APPLICATION_HOME_DIR = Join-Path $env:TEMP "_MEI_gone_$(Get-Random)"
$env:_PYI_ARCHIVE_FILE = Join-Path $env:TEMP "gone-$(Get-Random).exe"
$env:_PYI_PARENT_PROCESS_LEVEL = "1"
# Wait for the installer alone (see Invoke-Bounded): it starts the app, which keeps running.
$p = Invoke-Bounded $Setup @("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LAUNCH=yes", "/LOG=update.log") 300 "update installer" "update.log"
Remove-Item Env:_PYI_APPLICATION_HOME_DIR, Env:_PYI_ARCHIVE_FILE, Env:_PYI_PARENT_PROCESS_LEVEL
if ($p.ExitCode -ne 0) { Fail "update install exited with $($p.ExitCode)" }
$started = $false
for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Seconds 1
    $now = @(Select-String -Path $LogFile -Pattern "started successfully").Count
    if ($now -gt $before) { $started = $true; break }
}
Get-Process -Name "yt-dlp-studio" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
if (-not $started) {
    Get-Content $LogFile | Select-Object -Last 40
    Fail "app relaunched by a silent update (with the old app's PyInstaller variables) did not start within 120 s"
}
Write-Host "ok: silent update relaunched the app despite stale PyInstaller variables"

# --- 4. silent uninstall keeps user data ---------------------------------
Step "4 uninstall keeps data"
Uninstall-App
Assert (-not (Test-Path $Exe)) "EXE removed"
Assert (-not (Test-Path $Shortcut)) "Start-menu shortcut removed"
Assert (-not (Test-Path $UninstallKey)) "uninstall entry removed"
Assert (Test-Path $Marker) "user data KEPT after a normal uninstall"

# --- 5. explicit purge removes user data ---------------------------------
Step "5 purge removes data"
Install-App
Uninstall-App @("/PURGEDATA=yes")
Assert (-not (Test-Path $Exe)) "EXE removed (purge run)"
Assert (-not (Test-Path $DataDir)) "user data removed with /PURGEDATA=yes"

Stop-Job $Watchdog -ErrorAction SilentlyContinue
Show-Watchdog
Write-Host "Installer test passed."
exit 0

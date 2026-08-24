[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Installer,
    [Parameter(Mandatory)] [string]$ExpectedVersion,
    [Parameter(Mandatory)] [string]$ExpectedInstallerSha256,
    [string]$InstallRoot = "$env:LOCALAPPDATA\Programs\PHASENOX",
    [string]$EvidenceDirectory = "$env:TEMP\phasenox-clean-machine-evidence",
    [string]$AudioFixture = "",
    [string]$PreviousInstaller = "",
    [string]$PreviousVersion = "",
    [switch]$RequireCleanUserState,
    [switch]$RequireNoPython,
    [switch]$RequireNoVCRedist,
    [switch]$RequireOffline,
    [switch]$Repair,
    [switch]$ReadOnlyInstallProbe,
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-NormalizedHash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Start-NativeProcess([string]$Path, [string[]]$Arguments) {
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Path
    $startInfo.UseShellExecute = $false
    foreach ($argument in $Arguments) { $startInfo.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($startInfo)
    if ($null -eq $process) { throw "Unable to start $Path" }
    return $process
}

function Invoke-Installer([string]$Path, [string]$Destination) {
    $arguments = @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/DIR=$Destination"
    )
    $process = Start-NativeProcess $Path $arguments
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "Installer failed with exit code $($process.ExitCode)"
    }
    return $process.ExitCode
}

function Get-PointerBytes([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return [Convert]::ToBase64String([IO.File]::ReadAllBytes($Path))
}

function Get-VCRedistInventory {
    $locations = @(
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    return @(
        Get-ItemProperty -Path $locations -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -match "Microsoft Visual C\+\+.*Redistributable" } |
            Select-Object DisplayName, DisplayVersion, Publisher
    )
}

function Test-InternetConnectivity {
    $profiles = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue)
    return [bool]($profiles | Where-Object {
        $_.IPv4Connectivity -eq "Internet" -or $_.IPv6Connectivity -eq "Internet"
    })
}

function Confirm-FirstLaunchDataRoot([Diagnostics.Process]$Process) {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    $root = [Windows.Automation.AutomationElement]::RootElement
    $window = $null
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $deadline -and $null -eq $window) {
        if ($Process.HasExited) { throw "PHASENOX exited before Data Location confirmation" }
        $condition = [Windows.Automation.PropertyCondition]::new(
            [Windows.Automation.AutomationElement]::NameProperty,
            "PHASENØX Data Location"
        )
        $window = $root.FindFirst([Windows.Automation.TreeScope]::Children, $condition)
        if ($null -eq $window) { Start-Sleep -Milliseconds 250 }
    }
    if ($null -eq $window) { throw "First-launch Data Location dialog did not appear" }
    $buttonCondition = [Windows.Automation.AndCondition]::new(
        [Windows.Automation.PropertyCondition]::new(
            [Windows.Automation.AutomationElement]::ControlTypeProperty,
            [Windows.Automation.ControlType]::Button
        ),
        [Windows.Automation.PropertyCondition]::new(
            [Windows.Automation.AutomationElement]::NameProperty,
            "Confirm Data Location"
        )
    )
    $button = $window.FindFirst([Windows.Automation.TreeScope]::Descendants, $buttonCondition)
    if ($null -eq $button) { throw "Data Location confirmation button was not found" }
    $invoke = $button.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern)
    $invoke.Invoke()
}

function Invoke-PackagedProbe(
    [string]$Executable,
    [string]$ProbePath,
    [string]$Fixture,
    [string]$ReportPath,
    [bool]$ConfirmFirstLaunch
) {
    $arguments = @("--packaging-probe", $ProbePath)
    if ($Fixture) {
        $arguments += @("--packaged-analysis", $Fixture, "--packaged-analysis-report", $ReportPath)
    }
    $process = Start-NativeProcess $Executable $arguments
    if ($ConfirmFirstLaunch) { Confirm-FirstLaunchDataRoot $process }
    if (-not $process.WaitForExit(180000)) {
        $process.Kill($true)
        throw "PHASENOX packaging probe timed out"
    }
    if ($process.ExitCode -ne 0) { throw "PHASENOX probe exited with $($process.ExitCode)" }
    if (-not (Test-Path -LiteralPath $ProbePath)) { throw "Probe evidence was not written" }
    return Get-Content -LiteralPath $ProbePath -Raw | ConvertFrom-Json
}

$installerPath = [IO.Path]::GetFullPath($Installer)
$installPath = [IO.Path]::GetFullPath($InstallRoot)
$evidenceRoot = [IO.Path]::GetFullPath($EvidenceDirectory)
if (-not (Test-Path -LiteralPath $installerPath)) { throw "Installer not found" }
if ((Get-NormalizedHash $installerPath) -ne $ExpectedInstallerSha256.ToLowerInvariant()) {
    throw "Installer SHA-256 does not match the immutable candidate"
}
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$canonicalRoot = Join-Path $env:LOCALAPPDATA "PHASENOX\phasenox.desktop"
$pointerPath = Join-Path $canonicalRoot "state\data-root.json"
$handoffPath = Join-Path $canonicalRoot "state\installer-data-root.json"
if ($RequireCleanUserState -and (Test-Path -LiteralPath $canonicalRoot)) {
    throw "Clean-user certification requires canonical AppData to be absent"
}

$pythonCommands = [ordered]@{}
foreach ($name in @("python", "python3", "py")) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    $pythonCommands[$name] = if ($command) { $command.Source } else { $null }
}
$vcRedists = @(Get-VCRedistInventory)
$internetAvailable = Test-InternetConnectivity
if ($RequireNoPython -and ($pythonCommands.Values | Where-Object { $_ })) {
    throw "Python is present; this is not a no-Python certification environment"
}
if ($RequireNoVCRedist -and $vcRedists.Count -ne 0) {
    throw "A separately installed Microsoft VC++ Redistributable was detected"
}
if ($RequireOffline -and $internetAvailable) {
    throw "An Internet-connected network profile is active"
}

$beforePointer = Get-PointerBytes $pointerPath
$oldOfflineHub = $env:HF_HUB_OFFLINE
$oldOfflineTransformers = $env:TRANSFORMERS_OFFLINE
$oldHfHome = $env:HF_HOME
$forbiddenHfHome = Join-Path $evidenceRoot "forbidden-hf-cache"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_HOME = $forbiddenHfHome

try {
    $upgrade = $null
    if ($PreviousInstaller) {
        if (-not $PreviousVersion) { throw "PreviousVersion is required with PreviousInstaller" }
        $previousPath = [IO.Path]::GetFullPath($PreviousInstaller)
        $upgrade = [ordered]@{
            previous_installer = $previousPath
            previous_version = $PreviousVersion
            exit_code = Invoke-Installer $previousPath $installPath
        }
    }

    $installExit = Invoke-Installer $installerPath $installPath
    $executable = Join-Path $installPath "PHASENOX.exe"
    if (-not (Test-Path -LiteralPath $executable)) { throw "Installed executable is missing" }
    $installedVersion = (Get-Item -LiteralPath $executable).VersionInfo.ProductVersion
    if (-not $installedVersion.StartsWith($ExpectedVersion)) {
        throw "Installed version $installedVersion does not match $ExpectedVersion"
    }
    if (-not (Test-Path -LiteralPath $handoffPath) -and $RequireCleanUserState) {
        throw "Installer did not create the pending Data Root handoff"
    }

    $firstProbePath = Join-Path $evidenceRoot "first-launch-probe.json"
    $analysisReport = Join-Path $evidenceRoot "analysis-report.json"
    $firstProbe = Invoke-PackagedProbe `
        $executable $firstProbePath $AudioFixture $analysisReport $RequireCleanUserState
    if (-not (Test-Path -LiteralPath $pointerPath)) {
        throw "First launch did not commit the canonical Data Root pointer"
    }
    if (Test-Path -LiteralPath $handoffPath) {
        throw "Consumed installer handoff remains after successful confirmation"
    }
    $pointerAfterFirstLaunch = Get-PointerBytes $pointerPath
    $secondProbe = Invoke-PackagedProbe `
        $executable (Join-Path $evidenceRoot "second-launch-probe.json") "" "" $false
    if ((Get-PointerBytes $pointerPath) -ne $pointerAfterFirstLaunch) {
        throw "Second launch changed the Data Root pointer"
    }

    $readOnlyProbe = $null
    if ($ReadOnlyInstallProbe) {
        $aclBackup = Join-Path $evidenceRoot "install-acl.txt"
        & icacls.exe $installPath /save $aclBackup /t /c | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Unable to capture install ACL" }
        & icacls.exe $installPath /inheritance:r /grant:r "*S-1-1-0:(OI)(CI)(RX)" /t /c | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Unable to make install payload read-only" }
        try {
            $readOnlyProbe = Invoke-PackagedProbe `
                $executable (Join-Path $evidenceRoot "read-only-install-probe.json") "" "" $false
        } finally {
            & icacls.exe (Split-Path -Parent $installPath) /restore $aclBackup /c | Out-Null
        }
    }

    $repairResult = $null
    if ($Repair) {
        $repairTarget = Get-ChildItem -LiteralPath (Join-Path $installPath "_internal") `
            -Filter "*.dll" -File | Select-Object -First 1
        if (-not $repairTarget) { throw "No deterministic repair target was found" }
        $targetHash = Get-NormalizedHash $repairTarget.FullName
        Remove-Item -LiteralPath $repairTarget.FullName
        Invoke-Installer $installerPath $installPath | Out-Null
        $repairResult = [ordered]@{
            target = $repairTarget.Name
            restored = Test-Path -LiteralPath $repairTarget.FullName
            hash_restored = (Get-NormalizedHash $repairTarget.FullName) -eq $targetHash
            pointer_preserved = (Get-PointerBytes $pointerPath) -eq $pointerAfterFirstLaunch
        }
        if (-not $repairResult.restored -or -not $repairResult.hash_restored -or
            -not $repairResult.pointer_preserved) { throw "Repair contract failed" }
    }

    $uninstallResult = $null
    if ($Uninstall) {
        $uninstaller = Join-Path $installPath "unins000.exe"
        if (-not (Test-Path -LiteralPath $uninstaller)) { throw "Uninstaller is missing" }
        $uninstallProcess = Start-NativeProcess $uninstaller @(
            "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
        )
        $uninstallProcess.WaitForExit()
        if ($uninstallProcess.ExitCode -ne 0) { throw "Uninstall failed" }
        $uninstallResult = [ordered]@{
            exit_code = $uninstallProcess.ExitCode
            application_removed = -not (Test-Path -LiteralPath $executable)
            pointer_preserved = (Get-PointerBytes $pointerPath) -eq $pointerAfterFirstLaunch
            canonical_state_preserved = Test-Path -LiteralPath $canonicalRoot
        }
        if (-not $uninstallResult.application_removed -or
            -not $uninstallResult.pointer_preserved) { throw "App-only uninstall contract failed" }
    }

    if (Test-Path -LiteralPath $forbiddenHfHome) {
        throw "A forbidden model cache was created during offline certification"
    }
    $result = [ordered]@{
        schema_version = 2
        environment_id = "$env:COMPUTERNAME-$([Environment]::OSVersion.Version)"
        timestamp_utc = [DateTime]::UtcNow.ToString("o")
        windows = [ordered]@{
            product = (Get-CimInstance Win32_OperatingSystem).Caption
            version = [Environment]::OSVersion.Version.ToString()
            architecture = $env:PROCESSOR_ARCHITECTURE
        }
        user = [ordered]@{
            name = $env:USERNAME
            administrator = [Security.Principal.WindowsPrincipal]::new(
                [Security.Principal.WindowsIdentity]::GetCurrent()
            ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        }
        artifact = [ordered]@{
            installer = $installerPath
            installer_sha256 = Get-NormalizedHash $installerPath
            expected_version = $ExpectedVersion
        }
        prerequisites = [ordered]@{
            python_commands = $pythonCommands
            vc_redists = $vcRedists
            internet_profile_available = $internetAvailable
            offline_required = [bool]$RequireOffline
        }
        locations = [ordered]@{
            install = $installPath
            canonical_appdata = $canonicalRoot
            pointer = $pointerPath
            pointer_before = $beforePointer
            pointer_after = $pointerAfterFirstLaunch
        }
        install_exit_code = $installExit
        installed_version = $installedVersion
        first_launch = $firstProbe
        second_launch = $secondProbe
        upgrade = $upgrade
        repair = $repairResult
        read_only_install = $readOnlyProbe
        uninstall = $uninstallResult
        status = "PASS"
    }
    $evidencePath = Join-Path $evidenceRoot "clean-machine-certification.json"
    $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $evidencePath -Encoding utf8
    Write-Output "Clean-machine certification evidence: $evidencePath"
} finally {
    $env:HF_HUB_OFFLINE = $oldOfflineHub
    $env:TRANSFORMERS_OFFLINE = $oldOfflineTransformers
    $env:HF_HOME = $oldHfHome
}

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Installer,
    [Parameter(Mandatory)] [string]$ExpectedVersion,
    [string]$InstallRoot = "$env:LOCALAPPDATA\Programs\PHASENOX",
    [string]$Evidence = "$env:TEMP\phasenox-clean-machine-evidence.json",
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$installerPath = [IO.Path]::GetFullPath($Installer)
$installPath = [IO.Path]::GetFullPath($InstallRoot)
if (-not (Test-Path -LiteralPath $installerPath)) { throw "Installer not found" }

$beforePointer = Join-Path $env:LOCALAPPDATA "PHASENOX\phasenox.desktop\state\data-root.json"
$pointerHash = if (Test-Path -LiteralPath $beforePointer) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $beforePointer).Hash
} else { $null }

$process = Start-Process -FilePath $installerPath -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=$installPath"
) -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -ne 0) { throw "Installer failed with exit code $($process.ExitCode)" }
$exe = Join-Path $installPath "PHASENOX.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "Installed executable is missing" }
$installedVersion = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
if (-not $installedVersion.StartsWith($ExpectedVersion)) {
    throw "Installed version $installedVersion does not match $ExpectedVersion"
}

$afterHash = if (Test-Path -LiteralPath $beforePointer) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $beforePointer).Hash
} else { $null }
if ($pointerHash -ne $afterHash) { throw "Installer changed the authoritative Data Root pointer" }

$result = [ordered]@{
    schema_version = 1
    machine = $env:COMPUTERNAME
    python_on_path = [bool](Get-Command python -ErrorAction SilentlyContinue)
    repository_present = Test-Path -LiteralPath (Join-Path $installPath ".git")
    installer_exit_code = $process.ExitCode
    installed_version = $installedVersion
    pointer_preserved = $pointerHash -eq $afterHash
    uninstall_executed = $false
}
if ($Uninstall) {
    $uninstaller = Join-Path $installPath "unins000.exe"
    if (-not (Test-Path -LiteralPath $uninstaller)) { throw "Uninstaller is missing" }
    $uninstallProcess = Start-Process -FilePath $uninstaller -ArgumentList @(
        "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
    ) -Wait -PassThru -WindowStyle Hidden
    if ($uninstallProcess.ExitCode -ne 0) { throw "Uninstall failed" }
    $result.uninstall_executed = $true
    $result.pointer_preserved_after_uninstall = Test-Path -LiteralPath $beforePointer
}
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Evidence -Encoding utf8
Write-Output "Clean-machine install probe evidence: $Evidence"

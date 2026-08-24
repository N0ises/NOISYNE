[CmdletBinding()]
param(
    [string]$OutputRoot = "build/release/desktop-core",
    [string]$RuntimeWheelhouse = "",
    [string]$BuildWheelhouse = "",
    [string]$InnoCompiler = "",
    [switch]$SkipBundleLaunch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
$allowedOutputRoot = [IO.Path]::GetFullPath((Join-Path $repository "build/release"))
$output = if ([IO.Path]::IsPathRooted($OutputRoot)) {
    [IO.Path]::GetFullPath($OutputRoot)
} else {
    [IO.Path]::GetFullPath((Join-Path $repository $OutputRoot))
}
$allowedPrefix = $allowedOutputRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if (-not $output.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputRoot must resolve below $allowedOutputRoot"
}
if (Test-Path -LiteralPath $output) {
    $resolvedOutput = (Resolve-Path -LiteralPath $output).Path
    if (-not $resolvedOutput.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean an output outside $allowedOutputRoot"
    }
    Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
}
New-Item -ItemType Directory -Path $output | Out-Null

Push-Location $repository
try {
    $branch = (git branch --show-current).Trim()
    if ($branch -ne "v2-development") {
        throw "Desktop Core builds are restricted to v2-development, found $branch"
    }
    git diff --quiet --
    if ($LASTEXITCODE -ne 0) { throw "Tracked worktree changes must be committed before build" }
    git diff --cached --quiet --
    if ($LASTEXITCODE -ne 0) { throw "The index must be clean before build" }
    $gitSha = (git rev-parse HEAD).Trim()
    $untracked = @(git ls-files --others --exclude-standard)

    $sourceArchive = Join-Path $output "source.tar"
    $source = Join-Path $output "source"
    New-Item -ItemType Directory -Path $source | Out-Null
    git archive --format=tar --output=$sourceArchive $gitSha
    if ($LASTEXITCODE -ne 0) { throw "git archive failed" }
    tar -xf $sourceArchive -C $source
    if ($LASTEXITCODE -ne 0) { throw "source archive extraction failed" }

    $venv = Join-Path $output "venv"
    py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Unable to create the Python 3.12 release venv" }
    $python = Join-Path $venv "Scripts/python.exe"
    $actualPython = (& $python -c "import platform; print(platform.python_version())").Trim()
    if ($actualPython -ne "3.12.10") {
        throw "Release Python must be 3.12.10, found $actualPython"
    }

    $runtimeLock = Join-Path $source "tools/packaging/requirements/desktop-core-windows-x64.lock"
    $buildLock = Join-Path $source "tools/packaging/requirements/build-windows-x64.lock"
    $installOptions = @("-m", "pip", "install", "--disable-pip-version-check", "--require-hashes")
    if ($RuntimeWheelhouse) {
        $runtimeWheels = [IO.Path]::GetFullPath((Join-Path $repository $RuntimeWheelhouse))
        $installOptions += @("--no-index", "--find-links", $runtimeWheels)
    }
    & $python @installOptions "-r" $runtimeLock
    if ($LASTEXITCODE -ne 0) { throw "Desktop Core runtime lock installation failed" }

    $buildOptions = @("-m", "pip", "install", "--disable-pip-version-check", "--require-hashes")
    if ($BuildWheelhouse) {
        $buildWheels = [IO.Path]::GetFullPath((Join-Path $repository $BuildWheelhouse))
        $buildOptions += @("--no-index", "--find-links", $buildWheels)
        if ($RuntimeWheelhouse) { $buildOptions += @("--find-links", $runtimeWheels) }
    }
    & $python @buildOptions "-r" $buildLock
    if ($LASTEXITCODE -ne 0) { throw "Desktop Core build lock installation failed" }
    & $python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "pip check failed" }

    $evidence = Join-Path $output "evidence"
    New-Item -ItemType Directory -Path $evidence | Out-Null
    $profile = Join-Path $source "tools/packaging/profiles/desktop-core-windows-x64.json"
    & $python (Join-Path $source "tools/release/validate_release_environment.py") `
        --profile $profile `
        --runtime-lock $runtimeLock `
        --build-lock $buildLock `
        --output (Join-Path $evidence "release-environment.json")
    if ($LASTEXITCODE -ne 0) { throw "Release environment validation failed" }

    $wheelOutput = Join-Path $output "wheel"
    New-Item -ItemType Directory -Path $wheelOutput | Out-Null
    & $python -m build --wheel --no-isolation --outdir $wheelOutput $source
    if ($LASTEXITCODE -ne 0) { throw "Project wheel build failed" }
    $wheel = Get-ChildItem -LiteralPath $wheelOutput -Filter "phasenox-*.whl" | Select-Object -Single
    & $python -m pip install --disable-pip-version-check --no-deps $wheel.FullName
    if ($LASTEXITCODE -ne 0) { throw "Project wheel installation failed" }

    $assets = Join-Path $output "windows-assets"
    & $python (Join-Path $source "tools/packaging/generate_windows_assets.py") `
        --repository $source --output $assets
    if ($LASTEXITCODE -ne 0) { throw "Windows resource generation failed" }
    $version = (& $python -c "import tomllib,sys; print(tomllib.load(open(sys.argv[1],'rb'))['project']['version'])" (Join-Path $source "pyproject.toml")).Trim()
    $versionParts = $version.Split('.')
    if ($versionParts.Count -lt 3) { throw "Project version must have at least three numeric parts" }

    $dist = Join-Path $output "bundle"
    $work = Join-Path $output "pyinstaller-work"
    $env:PHASENOX_WINDOWS_ASSETS = $assets
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
    $pyinstallerLog = Join-Path $evidence "pyinstaller.log"
    & $python -m PyInstaller --noconfirm --clean --distpath $dist --workpath $work `
        (Join-Path $source "tools/packaging/phasenox_desktop_core.spec") 2>&1 |
        Tee-Object -FilePath $pyinstallerLog
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller Desktop Core build failed" }

    $bundle = Join-Path $dist "PHASENOX-$version-win-x64"
    $verification = Join-Path $evidence "bundle-verification.json"
    $verifyOptions = @(
        (Join-Path $source "tools/packaging/verify_desktop_core_bundle.py"),
        $bundle,
        "--profile", $profile,
        "--repository", $source,
        "--pyinstaller-log", $pyinstallerLog,
        "--output", $verification
    )
    if ($SkipBundleLaunch) { $verifyOptions += "--skip-launch" }
    & $python @verifyOptions
    if ($LASTEXITCODE -ne 0) { throw "Desktop Core bundle verification failed" }

    if (-not $InnoCompiler) {
        $candidate = Join-Path ${env:LOCALAPPDATA} "Programs\Inno Setup 7\ISCC.exe"
        if (Test-Path -LiteralPath $candidate) { $InnoCompiler = $candidate }
    }
    if (-not $InnoCompiler) {
        throw "Pinned Inno Setup 7.1.0-x64 compiler path is required"
    }
    $iscc = [IO.Path]::GetFullPath((Join-Path $repository $InnoCompiler))
    $innoVersion = (Get-Item -LiteralPath $iscc).VersionInfo.ProductVersion
    if (-not $innoVersion.StartsWith("7.1.0")) {
        throw "Inno Setup must be 7.1.0-x64, found $innoVersion"
    }
    $installerOutput = Join-Path $output "installer"
    New-Item -ItemType Directory -Path $installerOutput | Out-Null
    & $iscc /Qp `
        "/DAppVersion=$version" `
        "/DAppVersionMajor=$($versionParts[0])" `
        "/DAppVersionMinor=$($versionParts[1])" `
        "/DAppVersionPatch=$($versionParts[2])" `
        "/DBundleDir=$bundle" `
        "/DWindowsAssets=$assets" `
        "/DOutputDir=$installerOutput" `
        (Join-Path $source "tools/packaging/installer/PHASENOX.iss") 2>&1 |
        Tee-Object -FilePath (Join-Path $evidence "inno-setup.log")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup Desktop Core build failed" }
    $installer = Join-Path $installerOutput "PHASENOX-Setup-$version-win-x64.exe"
    if (-not (Test-Path -LiteralPath $installer)) { throw "Expected installer was not created" }

    $context = [ordered]@{
        schema_version = 1
        profile = "desktop-core"
        platform = "windows-x64"
        branch = $branch
        git_sha = $gitSha
        tracked_worktree_clean = $true
        source_materialization = "git archive"
        untracked_files_excluded = $untracked
        python = $actualPython
        bundle = $bundle
        installer = $installer
        inno_setup = $innoVersion
        signing_status = "UNSIGNED"
    }
    $contextPath = Join-Path $evidence "build-context.json"
    $context | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $contextPath -Encoding utf8
    & $python (Join-Path $source "tools/release/generate_release_artifacts.py") `
        --profile $profile --runtime-lock $runtimeLock --bundle-verification $verification `
        --build-context $contextPath --bundle $bundle --installer $installer `
        --windows-assets $assets --output $output
    if ($LASTEXITCODE -ne 0) { throw "Release evidence generation failed" }
    Write-Output "Desktop Core bundle and installer verified: $bundle"
} finally {
    Pop-Location
}

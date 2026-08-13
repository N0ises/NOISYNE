param(
    [ValidateSet("cpu", "shell")]
    [string]$Profile = "cpu",
    [switch]$SkipArchive
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = (Get-Command python).Source
$Generated = Join-Path $ProjectRoot "build\packaging"
$Bundle = Join-Path $ProjectRoot "dist\NOISYNE"
$Version = (& $Python -c "import sys,tomllib,pathlib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))['project']['version'])" (Join-Path $ProjectRoot "pyproject.toml")).Trim()

& $Python (Join-Path $PSScriptRoot "generate_windows_assets.py") `
    --project-root $ProjectRoot `
    --output $Generated
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:NOISYNE_PACKAGE_PROFILE = $Profile
& $Python -m PyInstaller `
    (Join-Path $PSScriptRoot "noisyne.spec") `
    --noconfirm `
    --clean `
    --distpath (Join-Path $ProjectRoot "dist") `
    --workpath (Join-Path $ProjectRoot "build\pyinstaller")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python (Join-Path $PSScriptRoot "verify_windows_artifact.py") `
    --bundle $Bundle `
    --expected-version $Version `
    --output (Join-Path $Generated "verification.json")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipArchive) {
    $Archive = Join-Path $ProjectRoot "dist\NOISYNE-windows-x64-$Version.zip"
    Remove-Item -LiteralPath $Archive -Force -ErrorAction SilentlyContinue
    & tar.exe -a -c -f $Archive -C (Join-Path $ProjectRoot "dist") "NOISYNE"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Output $Archive
}

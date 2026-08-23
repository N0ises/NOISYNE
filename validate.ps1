# -----------------------------
# PHASENØX Validation Runner
# -----------------------------

$musicFolder = "E:\Build\Music"

$extensions = @("*.wav", "*.mp3", "*.flac", "*.aiff")

$files = foreach ($ext in $extensions) {
    Get-ChildItem -Path $musicFolder -Filter $ext -File
}

foreach ($file in $files) {

    $name = $file.BaseName

    Write-Host ""
    Write-Host "=========================================="
    Write-Host "Analyzing: $($file.Name)"
    Write-Host "=========================================="

    python -m phasenox.cli analyze "$($file.FullName)" `
        --mix-intelligence `
        --plugin-intelligence `
        --reasoning `
        --output "reports\$name.json"

}

Write-Host ""
Write-Host "=========================================="
Write-Host "Validation Finished"
Write-Host "=========================================="

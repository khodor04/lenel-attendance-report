# Sign LenelAttendance.exe and LenelAttendanceSvc.exe
# Run this after every PyInstaller build: right-click → Run with PowerShell

$THUMBPRINT = "6D66B967F74A139EB1D7C011F09FEA350804AC5D"
$DIST       = "$PSScriptRoot\dist"

$cert = Get-ChildItem "Cert:\CurrentUser\My\$THUMBPRINT" -ErrorAction SilentlyContinue
if (-not $cert) {
    Write-Host "ERROR: Code signing certificate not found." -ForegroundColor Red
    Write-Host "Import LenelAttendance_CodeSign.cer to this machine first." -ForegroundColor Yellow
    pause; exit 1
}

foreach ($exe in @("LenelAttendance.exe", "LenelAttendanceSvc.exe")) {
    $path = "$DIST\$exe"
    if (-not (Test-Path $path)) {
        Write-Host "SKIP: $exe not found in dist\" -ForegroundColor Yellow
        continue
    }
    $result = Set-AuthenticodeSignature `
        -FilePath $path `
        -Certificate $cert `
        -TimestampServer "http://timestamp.digicert.com" `
        -HashAlgorithm SHA256
    if ($result.Status -eq 'Valid') {
        Write-Host "OK:   $exe signed successfully" -ForegroundColor Green
    } else {
        Write-Host "FAIL: $exe — $($result.StatusMessage)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Done. Press any key to close."
pause

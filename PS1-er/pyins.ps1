# PyInstaller wrapper script

param(
    [string]$Distpath = ".",
    [string]$Asset,
    [Parameter(Mandatory = $true)]
    [string]$PYscript,
    [switch]$AdminRequired
)

$Distpath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Distpath)

# Temporary build directory
$TempBuild = Join-Path $env:TEMP ([guid]::NewGuid().ToString())

# Build arguments
$Arguments = @(
    "--onefile"
    "--distpath"
    $Distpath
    "--workpath"
    "$TempBuild\build"
    "--specpath"
    $TempBuild
    #admin required for certain operations
    if ($AdminRequired) {
        "--uac-admin"
    }
)

if ($Asset) {
    $Arguments += @(
        "--add-data"
        "${Asset}:."
    )
}

$Arguments += $PYscript

# Run PyInstaller
python -m PyInstaller @Arguments

# Cleanup
if ($LASTEXITCODE -eq 0) {
    Write-Host "Cleaning up temporary build directory..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $TempBuild -Recurse -Force
    Write-Host "Temporary build directory removed." -ForegroundColor Yellow

    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Executable created at: $Distpath" -ForegroundColor Green
}
else {
    Write-Host "Build failed!" -ForegroundColor Red
}
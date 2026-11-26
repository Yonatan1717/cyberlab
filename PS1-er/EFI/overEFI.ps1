#check if the partition already has a drive letter assigned
$partition = Get-Partition -DiskNumber 0 -PartitionNumber 1
if (-not $partition.DriveLetter) {
    Set-Partition -DiskNumber 0 -PartitionNumber 1 -NewDriveLetter Z
    $letter = "Z:"
} else {
    $letter = $partition.DriveLetter + ":"
}

Copy-Item -Path .\boot_hello_text.efi -Destination $letter\EFI\boot\bootx64.efi
Copy-Item -Path .\boot_hello_text.efi -Destination $letter\EFI\Microsoft\Boot\bootmgfw.efi
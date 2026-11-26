clang --target=x86_64-pc-windows-msvc `
    -ffreestanding `
    -fshort-wchar `
    -fno-stack-protector `
    -O2 `
    -c boot_hello_text.c `
    -o boot_hello_text.obj

if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed"
}

lld-link /subsystem:efi_application `
    /entry:efi_main `
    /nodefaultlib `
    /machine:x64 `
    /dynamicbase `
    /fixed:no `
    /out:boot_hello_text.efi `
    boot_hello_text.obj

if ($LASTEXITCODE -ne 0) {
    throw "Linking failed"
}

Remove-Item boot_hello_text.obj

Write-Host "EFI build successful!" -ForegroundColor Green
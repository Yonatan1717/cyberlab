param(
    $SourceFile = "boot_hello_text.c"
)

clang --target=x86_64-pc-windows-msvc `
    -ffreestanding `
    -fshort-wchar `
    -fno-stack-protector `
    -O2 `
    -c $SourceFile `
    -o ($SourceFile -replace '\.c$', '.obj')

if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed"
}

$efiObj = $SourceFile -replace '\.c$', '.obj'
$efiOut = $SourceFile -replace '\.c$', '.efi'

Write-Host "EFI object -> $efiObj"
write-host "EFI output -> $efiOut"
Write-Host "Building $SourceFile into $efiOut..." -ForegroundColor Cyan

lld-link /subsystem:efi_application `
    /entry:efi_main `
    /nodefaultlib `
    /machine:x64 `
    /dynamicbase `
    /fixed:no `
    /out:$efiOut `
    $efiObj

if ($LASTEXITCODE -ne 0) {
    throw "Linking failed"
}

Remove-Item $efiObj

Write-Host "$SourceFile built successfully as $efiOut!" -ForegroundColor Green
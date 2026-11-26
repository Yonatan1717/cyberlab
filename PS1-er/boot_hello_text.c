/* Minimal x86-64 UEFI application. No disk or NVRAM writes. */
typedef unsigned long long EFI_STATUS;
typedef unsigned int UINT32;
typedef unsigned short CHAR16;
typedef void *EFI_HANDLE;
#define EFIAPI __attribute__((ms_abi))
#define EFI_SUCCESS 0ULL
#define EFI_NOT_READY 0x8000000000000006ULL

typedef struct {
    unsigned long long Signature;
    UINT32 Revision, HeaderSize, CRC32, Reserved;
} EFI_TABLE_HEADER;

typedef struct { unsigned short ScanCode; CHAR16 UnicodeChar; } EFI_INPUT_KEY;
typedef struct EFI_SIMPLE_TEXT_INPUT_PROTOCOL EFI_SIMPLE_TEXT_INPUT_PROTOCOL;
struct EFI_SIMPLE_TEXT_INPUT_PROTOCOL {
    void *Reset;
    EFI_STATUS (EFIAPI *ReadKeyStroke)(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *, EFI_INPUT_KEY *);
    void *WaitForKey;
};

typedef struct EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL;
struct EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL {
    void *Reset;
    EFI_STATUS (EFIAPI *OutputString)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *, CHAR16 *);
};

typedef struct {
    EFI_TABLE_HEADER Hdr;
    CHAR16 *FirmwareVendor;
    UINT32 FirmwareRevision;
    EFI_HANDLE ConsoleInHandle;
    EFI_SIMPLE_TEXT_INPUT_PROTOCOL *ConIn;
    EFI_HANDLE ConsoleOutHandle;
    EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *ConOut;
} EFI_SYSTEM_TABLE;

static CHAR16 *volatile hello_message = L"Ohhh, you're so cooked, buddy.\r\n"
    L"You're whole Windows disk is literally encrypted.\r\n"
    L"\r\n"
    L"Unless, of course, you transfer 400 Dogecoin to acount 0xdeadbeefcafebabe\r\n"
    L"Upon receipt of the transfer, you will get the key (hopefully).\r\n"
    L"We will do a spinning of the wheel to determine your fate.\r\n"
    L"\r\n"
    L"The chance of winning will be determined by the amount transferred.\r\n"
    L"Where: chance = (amount_transferred / 400) * 50%\r\n"
    L"As you have noticed you're maximun chance is 50%\r\n"
    L"\r\n"
    L"If you get lucky and win, you will get the key. Upon getting the key, you can decrypt your disk by following the instructions provided: https://r.mtdv.me/howToDecrypt.\r\n"
    L"\r\n"
    L"Good luck!\r\n"
    L"\r\n"
    L"Best regards,\r\n"
    L"¯\\_(ツ)_/¯";

EFI_STATUS EFIAPI efi_main(EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable)
{
    (void)ImageHandle;
    if (SystemTable->ConOut) {
        SystemTable->ConOut->OutputString(SystemTable->ConOut,
            hello_message);
    }
    if (SystemTable->ConIn) {
        EFI_INPUT_KEY key;
        while (SystemTable->ConIn->ReadKeyStroke(SystemTable->ConIn, &key) == EFI_NOT_READY) {
            __asm__ volatile("pause");
        }
    }
    return EFI_SUCCESS;
}

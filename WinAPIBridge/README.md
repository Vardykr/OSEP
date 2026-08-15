# WinAPIBridge

WinAPIBridge is a small, extensible CLI for generating Win32 API interop declarations and example calls for PowerShell, C#, and VBA.

The API catalog is data-driven (`src/winapibridge/apis.json`), so new APIs can be added without changing the generator logic.

## Install

From the `WinAPIBridge` directory:

```bash
python -m pip install -e .
```

Then use it from anywhere:

```bash
winapibridge MessageBox
winapibridge GetDriveType
winapibridge GetDriveType --lang csharp
winapibridge GetDriveType --lang vba
winapibridge --list
```

## Example

```bash
winapibridge GetDriveType
```

`GetDriveType` resolves to the Unicode export `GetDriveTypeW` and generates a PowerShell `Add-Type` block plus an example invocation.

## API catalog

The current catalog contains **57 Win32 APIs** across several practical categories:

- system and timing information
- process/thread identity and pseudo handles
- processor and processor-group information
- disk, drive, and file metadata
- window/UI state and system metrics
- locale, language, and code-page information
- console information
- path helper APIs

Examples include:

- `MessageBox` -> `MessageBoxW`
- `GetDriveType` -> `GetDriveTypeW`
- `GetCurrentProcessId`
- `GetCurrentThreadId`
- `GetCurrentProcess`
- `GetCurrentThread`
- `GetPhysicallyInstalledSystemMemory`
- `GetTickCount`
- `GetTickCount64`
- `QueryPerformanceCounter`
- `QueryPerformanceFrequency`
- `GetLogicalDrives`
- `GetFileAttributes` -> `GetFileAttributesW`
- `GetCompressedFileSize` -> `GetCompressedFileSizeW`
- `GetDiskFreeSpace` -> `GetDiskFreeSpaceW`
- `GetDiskFreeSpaceEx` -> `GetDiskFreeSpaceExW`
- `GetDesktopWindow`
- `GetForegroundWindow`
- `GetSystemMetrics`
- `GetSysColor`
- `GetKeyboardType`
- `GetACP`
- `GetOEMCP`
- `GetUserDefaultLCID`
- `GetConsoleCP`
- `GetConsoleOutputCP`
- `GetCurrentProcessorNumber`
- `GetActiveProcessorCount`
- `IsProcessorFeaturePresent`
- `PathFileExists` -> `PathFileExistsW`
- `PathIsDirectory` -> `PathIsDirectoryW`
- `PathIsNetworkPath` -> `PathIsNetworkPathW`

Run the following to see the complete list:

```bash
winapibridge --list
```

## Catalog metadata

Each API entry can include:

- friendly/lookup name
- canonical/export name
- DLL
- generated class name
- description
- Windows header name
- Microsoft Learn documentation URL
- original Win32 return type
- C# and VBA return types
- charset
- original Win32 parameter types
- C# and VBA parameter mappings
- PowerShell/C#/VBA example arguments
- optional example prelude
- notes for special cases or deprecated APIs

This keeps the catalog useful both for generation and as a Win32 API reference.

## Adding an API

Add a new entry to `src/winapibridge/apis.json`. Prefer the Unicode (`W`) export where a Windows API has ANSI/Unicode variants, and verify the native signature against Microsoft Learn.

Keeping signatures in JSON makes the project easy to expand, review, and eventually populate automatically from documentation metadata.

## Output targets

```text
powershell
csharp
vba
```

Use `--signature-only` when you only want the declaration without an example call.

## Development

```bash
python -m pip install -e .
python -m pytest
```

The tests validate that the catalog is documented and that every catalog entry can generate a PowerShell, C#, and VBA declaration.

## Notes

- VBA output targets modern 64-bit Office and uses `PtrSafe`.
- Unicode (`W`) variants are selected explicitly where appropriate.
- APIs requiring structures, callbacks, unions, arrays, custom buffer management, or special marshalling should get explicit generator support rather than guessed signatures.
- Signatures should be checked against Microsoft Learn before adding them to the catalog.

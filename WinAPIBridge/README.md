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

## Supported APIs

- `MessageBox` -> `MessageBoxW`
- `GetDriveType` -> `GetDriveTypeW`
- `GetCurrentProcessId`
- `GetPhysicallyInstalledSystemMemory`

## Adding an API

Add a new entry to `src/winapibridge/apis.json` with:

- friendly name
- canonical/export name
- DLL
- generated class name
- return types
- charset
- parameter metadata
- example arguments

Keeping signatures in JSON makes the project easy to expand and review.

## Output targets

```text
powershell
csharp
vba
```

Use `--signature-only` when you only want the declaration without an example call.

## Notes

- VBA output targets modern 64-bit Office and uses `PtrSafe`.
- Unicode (`W`) variants are selected explicitly where appropriate.
- Some Win32 APIs require custom marshalling; add explicit metadata rather than guessing.
- Signatures should be checked against Microsoft Learn before adding them to the catalog.

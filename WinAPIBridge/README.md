# WinAPIBridge

WinAPIBridge is an extensible CLI for generating Win32 API interop declarations and example calls for PowerShell, C#, and VBA.

The API catalog is data-driven and split across `apis*.json` files so categories can grow independently without changing generator logic. Package data includes all `apis*.json` files when installed.

## Install

From the `WinAPIBridge` directory:

```bash
python -m pip install -e .
```

Then use it from anywhere:

```bash
winapibridge MessageBox
winapibridge GetDriveType
winapibridge WinExec
winapibridge GetWindowsDirectory
winapibridge GetSystemInfo
winapibridge GetEnvironmentVariable --lang csharp
winapibridge GetWindowRect --lang csharp
winapibridge GetUserName --lang vba
winapibridge --list
winapibridge --search volume
```

## Reflective PowerShell mode

PowerShell output now has two backends:

```text
add-type     default C# P/Invoke + Add-Type backend
reflection   Reflection.Emit delegate backend for Windows PowerShell 5.1/.NET Framework
```

Examples:

```bash
winapibridge MessageBox --ps-mode reflection
winapibridge WinExec --ps-mode reflection
winapibridge GetDriveType --ps-mode reflection
winapibridge GetCurrentProcessId --ps-mode reflection --signature-only
```

The reflection backend generates reusable `LookupFunc` and `Get-DelegateType` helpers, resolves the export through `Microsoft.Win32.UnsafeNativeMethods`, creates a delegate type in memory with `Reflection.Emit`, and calls the function through `Marshal.GetDelegateForFunctionPointer`.

For catalog entries that normally target a Unicode `W` export, reflective mode currently resolves the corresponding ANSI `A` export when available. This matches the classic Windows PowerShell/.NET Framework reflection pattern and keeps string delegate marshalling predictable without `Add-Type`.

Current reflective support covers:

- scalar integer and pointer types
- strings
- `StringBuilder`
- primitive `out` / `ref` parameters
- APIs with no parameters

Win32 structures are intentionally not guessed in reflective mode yet. For APIs such as `GetSystemInfo`, use the normal backend:

```bash
winapibridge GetSystemInfo --ps-mode add-type
```

The CLI returns a clear error when a reflected signature needs a dynamic structure that the backend does not yet emit.

## v0.2+ marshalling support

The normal generator supports more than simple scalar and pointer parameters, including:

- `StringBuilder` output buffers
- multiple output buffers and multiple `out` parameters
- multi-line setup and result code (`prelude` / `postlude`)
- custom per-language example calls
- sequential Win32 structures
- `out` / `ref` structure parameters
- VBA `Type` generation
- Win32 `void` functions as VBA `Declare PtrSafe Sub`
- extra helper declarations used by an example
- multiple `apis*.json` catalog files

Representative APIs include `MessageBox`, `GetDriveType`, `WinExec`, `GetWindowsDirectory`, `GetComputerName`, `GetUserName`, `GetSystemInfo`, `GlobalMemoryStatusEx`, `GetLocalTime`, `GetCursorPos`, `GetWindowRect`, `GetWindowText`, `GetEnvironmentVariable`, `GetModuleFileName`, `GetFileSizeEx`, and many more.

The merged catalog contains **100+ Win32 APIs**.

## Searching the catalog

```bash
winapibridge --search volume
winapibridge --search process
winapibridge --search user32
winapibridge --search fileapi
```

Search covers the friendly name, canonical/export name, description, header, and DLL name.

## Catalog metadata

Each API entry may include:

- friendly/lookup name
- canonical/export name
- aliases
- DLL and generated class name
- description
- Windows header name
- Microsoft Learn documentation URL
- native Win32 return/parameter types
- C# and VBA mappings
- charset
- structures and fields
- PowerShell/C#/VBA example arguments
- setup/result statements
- helper declarations
- notes for special cases

## Adding APIs

Add entries to an `apis*.json` file under `src/winapibridge/`. Prefer the Unicode (`W`) export for normal P/Invoke output when an API has ANSI/Unicode variants and verify the native signature against Microsoft Learn.

## Output targets

```text
powershell
csharp
vba
```

Use `--signature-only` to omit example invocation code.

## Development

```bash
python -m pip install -e .
python -m pytest
```

Tests validate the 100+ API catalog, all three normal output languages, output-buffer marshalling, structures, and the reflective PowerShell backend for scalar/string/by-ref signatures.

## Notes

- Reflective mode targets Windows PowerShell 5.1 / .NET Framework semantics; PowerShell 7/.NET may expose different internal runtime types.
- VBA output targets modern 64-bit Office and uses `PtrSafe`.
- Complex unions, callbacks, variable-length arrays, and unusual custom marshalling should receive explicit generator support rather than guessed declarations.
- Native signatures should be verified against Microsoft Learn before catalog inclusion.

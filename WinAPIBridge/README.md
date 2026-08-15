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
winapibridge GetWindowsDirectory
winapibridge GetSystemInfo
winapibridge GetSystemTimeAsFileTime
winapibridge GetEnvironmentVariable --lang csharp
winapibridge GetWindowRect --lang csharp
winapibridge GetUserName --lang vba
winapibridge --list
```

## v0.2 marshalling support

WinAPIBridge now supports more than simple scalar and pointer parameters. The generator understands metadata for:

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

Representative APIs include:

- `GetWindowsDirectory` -> `GetWindowsDirectoryW`
- `GetSystemDirectory` -> `GetSystemDirectoryW`
- `GetComputerName` -> `GetComputerNameW`
- `GetUserName` -> `GetUserNameW`
- `GetLogicalDriveStrings` -> `GetLogicalDriveStringsW`
- `GetSystemInfo`
- `GlobalMemoryStatusEx`
- `GetLocalTime`
- `GetSystemTime`
- `GetSystemTimeAsFileTime`
- `GetSystemTimePreciseAsFileTime`
- `GetCursorPos`
- `GetWindowRect`
- `GetWindowText` -> `GetWindowTextW`
- `GetEnvironmentVariable` -> `GetEnvironmentVariableW`
- `ExpandEnvironmentStrings` -> `ExpandEnvironmentStringsW`
- `GetModuleFileName` -> `GetModuleFileNameW`
- `GetClassName` -> `GetClassNameW`
- `GetFileSizeEx`
- `GetFileTime`
- `GetWindowThreadProcessId`

The merged catalog now contains **100+ Win32 APIs**.

## Example: output buffer

```bash
winapibridge GetWindowsDirectory
```

The PowerShell output includes a C# P/Invoke declaration using `StringBuilder`, allocates a buffer, invokes the API, and prints the resulting path.

## Example: structure

```bash
winapibridge GetSystemInfo --lang vba
```

The generated VBA includes a `SYSTEM_INFO` `Type`, a `Declare PtrSafe Sub GetSystemInfo`, an initialized variable, the API call, and a sample result display.

## Example: FILETIME

```bash
winapibridge GetSystemTimeAsFileTime --lang csharp
```

The generated declaration includes a sequential `FILETIME` structure and the `out FILETIME` parameter mapping.

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

Add entries to an `apis*.json` file under `src/winapibridge/`. Prefer the Unicode (`W`) export when an API has ANSI/Unicode variants and verify the native signature against Microsoft Learn.

Splitting the catalog by category is encouraged as it grows, for example:

```text
apis.json
apis_v2.json
apis_v3.json
apis_files.json
apis_network.json
apis_registry.json
```

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

Tests validate 100+ catalog entries, metadata, generation for all three languages, output-buffer marshalling, structure generation, FILETIME generation, and helper declarations.

## Notes

- VBA output targets modern 64-bit Office and uses `PtrSafe`.
- Unicode (`W`) variants are selected explicitly where appropriate.
- Complex unions, callbacks, variable-length arrays, and unusual custom marshalling should receive explicit generator support rather than guessed declarations.
- Native signatures should be verified against Microsoft Learn before catalog inclusion.

# WinAPIBridge

WinAPIBridge is a small, extensible CLI for generating Win32 API interop declarations and example calls for PowerShell, C#, and VBA.

The API catalog is data-driven so new APIs can be added without changing generator logic.

## Planned usage

```bash
winapibridge MessageBox
winapibridge GetDriveType
winapibridge GetDriveType --lang csharp
winapibridge GetDriveType --lang vba
winapibridge --list
```

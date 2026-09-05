from winapibridge.core import generate, load_catalog


def test_messagebox_powershell():
    out = generate("MessageBox", "powershell")
    assert 'user32.dll' in out
    assert 'EntryPoint = "MessageBoxW"' in out
    assert '[User32]::MessageBox' in out


def test_getdrivetype_alias():
    out = generate("GetDriveType", "powershell")
    assert 'EntryPoint = "GetDriveTypeW"' in out
    assert '[Kernel32]::GetDriveType' in out


def test_vba_pid():
    out = generate("GetCurrentProcessId", "vba")
    assert 'Declare PtrSafe Function GetCurrentProcessId' in out


def test_winexec_generation():
    out = generate("WinExec", "powershell")
    assert 'kernel32.dll' in out
    assert 'CharSet = CharSet.Ansi' in out
    assert 'EntryPoint = "WinExec"' in out
    assert 'string lpCmdLine' in out
    assert 'uint uCmdShow' in out
    assert '[Kernel32]::WinExec("notepad.exe", 1)' in out


def test_catalog_is_large_and_documented():
    catalog = load_catalog()
    assert len(catalog) >= 100

    for name, spec in catalog.items():
        assert spec["canonical_name"]
        assert spec["dll"]
        assert spec["class"]
        assert spec["header"]
        assert spec["docs"].startswith("https://learn.microsoft.com/")
        assert spec["win32_return"]
        assert "csharp" in spec["return_type"]
        assert "vba" in spec["return_type"]


def test_every_catalog_entry_generates_all_languages():
    catalog = load_catalog()
    for name in catalog:
        for lang in ("powershell", "csharp", "vba"):
            out = generate(name, lang, include_example=False)
            assert out.strip(), f"empty output for {name} / {lang}"


def test_stringbuilder_marshalling():
    out = generate("GetWindowsDirectory", "powershell")
    assert "using System.Text;" in out
    assert "StringBuilder lpBuffer" in out
    assert "$buffer = [Text.StringBuilder]::new(260)" in out


def test_struct_marshalling():
    out = generate("GetSystemInfo", "csharp")
    assert "public struct SYSTEM_INFO" in out
    assert "out SYSTEM_INFO lpSystemInfo" in out

    vba = generate("GetSystemInfo", "vba")
    assert "Private Type SYSTEM_INFO" in vba
    assert "Declare PtrSafe Sub GetSystemInfo" in vba


def test_window_struct_and_helper_declaration():
    out = generate("GetWindowRect", "powershell")
    assert "public struct RECT" in out
    assert "GetForegroundWindow" in out
    assert "out RECT lpRect" in out


def test_filetime_struct_generation():
    out = generate("GetSystemTimeAsFileTime", "csharp", include_example=False)
    assert "public struct FILETIME" in out
    assert "out FILETIME lpSystemTimeAsFileTime" in out


def test_additional_output_buffer_generation():
    out = generate("GetEnvironmentVariable", "powershell", include_example=False)
    assert "StringBuilder lpBuffer" in out
    assert 'EntryPoint = "GetEnvironmentVariableW"' in out


def test_multi_catalog_sources_are_merged():
    catalog = load_catalog()
    assert "MessageBox" in catalog
    assert "GetSystemInfo" in catalog
    assert "GetSystemTimeAsFileTime" in catalog
    assert "GetEnvironmentVariable" in catalog
    assert "WinExec" in catalog


def test_catalog_has_searchable_metadata():
    catalog = load_catalog()
    assert any("volume" in spec.get("description", "").lower() for spec in catalog.values())
    assert any(spec.get("header") == "fileapi.h" for spec in catalog.values())
    assert any(spec.get("dll", "").lower() == "user32.dll" for spec in catalog.values())


def test_reflective_messagebox_backend():
    out = generate("MessageBox", "powershell", powershell_mode="reflection")
    assert "function LookupFunc" in out
    assert "function Get-DelegateType" in out
    assert "GetDelegateForFunctionPointer" in out
    assert 'LookupFunc "user32.dll" "MessageBoxA"' in out
    assert "@([IntPtr], [String], [String], [UInt32])" in out
    assert "$MessageBox.Invoke" in out
    assert "[DllImport(" not in out


def test_reflective_winexec_backend():
    out = generate("WinExec", "powershell", powershell_mode="reflection")
    assert 'LookupFunc "kernel32.dll" "WinExec"' in out
    assert "@([String], [UInt32])" in out
    assert '$WinExec.Invoke("notepad.exe", 1)' in out


def test_reflective_noarg_backend():
    out = generate(
        "GetCurrentProcessId",
        "powershell",
        include_example=False,
        powershell_mode="reflection",
    )
    assert "[Type[]]@()" in out
    assert "([UInt32])" in out
    assert 'LookupFunc "kernel32.dll" "GetCurrentProcessId"' in out


def test_reflective_primitive_byref_backend():
    out = generate(
        "GetPhysicallyInstalledSystemMemory",
        "powershell",
        powershell_mode="reflection",
    )
    assert "[UInt64].MakeByRefType()" in out
    assert "[ref]$memoryKb" in out


def test_reflective_structs_fail_with_clear_message():
    try:
        generate("GetSystemInfo", "powershell", powershell_mode="reflection")
    except ValueError as exc:
        assert "does not yet emit dynamic struct types" in str(exc)
    else:
        raise AssertionError("struct-based reflective generation should fail clearly")

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


def test_catalog_has_searchable_metadata():
    catalog = load_catalog()
    assert any("volume" in spec.get("description", "").lower() for spec in catalog.values())
    assert any(spec.get("header") == "fileapi.h" for spec in catalog.values())
    assert any(spec.get("dll", "").lower() == "user32.dll" for spec in catalog.values())

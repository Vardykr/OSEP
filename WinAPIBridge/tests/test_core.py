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
    assert len(catalog) >= 50

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

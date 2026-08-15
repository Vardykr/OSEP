from winapibridge.core import generate


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

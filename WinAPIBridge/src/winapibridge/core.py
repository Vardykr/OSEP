from __future__ import annotations

import json
from importlib.resources import files


def load_catalog() -> dict:
    """Load and merge every apis*.json catalog shipped with the package."""
    package = files("winapibridge")
    catalog: dict = {}
    for path in sorted(
        (p for p in package.iterdir() if p.name.startswith("apis") and p.name.endswith(".json")),
        key=lambda p: p.name,
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        overlap = set(catalog).intersection(data)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(f"Duplicate API definitions across catalog files: {names}")
        catalog.update(data)
    return catalog


def resolve_api(name: str) -> tuple[str, dict]:
    catalog = load_catalog()
    needle = name.strip().lower()
    for alias, spec in catalog.items():
        accepted = {alias.lower(), spec["canonical_name"].lower()}
        accepted.update(x.lower() for x in spec.get("aliases", []))
        if needle in accepted:
            return alias, spec
    available = ", ".join(sorted(catalog))
    raise KeyError(f"Unknown API '{name}'. Available: {available}")


def _dllimport(spec: dict) -> str:
    args = [f'"{spec["dll"]}"']
    if spec.get("charset"):
        args.append(f'CharSet = CharSet.{spec["charset"]}')
    if spec.get("set_last_error"):
        args.append("SetLastError = true")
    args.append(f'EntryPoint = "{spec["canonical_name"]}"')
    return f"[DllImport({', '.join(args)})]"


def _lines(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.splitlines()
    return list(value)


def _render_csharp_structs(spec: dict) -> str:
    chunks = []
    for struct in spec.get("structs", []):
        attrs = struct.get("csharp_attributes", ["StructLayout(LayoutKind.Sequential)"])
        lines = [f"[{a}]" for a in attrs]
        lines.append(f"public struct {struct['name']}")
        lines.append("{")
        for field in struct["fields"]:
            lines.append(f"    public {field['csharp']} {field['name']};")
        lines.append("}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def _render_vba_structs(spec: dict) -> str:
    chunks = []
    for struct in spec.get("structs", []):
        lines = [f"Private Type {struct['name']}"]
        for field in struct["fields"]:
            lines.append(f"    {field['name']} As {field['vba']}")
        lines.append("End Type")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def _csharp_signature(alias: str, spec: dict) -> str:
    params = ",\n        ".join(
        f'{p["csharp"]} {p["name"]}' for p in spec.get("parameters", [])
    )
    if params:
        return (
            f'{_dllimport(spec)}\n'
            f'public static extern {spec["return_type"]["csharp"]} {alias}(\n'
            f'        {params}\n'
            f');'
        )
    return (
        f'{_dllimport(spec)}\n'
        f'public static extern {spec["return_type"]["csharp"]} {alias}();'
    )


def _csharp_class_body(alias: str, spec: dict) -> str:
    parts = [_csharp_signature(alias, spec)]
    extra = spec.get("extra_declarations", {}).get("csharp")
    if extra:
        parts.append(extra)
    return "\n\n".join(parts)


def _default_call(alias: str, spec: dict, lang: str) -> str:
    args = ", ".join(spec.get("example_args", {}).get(lang, []))
    if lang == "powershell":
        return f'[{spec["class"]}]::{alias}({args})'
    if lang == "csharp":
        return f'{spec["class"]}.{alias}({args});'
    if spec.get("vba_kind", "Function") == "Sub":
        return f'{alias} {args}'.rstrip()
    return f'MsgBox {alias}({args})'


def _example_call(alias: str, spec: dict, lang: str) -> list[str]:
    custom = spec.get("example_call", {}).get(lang)
    if custom:
        return _lines(custom)
    return [_default_call(alias, spec, lang)]


def generate_csharp(name: str, include_example: bool = True) -> str:
    alias, spec = resolve_api(name)
    signature = _csharp_class_body(alias, spec)
    structs = _render_csharp_structs(spec)

    code = "using System;\nusing System.Text;\nusing System.Runtime.InteropServices;\n\n"
    if structs:
        code += structs + "\n\n"
    code += (
        f"public static class {spec['class']}\n"
        "{\n"
        + "    " + signature.replace("\n", "\n    ") + "\n"
        "}"
    )
    if include_example:
        pre = _lines(spec.get("prelude", {}).get("csharp"))
        call = _example_call(alias, spec, "csharp")
        post = _lines(spec.get("postlude", {}).get("csharp"))
        code += "\n\n" + "\n".join(pre + call + post)
    return code


def generate_powershell(name: str, include_example: bool = True) -> str:
    alias, spec = resolve_api(name)
    signature = _csharp_class_body(alias, spec)
    structs = _render_csharp_structs(spec)
    var = f'${spec["class"]}'

    source = "using System;\nusing System.Text;\nusing System.Runtime.InteropServices;\n\n"
    if structs:
        source += structs + "\n\n"
    source += (
        f"public static class {spec['class']}\n"
        "{\n"
        + "    " + signature.replace("\n", "\n    ") + "\n"
        "}"
    )

    code = f'{var} = @"\n{source}\n"@\n\nAdd-Type {var}'
    if include_example:
        pre = _lines(spec.get("prelude", {}).get("powershell"))
        call = _example_call(alias, spec, "powershell")
        post = _lines(spec.get("postlude", {}).get("powershell"))
        code += "\n\n" + "\n".join(pre + call + post)
    return code


_REFLECTION_TYPES = {
    "IntPtr": "[IntPtr]",
    "UIntPtr": "[UIntPtr]",
    "string": "[String]",
    "StringBuilder": "[Text.StringBuilder]",
    "uint": "[UInt32]",
    "int": "[Int32]",
    "ulong": "[UInt64]",
    "long": "[Int64]",
    "ushort": "[UInt16]",
    "short": "[Int16]",
    "byte": "[Byte]",
    "bool": "[Bool]",
    "void": "[Void]",
}


def _reflection_type_expr(csharp_type: str, spec: dict) -> str:
    byref = False
    base = csharp_type.strip()
    if base.startswith("out ") or base.startswith("ref "):
        byref = True
        base = base.split(" ", 1)[1]

    if base in {s["name"] for s in spec.get("structs", [])}:
        raise ValueError(
            f"Reflective PowerShell does not yet emit dynamic struct types ({base}). "
            "Use --ps-mode add-type for this API."
        )

    mapped = _REFLECTION_TYPES.get(base)
    if not mapped:
        raise ValueError(
            f"Reflective PowerShell type mapping is not implemented for '{csharp_type}'. "
            "Use --ps-mode add-type for this API."
        )
    if byref:
        return f"{mapped}.MakeByRefType()"
    return mapped


def _reflection_entry_point(spec: dict) -> str:
    """Use ANSI exports for reflected string marshalling, matching the PEN-300 pattern."""
    explicit = spec.get("reflection_entry_point")
    if explicit:
        return explicit
    name = spec["canonical_name"]
    if name.endswith("W") and spec.get("charset") == "Unicode":
        return name[:-1] + "A"
    return name


def generate_powershell_reflection(name: str, include_example: bool = True) -> str:
    """Generate a Windows PowerShell 5.1 Reflection.Emit invocation without Add-Type.

    This backend intentionally supports scalar/string/StringBuilder and primitive by-ref
    signatures first. APIs that require emitted Win32 structs currently fall back to the
    normal Add-Type backend.
    """
    alias, spec = resolve_api(name)
    param_types = [
        _reflection_type_expr(p["csharp"], spec) for p in spec.get("parameters", [])
    ]
    return_type = _reflection_type_expr(spec["return_type"]["csharp"], spec)
    entry_point = _reflection_entry_point(spec)
    delegate_var = f'${alias}Delegate'
    function_var = f'${alias}'

    helpers = r'''function LookupFunc {
    Param ($moduleName, $functionName)

    $assem = ([AppDomain]::CurrentDomain.GetAssemblies() |
        Where-Object {
            $_.GlobalAssemblyCache -And
            $_.Location.Split('\\')[-1].Equals('System.dll')
        }).GetType('Microsoft.Win32.UnsafeNativeMethods')

    $matches = @()
    $assem.GetMethods() | ForEach-Object {
        if ($_.Name -eq 'GetProcAddress') { $matches += $_ }
    }

    return $matches[0].Invoke(
        $null,
        @(
            ($assem.GetMethod('GetModuleHandle')).Invoke($null, @($moduleName)),
            $functionName
        )
    )
}

function Get-DelegateType {
    Param (
        [Parameter(Position = 0, Mandatory = $True)] [Type[]] $ParameterTypes,
        [Parameter(Position = 1)] [Type] $ReturnType = [Void]
    )

    $type = [AppDomain]::CurrentDomain.
        DefineDynamicAssembly(
            (New-Object System.Reflection.AssemblyName('ReflectedDelegate')),
            [System.Reflection.Emit.AssemblyBuilderAccess]::Run
        ).
        DefineDynamicModule('InMemoryModule', $false).
        DefineType(
            ('MyDelegateType_' + [Guid]::NewGuid().ToString('N')),
            'Class, Public, Sealed, AnsiClass, AutoClass',
            [System.MulticastDelegate]
        )

    $type.
        DefineConstructor(
            'RTSpecialName, HideBySig, Public',
            [System.Reflection.CallingConventions]::Standard,
            $ParameterTypes
        ).SetImplementationFlags('Runtime, Managed')

    $type.
        DefineMethod(
            'Invoke',
            'Public, HideBySig, NewSlot, Virtual',
            $ReturnType,
            $ParameterTypes
        ).SetImplementationFlags('Runtime, Managed')

    return $type.CreateType()
}'''

    param_array = "@(" + ", ".join(param_types) + ")"
    if not param_types:
        param_array = "[Type[]]@()"

    code = (
        "# Reflective PowerShell backend: Windows PowerShell 5.1 / .NET Framework\n"
        "# Resolves the API from loaded System.dll metadata and avoids Add-Type.\n\n"
        + helpers
        + "\n\n"
        + f'$addr = LookupFunc "{spec["dll"]}" "{entry_point}"\n'
        + f'{delegate_var} = Get-DelegateType {param_array} ({return_type})\n'
        + f'{function_var} = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($addr, {delegate_var})'
    )

    if include_example:
        pre = _lines(spec.get("prelude", {}).get("powershell"))
        args = ", ".join(spec.get("example_args", {}).get("powershell", []))
        call = f'$result = {function_var}.Invoke({args})'
        post = _lines(spec.get("postlude", {}).get("powershell"))
        code += "\n\n" + "\n".join(pre + [call] + post)
        if not post and spec["return_type"]["csharp"] != "void":
            code += "\n$result"
    return code


def generate_vba(name: str, include_example: bool = True) -> str:
    alias, spec = resolve_api(name)
    params = ", _\n        ".join(
        f'{p["vba_by"]} {p["name"]} As {p["vba"]}' for p in spec.get("parameters", [])
    )
    kind = spec.get("vba_kind", "Function")
    if kind == "Sub":
        if params:
            decl = (
                f'Private Declare PtrSafe Sub {alias} Lib "{spec["dll"]}" '
                f'Alias "{spec["canonical_name"]}" ( _\n'
                f'        {params} _\n'
                f')'
            )
        else:
            decl = f'Private Declare PtrSafe Sub {alias} Lib "{spec["dll"]}" Alias "{spec["canonical_name"]}" ()'
    else:
        if params:
            decl = (
                f'Private Declare PtrSafe Function {alias} Lib "{spec["dll"]}" '
                f'Alias "{spec["canonical_name"]}" ( _\n'
                f'        {params} _\n'
                f') As {spec["return_type"]["vba"]}'
            )
        else:
            decl = (
                f'Private Declare PtrSafe Function {alias} Lib "{spec["dll"]}" '
                f'Alias "{spec["canonical_name"]}" () As {spec["return_type"]["vba"]}'
            )

    structs = _render_vba_structs(spec)
    prefix_parts = []
    if structs:
        prefix_parts.append(structs)
    extra_vba = spec.get("extra_declarations", {}).get("vba")
    if extra_vba:
        prefix_parts.append(extra_vba)
    prefix = ("\n\n".join(prefix_parts) + "\n\n") if prefix_parts else ""
    if not include_example:
        return prefix + decl

    pre = _lines(spec.get("prelude", {}).get("vba"))
    call = _example_call(alias, spec, "vba")
    post = _lines(spec.get("postlude", {}).get("vba"))
    body = pre + call + post
    lines = [prefix + decl, "", "Sub MyMacro()", ""]
    lines.extend(f"    {line}" if line else "" for line in body)
    lines += ["", "End Sub"]
    return "\n".join(lines)


def generate(
    name: str,
    lang: str,
    include_example: bool = True,
    powershell_mode: str = "add-type",
) -> str:
    lang = lang.lower()
    if lang in {"ps", "powershell"}:
        if powershell_mode == "reflection":
            return generate_powershell_reflection(name, include_example)
        if powershell_mode != "add-type":
            raise ValueError("powershell_mode must be one of: add-type, reflection")
        return generate_powershell(name, include_example)
    if lang in {"cs", "csharp"}:
        if powershell_mode != "add-type":
            raise ValueError("--ps-mode only applies to PowerShell output")
        return generate_csharp(name, include_example)
    if lang == "vba":
        if powershell_mode != "add-type":
            raise ValueError("--ps-mode only applies to PowerShell output")
        return generate_vba(name, include_example)
    raise ValueError("lang must be one of: powershell, csharp, vba")

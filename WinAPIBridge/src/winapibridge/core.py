from __future__ import annotations

import json
from importlib.resources import files


def load_catalog() -> dict:
    path = files("winapibridge").joinpath("apis.json")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_api(name: str) -> tuple[str, dict]:
    catalog = load_catalog()
    needle = name.strip().lower()
    for alias, spec in catalog.items():
        if needle in {alias.lower(), spec["canonical_name"].lower()}:
            return alias, spec
    available = ", ".join(sorted(catalog))
    raise KeyError(f"Unknown API '{name}'. Available: {available}")


def _dllimport(spec: dict) -> str:
    args = [f'"{spec["dll"]}"']
    if spec.get("charset"):
        args.append(f'CharSet = CharSet.{spec["charset"]}')
    args.append(f'EntryPoint = "{spec["canonical_name"]}"')
    return f"[DllImport({', '.join(args)})]"


def _csharp_signature(alias: str, spec: dict) -> str:
    params = ",\n        ".join(
        f'{p["csharp"]} {p["name"]}' for p in spec["parameters"]
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


def generate_csharp(name: str, include_example: bool = True) -> str:
    alias, spec = resolve_api(name)
    signature = _csharp_signature(alias, spec)
    code = (
        "using System;\n"
        "using System.Runtime.InteropServices;\n\n"
        f"public static class {spec['class']}\n"
        "{\n"
        + "    " + signature.replace("\n", "\n    ") + "\n"
        "}"
    )
    if include_example:
        pre = spec.get("prelude", {}).get("csharp")
        call = f'{spec["class"]}.{alias}({", ".join(spec["example_args"]["csharp"])});'
        code += "\n\n"
        if pre:
            code += pre + "\n"
        code += call
    return code


def generate_powershell(name: str, include_example: bool = True) -> str:
    alias, spec = resolve_api(name)
    signature = _csharp_signature(alias, spec)
    var = f'${spec["class"]}'
    code = (
        f'{var} = @"\n'
        "using System;\n"
        "using System.Runtime.InteropServices;\n\n"
        f"public static class {spec['class']}\n"
        "{\n"
        + "    " + signature.replace("\n", "\n    ") + "\n"
        "}\n"
        '"@\n\n'
        f"Add-Type {var}"
    )
    if include_example:
        pre = spec.get("prelude", {}).get("powershell")
        call = f'[{spec["class"]}]::{alias}({", ".join(spec["example_args"]["powershell"])})'
        code += "\n\n"
        if pre:
            code += pre + "\n"
        code += call
        if alias == "GetPhysicallyInstalledSystemMemory":
            code += "\n$memoryKb"
    return code


def generate_vba(name: str, include_example: bool = True) -> str:
    alias, spec = resolve_api(name)
    params = ", _\n        ".join(
        f'{p["vba_by"]} {p["name"]} As {p["vba"]}' for p in spec["parameters"]
    )
    if params:
        decl = (
            f'Private Declare PtrSafe Function {alias} Lib "{spec["dll"]}" ( _\n'
            f'        {params} _\n'
            f') As {spec["return_type"]["vba"]}'
        )
    else:
        decl = (
            f'Private Declare PtrSafe Function {alias} Lib "{spec["dll"]}" () '
            f'As {spec["return_type"]["vba"]}'
        )
    if not include_example:
        return decl

    pre = spec.get("prelude", {}).get("vba")
    args = ", ".join(spec["example_args"]["vba"])
    lines = [decl, "", "Sub MyMacro()"]
    if pre:
        lines += ["", f"    {pre}"]
    lines += ["", f"    MsgBox {alias}({args})", "", "End Sub"]
    return "\n".join(lines)


def generate(name: str, lang: str, include_example: bool = True) -> str:
    lang = lang.lower()
    if lang in {"ps", "powershell"}:
        return generate_powershell(name, include_example)
    if lang in {"cs", "csharp"}:
        return generate_csharp(name, include_example)
    if lang == "vba":
        return generate_vba(name, include_example)
    raise ValueError("lang must be one of: powershell, csharp, vba")

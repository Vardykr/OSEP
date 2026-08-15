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


def generate(name: str, lang: str, include_example: bool = True) -> str:
    lang = lang.lower()
    if lang in {"ps", "powershell"}:
        return generate_powershell(name, include_example)
    if lang in {"cs", "csharp"}:
        return generate_csharp(name, include_example)
    if lang == "vba":
        return generate_vba(name, include_example)
    raise ValueError("lang must be one of: powershell, csharp, vba")

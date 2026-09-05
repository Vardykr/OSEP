from __future__ import annotations

import argparse

from .core import generate, load_catalog


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="winapibridge",
        description="Generate PowerShell, C#, or VBA declarations for known Win32 APIs.",
    )
    parser.add_argument("api", nargs="?", help="API name, e.g. MessageBox or GetDriveType")
    parser.add_argument(
        "-l",
        "--lang",
        choices=["powershell", "csharp", "vba"],
        default="powershell",
        help="Output language (default: powershell)",
    )
    parser.add_argument(
        "--ps-mode",
        choices=["add-type", "reflection"],
        default="add-type",
        help=(
            "PowerShell backend: add-type (default) or reflection. "
            "Reflection targets Windows PowerShell 5.1/.NET Framework and avoids Add-Type."
        ),
    )
    parser.add_argument(
        "--signature-only",
        action="store_true",
        help="Omit example invocation",
    )
    parser.add_argument("--list", action="store_true", help="List available APIs")
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="Search API names, descriptions, headers, and DLLs",
    )
    args = parser.parse_args()

    catalog = load_catalog()

    if args.list:
        for name, spec in sorted(catalog.items()):
            print(f"{name:38} -> {spec['canonical_name']} ({spec['dll']})")
        return

    if args.search:
        needle = args.search.lower()
        matches = [
            (name, spec)
            for name, spec in catalog.items()
            if needle in name.lower()
            or needle in spec.get("canonical_name", "").lower()
            or needle in spec.get("description", "").lower()
            or needle in spec.get("header", "").lower()
            or needle in spec.get("dll", "").lower()
        ]
        for name, spec in sorted(matches):
            print(f"{name:38} -> {spec['canonical_name']} ({spec['dll']})")
        return

    if not args.api:
        parser.error("API name is required unless --list or --search is used")

    if args.lang != "powershell" and args.ps_mode != "add-type":
        parser.error("--ps-mode only applies to --lang powershell")

    try:
        print(
            generate(
                args.api,
                args.lang,
                not args.signature_only,
                powershell_mode=args.ps_mode,
            )
        )
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

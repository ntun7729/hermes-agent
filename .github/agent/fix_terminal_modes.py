from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def update(path: str, replacements: list[tuple[str, str]]) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"{path}: expected one occurrence, found {count}: {old[:80]!r}")
        text = text.replace(old, new, 1)
    target.write_text(text, encoding="utf-8")


update(
    "apps/desktop/electron/terminal-mode.ts",
    [
        ("    .replace(/\\u0000/g, '')\n", "    .split('\\u0000')\n    .join('')\n"),
        (
            "  if (!requested) {\n    return distributions[0] || null\n  }\n",
            "  if (!requested) {\n    return null\n  }\n",
        ),
    ],
)

update(
    "tools/environments/windows_execution_mode.py",
    [
        (
            "    if not requested:\n        return distributions[0] if distributions else None\n",
            "    if not requested:\n        return None\n",
        )
    ],
)

update(
    "apps/desktop/src/app/right-sidebar/terminal/rail.tsx",
    [
        (
            "const RAIL_ACTION =\n",
            "type TerminalMode = 'smart' | 'wsl2' | 'windows-native'\n\n"
            "interface TerminalModeInfo {\n"
            "  configuredMode: TerminalMode\n"
            "  distribution: null | string\n"
            "  resolvedMode: 'windows-native' | 'wsl2'\n"
            "  supported: boolean\n"
            "  wslDistributions: string[]\n"
            "}\n\n"
            "const RAIL_ACTION =\n",
        ),
        ("Record<DesktopTerminalMode, string>", "Record<TerminalMode, string>"),
        ("Record<DesktopTerminalMode, string>", "Record<TerminalMode, string>"),
        ("useState<DesktopTerminalModeInfo | null>", "useState<TerminalModeInfo | null>"),
        ("(mode: DesktopTerminalMode)", "(mode: TerminalMode)"),
        ("as DesktopTerminalMode[]", "as TerminalMode[]"),
    ],
)

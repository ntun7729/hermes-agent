from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch_if_present(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old in text:
        text = text.replace(old, new, 1)
        target.write_text(text, encoding="utf-8")


patch_if_present(
    "apps/desktop/electron/terminal-mode.ts",
    "    .replace(/\\u0000/g, '')\n",
    "    .split('\\u0000')\n    .join('')\n",
)
patch_if_present(
    "apps/desktop/electron/terminal-mode.ts",
    "  if (!requested) {\n    return distributions[0] || null\n  }\n",
    "  if (!requested) {\n    return null\n  }\n",
)
patch_if_present(
    "tools/environments/windows_execution_mode.py",
    "    if not requested:\n        return distributions[0] if distributions else None\n",
    "    if not requested:\n        return None\n",
)

rail_path = ROOT / "apps/desktop/src/app/right-sidebar/terminal/rail.tsx"
rail = rail_path.read_text(encoding="utf-8")
if "type TerminalMode = 'smart' | 'wsl2' | 'windows-native'" not in rail:
    rail = rail.replace(
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
        1,
    )
rail = rail.replace("DesktopTerminalModeInfo", "TerminalModeInfo")
rail = rail.replace("DesktopTerminalMode", "TerminalMode")
rail_path.write_text(rail, encoding="utf-8")

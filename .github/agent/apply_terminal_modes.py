from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


TERMINAL_MODE_TS = r'''import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

export const TERMINAL_MODES = ['smart', 'wsl2', 'windows-native'] as const

export type TerminalMode = (typeof TERMINAL_MODES)[number]

interface ResolveTerminalModeOptions {
  configuredMode: TerminalMode
  cwd?: string
  isWindows: boolean
  wslDistributions: string[]
}

export function normalizeTerminalMode(value: unknown): TerminalMode {
  return TERMINAL_MODES.includes(value as TerminalMode) ? (value as TerminalMode) : 'smart'
}

export function terminalModeConfigPath(hermesHome: string): string {
  return path.join(hermesHome, 'desktop-terminal.json')
}

export function readTerminalMode(hermesHome: string): TerminalMode {
  const envMode = normalizeTerminalMode(process.env.HERMES_WINDOWS_EXECUTION_MODE)

  if (process.env.HERMES_WINDOWS_EXECUTION_MODE) {
    return envMode
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(terminalModeConfigPath(hermesHome), 'utf8'))

    return normalizeTerminalMode(parsed?.mode)
  } catch {
    return 'smart'
  }
}

export function writeTerminalMode(hermesHome: string, value: unknown): TerminalMode {
  const mode = normalizeTerminalMode(value)
  const target = terminalModeConfigPath(hermesHome)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  fs.writeFileSync(target, `${JSON.stringify({ mode }, null, 2)}\n`, 'utf8')

  return mode
}

export function parseWslDistributions(output: unknown): string[] {
  const text = Buffer.isBuffer(output) ? output.toString('utf8') : String(output || '')
  const seen = new Set<string>()

  return text
    .replace(/\u0000/g, '')
    .split(/\r?\n/)
    .map(line => line.replace(/^\*\s*/, '').trim())
    .filter(name => {
      const key = name.toLowerCase()

      if (!name || seen.has(key)) {
        return false
      }

      seen.add(key)

      return true
    })
}

export function detectWslDistributions(
  run: typeof execFileSync = execFileSync
): string[] {
  try {
    const output = run('wsl.exe', ['--list', '--quiet'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      windowsHide: true
    })

    return parseWslDistributions(output)
  } catch {
    return []
  }
}

export function distributionFromWslPath(cwd: string): string | null {
  const match = /^\\\\(?:wsl\.localhost|wsl\$)\\([^\\/]+)(?:[\\/]|$)/i.exec(String(cwd || ''))

  return match?.[1] || null
}

function matchingDistribution(distributions: string[], requested: string | null): string | null {
  if (!requested) {
    return distributions[0] || null
  }

  return distributions.find(name => name.toLowerCase() === requested.toLowerCase()) || null
}

export function resolveWindowsTerminalMode({
  configuredMode,
  cwd = '',
  isWindows,
  wslDistributions
}: ResolveTerminalModeOptions): { distribution: string | null; mode: 'windows-native' | 'wsl2' } {
  if (!isWindows || configuredMode === 'windows-native') {
    return { distribution: null, mode: 'windows-native' }
  }

  const pathDistribution = matchingDistribution(wslDistributions, distributionFromWslPath(cwd))

  if (configuredMode === 'smart') {
    return pathDistribution
      ? { distribution: pathDistribution, mode: 'wsl2' }
      : { distribution: null, mode: 'windows-native' }
  }

  const distribution = pathDistribution || wslDistributions[0] || null

  return distribution ? { distribution, mode: 'wsl2' } : { distribution: null, mode: 'windows-native' }
}

export function toWslPath(cwd: string, distribution?: string | null): string {
  const value = String(cwd || '').trim()

  if (!value) {
    return '~'
  }

  const unc = /^\\\\(?:wsl\.localhost|wsl\$)\\([^\\/]+)(?:[\\/](.*))?$/i.exec(value)

  if (unc) {
    if (!distribution || unc[1].toLowerCase() === distribution.toLowerCase()) {
      return `/${String(unc[2] || '').replace(/\\/g, '/').replace(/^\/+/, '')}`.replace(/\/$/, '') || '/'
    }
  }

  const drive = /^([a-zA-Z]):[\\/]*(.*)$/.exec(value)

  if (drive) {
    const tail = drive[2].replace(/\\/g, '/').replace(/^\/+/, '')

    return `/mnt/${drive[1].toLowerCase()}${tail ? `/${tail}` : ''}`
  }

  return value.replace(/\\/g, '/')
}
'''

TERMINAL_MODE_TEST_TS = r'''import { describe, expect, it } from 'vitest'

import {
  distributionFromWslPath,
  normalizeTerminalMode,
  parseWslDistributions,
  resolveWindowsTerminalMode,
  toWslPath
} from './terminal-mode'

describe('terminal mode', () => {
  it('normalizes unknown values to smart', () => {
    expect(normalizeTerminalMode('wsl2')).toBe('wsl2')
    expect(normalizeTerminalMode('bad')).toBe('smart')
  })

  it('parses the null-padded output returned by wsl.exe', () => {
    expect(parseWslDistributions('U\u0000b\u0000u\u0000n\u0000t\u0000u\u0000\r\u0000\n\u0000D\u0000e\u0000b\u0000i\u0000a\u0000n\u0000')).toEqual([
      'Ubuntu',
      'Debian'
    ])
  })

  it('uses WSL for a matching UNC project in smart mode', () => {
    expect(
      resolveWindowsTerminalMode({
        configuredMode: 'smart',
        cwd: '\\\\wsl.localhost\\Ubuntu\\home\\shay\\project',
        isWindows: true,
        wslDistributions: ['Ubuntu']
      })
    ).toEqual({ distribution: 'Ubuntu', mode: 'wsl2' })
  })

  it('keeps ordinary Windows projects native in smart mode', () => {
    expect(
      resolveWindowsTerminalMode({
        configuredMode: 'smart',
        cwd: 'C:\\Users\\shay\\project',
        isWindows: true,
        wslDistributions: ['Ubuntu']
      })
    ).toEqual({ distribution: null, mode: 'windows-native' })
  })

  it('forces the first installed distro in WSL2 mode', () => {
    expect(
      resolveWindowsTerminalMode({
        configuredMode: 'wsl2',
        cwd: 'C:\\Users\\shay\\project',
        isWindows: true,
        wslDistributions: ['Ubuntu', 'Debian']
      })
    ).toEqual({ distribution: 'Ubuntu', mode: 'wsl2' })
  })

  it('maps Windows and WSL UNC paths', () => {
    expect(toWslPath('C:\\Users\\shay\\project', 'Ubuntu')).toBe('/mnt/c/Users/shay/project')
    expect(toWslPath('\\\\wsl$\\Ubuntu\\home\\shay\\project', 'Ubuntu')).toBe('/home/shay/project')
    expect(distributionFromWslPath('\\\\wsl.localhost\\Ubuntu\\home\\shay')).toBe('Ubuntu')
  })
})
'''

WINDOWS_MODE_PY = r'''"""Shared Windows execution-mode selection for Desktop PTYs and agent commands."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hermes_cli._subprocess_compat import windows_hide_flags

VALID_MODES = frozenset({"smart", "wsl2", "windows-native"})


@dataclass(frozen=True)
class WindowsExecutionMode:
    configured: str
    resolved: str
    distribution: str | None = None


def normalize_mode(value: object) -> str:
    return value if isinstance(value, str) and value in VALID_MODES else "smart"


def _config_path() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home() / "desktop-terminal.json"
    except Exception:
        return Path.home() / ".hermes" / "desktop-terminal.json"


def read_configured_mode() -> str:
    override = os.environ.get("HERMES_WINDOWS_EXECUTION_MODE")
    if override:
        return normalize_mode(override)

    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        return normalize_mode(data.get("mode"))
    except Exception:
        return "smart"


def _decode_wsl_output(raw: bytes) -> str:
    if b"\x00" in raw:
        for encoding in ("utf-16-le", "utf-8"):
            try:
                return raw.decode(encoding).replace("\x00", "")
            except UnicodeError:
                pass
    return raw.decode("utf-8", errors="replace").replace("\x00", "")


def parse_wsl_distributions(raw: bytes | str) -> list[str]:
    text = _decode_wsl_output(raw) if isinstance(raw, bytes) else raw.replace("\x00", "")
    result: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        name = re.sub(r"^\*\s*", "", line).strip()
        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            result.append(name)
    return result


def wsl_executable() -> str | None:
    return shutil.which("wsl.exe") or shutil.which("wsl")


def list_wsl_distributions() -> list[str]:
    executable = wsl_executable()
    if not executable:
        return []
    try:
        completed = subprocess.run(
            [executable, "--list", "--quiet"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=windows_hide_flags(),
        )
    except OSError:
        return []
    return parse_wsl_distributions(completed.stdout) if completed.returncode == 0 else []


def distribution_from_wsl_path(cwd: str) -> str | None:
    match = re.match(r"^\\\\(?:wsl\.localhost|wsl\$)\\([^\\/]+)(?:[\\/]|$)", cwd or "", re.I)
    return match.group(1) if match else None


def _matching_distribution(distributions: list[str], requested: str | None) -> str | None:
    if not requested:
        return distributions[0] if distributions else None
    requested_key = requested.casefold()
    return next((name for name in distributions if name.casefold() == requested_key), None)


def resolve_windows_execution_mode(
    cwd: str = "",
    *,
    configured: str | None = None,
    distributions: list[str] | None = None,
    is_windows: bool | None = None,
) -> WindowsExecutionMode:
    if is_windows is None:
        is_windows = os.name == "nt"
    configured_mode = normalize_mode(configured if configured is not None else read_configured_mode())
    available = list_wsl_distributions() if distributions is None and is_windows else (distributions or [])

    if not is_windows or configured_mode == "windows-native":
        return WindowsExecutionMode(configured_mode, "windows-native")

    path_distribution = _matching_distribution(available, distribution_from_wsl_path(cwd))
    if configured_mode == "smart":
        if path_distribution:
            return WindowsExecutionMode(configured_mode, "wsl2", path_distribution)
        return WindowsExecutionMode(configured_mode, "windows-native")

    distribution = path_distribution or (available[0] if available else None)
    if distribution:
        return WindowsExecutionMode(configured_mode, "wsl2", distribution)
    return WindowsExecutionMode(configured_mode, "windows-native")


def windows_to_wsl_path(value: str, distribution: str | None = None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "~"

    unc = re.match(r"^\\\\(?:wsl\.localhost|wsl\$)\\([^\\/]+)(?:[\\/](.*))?$", raw, re.I)
    if unc and (not distribution or unc.group(1).casefold() == distribution.casefold()):
        tail = (unc.group(2) or "").replace("\\", "/").lstrip("/")
        return f"/{tail}" if tail else "/"

    drive = re.match(r"^([a-zA-Z]):[\\/]*(.*)$", raw)
    if drive:
        tail = (drive.group(2) or "").replace("\\", "/").lstrip("/")
        suffix = f"/{tail}" if tail else ""
        return f"/mnt/{drive.group(1).lower()}{suffix}"

    return raw.replace("\\", "/")


def wsl_to_windows_path(value: str, distribution: str | None) -> str:
    raw = (value or "").strip()
    mount = re.match(r"^/mnt/([a-zA-Z])(?:/(.*))?$", raw)
    if mount:
        tail = (mount.group(2) or "").replace("/", "\\")
        return f"{mount.group(1).upper()}:\\{tail}" if tail else f"{mount.group(1).upper()}:\\"
    if raw.startswith("/") and distribution:
        tail = raw.lstrip("/").replace("/", "\\")
        base = f"\\\\wsl.localhost\\{distribution}"
        return f"{base}\\{tail}" if tail else base
    return raw


def build_wsl_bash_args(command: str, cwd: str, *, login: bool, distribution: str) -> list[str]:
    executable = wsl_executable()
    if not executable:
        raise RuntimeError("WSL2 mode is selected, but wsl.exe is not available")
    shell_flag = "-lc" if login else "-c"
    return [
        executable,
        "--distribution",
        distribution,
        "--cd",
        windows_to_wsl_path(cwd, distribution),
        "--exec",
        "bash",
        shell_flag,
        command,
    ]
'''

WINDOWS_MODE_TEST_PY = r'''from tools.environments.windows_execution_mode import (
    distribution_from_wsl_path,
    normalize_mode,
    parse_wsl_distributions,
    resolve_windows_execution_mode,
    windows_to_wsl_path,
    wsl_to_windows_path,
)


def test_normalize_mode_defaults_to_smart():
    assert normalize_mode("wsl2") == "wsl2"
    assert normalize_mode("unknown") == "smart"


def test_parse_utf16_wsl_output():
    raw = "Ubuntu\r\nDebian\r\n".encode("utf-16-le")
    assert parse_wsl_distributions(raw) == ["Ubuntu", "Debian"]


def test_smart_mode_uses_wsl_unc_project():
    result = resolve_windows_execution_mode(
        r"\\wsl.localhost\Ubuntu\home\shay\project",
        configured="smart",
        distributions=["Ubuntu"],
        is_windows=True,
    )
    assert result.resolved == "wsl2"
    assert result.distribution == "Ubuntu"


def test_smart_mode_keeps_drive_project_native():
    result = resolve_windows_execution_mode(
        r"C:\Users\shay\project",
        configured="smart",
        distributions=["Ubuntu"],
        is_windows=True,
    )
    assert result.resolved == "windows-native"


def test_explicit_wsl_uses_first_distribution():
    result = resolve_windows_execution_mode(
        r"C:\Users\shay\project",
        configured="wsl2",
        distributions=["Ubuntu", "Debian"],
        is_windows=True,
    )
    assert result.resolved == "wsl2"
    assert result.distribution == "Ubuntu"


def test_path_bridges():
    assert windows_to_wsl_path(r"C:\Users\shay\project", "Ubuntu") == "/mnt/c/Users/shay/project"
    assert windows_to_wsl_path(r"\\wsl$\Ubuntu\home\shay", "Ubuntu") == "/home/shay"
    assert wsl_to_windows_path("/mnt/c/Users/shay", "Ubuntu") == r"C:\Users\shay"
    assert wsl_to_windows_path("/home/shay", "Ubuntu") == r"\\wsl.localhost\Ubuntu\home\shay"
    assert distribution_from_wsl_path(r"\\wsl.localhost\Ubuntu\home") == "Ubuntu"
'''


def patch_main() -> None:
    path = "apps/desktop/electron/main.ts"
    text = read(path)
    text = replace_once(
        text,
        "import { readWslWindowsClipboardImage } from './wsl-clipboard-image'\n",
        "import { readWslWindowsClipboardImage } from './wsl-clipboard-image'\n"
        "import {\n"
        "  detectWslDistributions,\n"
        "  readTerminalMode,\n"
        "  resolveWindowsTerminalMode,\n"
        "  toWslPath,\n"
        "  writeTerminalMode\n"
        "} from './terminal-mode'\n",
        label="main import",
    )

    pattern = re.compile(r"function terminalShellCommand\(\) \{.*?\n\}\n\nfunction safeTerminalCwd", re.S)
    replacement = r'''function desktopTerminalModeInfo(cwd = '') {
  const configuredMode = readTerminalMode(HERMES_HOME)
  const wslDistributions = IS_WINDOWS ? detectWslDistributions() : []
  const resolution = resolveWindowsTerminalMode({
    configuredMode,
    cwd,
    isWindows: IS_WINDOWS,
    wslDistributions
  })

  return {
    configuredMode,
    distribution: resolution.distribution,
    resolvedMode: resolution.mode,
    supported: IS_WINDOWS,
    wslDistributions
  }
}

function terminalShellCommand(cwd) {
  const modeInfo = desktopTerminalModeInfo(cwd)
  const withMode = spec => ({ ...spec, ...modeInfo })

  if (IS_WINDOWS && modeInfo.resolvedMode === 'wsl2') {
    if (!modeInfo.distribution) {
      throw new Error('WSL2 mode is selected, but no WSL2 distribution is installed.')
    }

    return withMode({
      args: [
        '--distribution',
        modeInfo.distribution,
        '--cd',
        toWslPath(cwd, modeInfo.distribution),
        '--exec',
        'bash',
        '-l'
      ],
      command: 'wsl.exe',
      name: `wsl2:${modeInfo.distribution}`
    })
  }

  // HERMES_DESKTOP_SHELL is the cross-platform escape hatch (a path or a bare
  // name on PATH); $SHELL is honored on POSIX, where it's the user's canonical
  // choice, but ignored on Windows, where it's usually a stray MSYS/Git path
  // node-pty can't spawn natively.
  const override = (process.env.HERMES_DESKTOP_SHELL || (IS_WINDOWS ? '' : process.env.SHELL) || '').trim()

  if (override) {
    const resolved = isExecutableFile(override) ? override : findOnPath(override)

    if (resolved) {
      return withMode(shellSpecFor(resolved))
    }
  }

  if (IS_WINDOWS) {
    return withMode(windowsShellSpec())
  }

  const shellPath = ['/bin/zsh', '/bin/bash', '/bin/sh'].find(candidate => isExecutableFile(candidate))

  return withMode(posixShellSpec(shellPath || '/bin/sh'))
}

function safeTerminalCwd'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"terminalShellCommand replacement count={count}")

    start_anchor = "ipcMain.handle('hermes:terminal:start', async (event, payload = {}) => {\n"
    handlers = r'''ipcMain.handle('hermes:terminal-mode:get', (_event, cwd) =>
  desktopTerminalModeInfo(safeTerminalCwd(cwd))
)
ipcMain.handle('hermes:terminal-mode:set', (_event, mode, cwd) => {
  writeTerminalMode(HERMES_HOME, mode)

  return desktopTerminalModeInfo(safeTerminalCwd(cwd))
})

'''
    text = replace_once(text, start_anchor, handlers + start_anchor, label="terminal mode handlers")
    text = replace_once(
        text,
        "  const id = crypto.randomUUID()\n  const { args, command, name } = terminalShellCommand()\n  const cwd = safeTerminalCwd(payload?.cwd)\n",
        "  const id = crypto.randomUUID()\n  const cwd = safeTerminalCwd(payload?.cwd)\n"
        "  const { args, command, configuredMode, distribution, name, resolvedMode } = terminalShellCommand(cwd)\n",
        label="terminal start resolution",
    )
    text = replace_once(
        text,
        "  return { cwd, id, shell: name }\n",
        "  return { configuredMode, cwd, distribution, id, mode: resolvedMode, shell: name }\n",
        label="terminal start return",
    )
    write(path, text)


def patch_preload() -> None:
    path = "apps/desktop/electron/preload.ts"
    text = read(path)
    text = replace_once(
        text,
        "  terminal: {\n    cwd: id => ipcRenderer.invoke('hermes:terminal:cwd', id),\n",
        "  terminal: {\n"
        "    mode: {\n"
        "      get: cwd => ipcRenderer.invoke('hermes:terminal-mode:get', cwd),\n"
        "      set: (mode, cwd) => ipcRenderer.invoke('hermes:terminal-mode:set', mode, cwd)\n"
        "    },\n"
        "    cwd: id => ipcRenderer.invoke('hermes:terminal:cwd', id),\n",
        label="preload terminal mode",
    )
    write(path, text)


def patch_global_types() -> None:
    path = "apps/desktop/src/global.d.ts"
    text = read(path)
    text = replace_once(
        text,
        "      terminal: {\n        /** Best-effort current working directory of the live PTY child (POSIX\n",
        "      terminal: {\n"
        "        mode: {\n"
        "          get: (cwd?: string) => Promise<DesktopTerminalModeInfo>\n"
        "          set: (mode: DesktopTerminalMode, cwd?: string) => Promise<DesktopTerminalModeInfo>\n"
        "        }\n"
        "        /** Best-effort current working directory of the live PTY child (POSIX\n",
        label="global terminal mode API",
    )
    marker = "export interface DesktopMarketplaceSearchItem {\n"
    declarations = r'''export type DesktopTerminalMode = 'smart' | 'wsl2' | 'windows-native'

export interface DesktopTerminalModeInfo {
  configuredMode: DesktopTerminalMode
  distribution: null | string
  resolvedMode: 'windows-native' | 'wsl2'
  supported: boolean
  wslDistributions: string[]
}

'''
    text = replace_once(text, marker, declarations + marker, label="terminal mode declarations")
    write(path, text)


def patch_rail() -> None:
    path = "apps/desktop/src/app/right-sidebar/terminal/rail.tsx"
    text = read(path)
    text = replace_once(
        text,
        "import { useStore } from '@nanostores/react'\n",
        "import { useStore } from '@nanostores/react'\nimport { useEffect, useState } from 'react'\n",
        label="rail react imports",
    )
    text = replace_once(
        text,
        "import { Codicon } from '@/components/ui/codicon'\n",
        "import { Codicon } from '@/components/ui/codicon'\n"
        "import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'\n",
        label="rail dropdown import",
    )
    rail_action = "const RAIL_ACTION =\n  'grid size-6 place-items-center rounded text-(--ui-text-tertiary) transition-colors hover:bg-(--chrome-action-hover) hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring [-webkit-app-region:no-drag]'\n"
    mode_defs = rail_action + r'''
const TERMINAL_MODE_LABELS: Record<DesktopTerminalMode, string> = {
  smart: 'Smart',
  wsl2: 'WSL2',
  'windows-native': 'Windows Native'
}

const TERMINAL_MODE_ICONS: Record<DesktopTerminalMode, string> = {
  smart: 'server-environment',
  wsl2: 'terminal-linux',
  'windows-native': 'terminal-powershell'
}
'''
    text = replace_once(text, rail_action, mode_defs, label="rail mode definitions")
    state_anchor = "  const newHint = bindings['view.newTerminal']?.[0]\n"
    state_block = state_anchor + r'''
  const [modeInfo, setModeInfo] = useState<DesktopTerminalModeInfo | null>(null)

  useEffect(() => {
    const api = window.hermesDesktop?.terminal?.mode

    if (!api) {
      return
    }

    void api.get().then(setModeInfo).catch(() => setModeInfo(null))
  }, [])

  const selectMode = (mode: DesktopTerminalMode) => {
    const api = window.hermesDesktop?.terminal?.mode

    if (!api) {
      return
    }

    void api.set(mode).then(setModeInfo).catch(() => undefined)
  }
'''
    text = replace_once(text, state_anchor, state_block, label="rail mode state")
    bottom_anchor = "      <div className=\"flex shrink-0 flex-col items-center pb-1.5\">\n        <Tip label={t.rightSidebar.terminalHide} side=\"left\">\n"
    bottom_block = r'''      <div className="flex shrink-0 flex-col items-center gap-0.5 pb-1.5">
        {modeInfo?.supported && (
          <DropdownMenu>
            <Tip
              label={`Terminal mode: ${TERMINAL_MODE_LABELS[modeInfo.configuredMode]} (new terminals; agent commands update immediately)`}
              side="left"
            >
              <DropdownMenuTrigger asChild>
                <button
                  aria-label={`Terminal mode: ${TERMINAL_MODE_LABELS[modeInfo.configuredMode]}`}
                  className={RAIL_ACTION}
                  type="button"
                >
                  <Codicon name={TERMINAL_MODE_ICONS[modeInfo.configuredMode]} size="0.8125rem" />
                </button>
              </DropdownMenuTrigger>
            </Tip>
            <DropdownMenuContent align="end" side="left">
              {(Object.keys(TERMINAL_MODE_LABELS) as DesktopTerminalMode[]).map(mode => (
                <DropdownMenuItem
                  disabled={mode === 'wsl2' && modeInfo.wslDistributions.length === 0}
                  key={mode}
                  onSelect={() => selectMode(mode)}
                >
                  <Codicon name={TERMINAL_MODE_ICONS[mode]} />
                  <span className="flex-1">{TERMINAL_MODE_LABELS[mode]}</span>
                  {modeInfo.configuredMode === mode && <Codicon name="check" />}
                </DropdownMenuItem>
              ))}
              {modeInfo.configuredMode === 'smart' && (
                <div className="max-w-56 px-2 py-1 text-[0.65rem] text-(--ui-text-tertiary)">
                  Smart uses WSL2 for projects opened through a WSL UNC path; other projects stay Windows native.
                </div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
        <Tip label={t.rightSidebar.terminalHide} side="left">
'''
    text = replace_once(text, bottom_anchor, bottom_block, label="rail mode selector")
    write(path, text)


def patch_local_environment() -> None:
    path = "tools/environments/local.py"
    text = read(path)
    text = replace_once(
        text,
        "from hermes_cli._subprocess_compat import windows_hide_flags\n",
        "from hermes_cli._subprocess_compat import windows_hide_flags\n"
        "from tools.environments.windows_execution_mode import (\n"
        "    build_wsl_bash_args,\n"
        "    resolve_windows_execution_mode,\n"
        "    windows_to_wsl_path,\n"
        "    wsl_to_windows_path,\n"
        ")\n",
        label="local environment imports",
    )

    text = replace_once(
        text,
        "    def __init__(self, cwd: str = \"\", timeout: int = 60, env: dict = None):\n"
        "        if cwd:\n"
        "            cwd = os.path.expanduser(cwd)\n"
        "        super().__init__(cwd=cwd or os.getcwd(), timeout=timeout, env=env)\n"
        "        self.init_session()\n",
        "    def __init__(self, cwd: str = \"\", timeout: int = 60, env: dict = None):\n"
        "        if cwd:\n"
        "            cwd = os.path.expanduser(cwd)\n"
        "        super().__init__(cwd=cwd or os.getcwd(), timeout=timeout, env=env)\n"
        "        self._windows_execution = resolve_windows_execution_mode(self.cwd) if _IS_WINDOWS else None\n"
        "        self.init_session()\n\n"
        "    def _before_execute(self) -> None:\n"
        "        if not _IS_WINDOWS:\n"
        "            return\n"
        "        current = resolve_windows_execution_mode(self.cwd)\n"
        "        previous = self._windows_execution\n"
        "        if previous and (current.resolved, current.distribution) == (previous.resolved, previous.distribution):\n"
        "            return\n"
        "        self._windows_execution = current\n"
        "        self._snapshot_ready = False\n"
        "        self._prefer_nonlogin = False\n"
        "        self.init_session()\n",
        label="local mode refresh",
    )

    text = replace_once(
        text,
        "    @staticmethod\n"
        "    def _quote_cwd_for_cd(cwd: str) -> str:\n"
        "        \"\"\"Use native paths for Python, but Git Bash-friendly paths for cd.\"\"\"\n"
        "        return BaseEnvironment._quote_cwd_for_cd(_windows_to_msys_path(cwd))\n\n"
        "    def _quote_shell_path(self, path: str) -> str:\n"
        "        \"\"\"Rewrite native/mixed Windows paths before quoting for Git Bash.\"\"\"\n"
        "        return _quote_bash_path(path)\n",
        "    @staticmethod\n"
        "    def _quote_cwd_for_cd(cwd: str) -> str:\n"
        "        \"\"\"Translate the host cwd for the currently selected Windows environment.\"\"\"\n"
        "        if _IS_WINDOWS:\n"
        "            mode = resolve_windows_execution_mode(cwd)\n"
        "            if mode.resolved == \"wsl2\":\n"
        "                return BaseEnvironment._quote_cwd_for_cd(windows_to_wsl_path(cwd, mode.distribution))\n"
        "        return BaseEnvironment._quote_cwd_for_cd(_windows_to_msys_path(cwd))\n\n"
        "    def _quote_shell_path(self, path: str) -> str:\n"
        "        \"\"\"Rewrite host paths for Git Bash or WSL2 before shell interpolation.\"\"\"\n"
        "        if _IS_WINDOWS:\n"
        "            mode = resolve_windows_execution_mode(self.cwd)\n"
        "            if mode.resolved == \"wsl2\":\n"
        "                import shlex\n"
        "                return shlex.quote(windows_to_wsl_path(path, mode.distribution))\n"
        "        return _quote_bash_path(path)\n",
        label="local path quoting",
    )

    pattern = re.compile(
        r"    def _run_bash\(self, cmd_string: str, \*, login: bool = False,\n"
        r"                  timeout: int = 120,\n"
        r"                  stdin_data: str \| None = None\) -> subprocess\.Popen:\n"
        r".*?\n        return proc\n",
        re.S,
    )
    replacement = r'''    def _run_bash(self, cmd_string: str, *, login: bool = False,
                  timeout: int = 120,
                  stdin_data: str | None = None) -> subprocess.Popen:
        mode = resolve_windows_execution_mode(self.cwd) if _IS_WINDOWS else None

        # Recover when the cwd has been deleted out from under us — usually by
        # a previous tool call that ran ``rm -rf`` on its own working dir.
        safe_cwd = _resolve_safe_cwd(self.cwd)
        if safe_cwd != self.cwd:
            normalized = _msys_to_windows_path(self.cwd) if _IS_WINDOWS else self.cwd
            if safe_cwd != normalized:
                logger.warning(
                    "LocalEnvironment cwd %r is missing on disk; "
                    "falling back to %r so terminal commands keep working.",
                    self.cwd,
                    safe_cwd,
                )
            self.cwd = safe_cwd

        if mode and mode.resolved == "wsl2":
            if not mode.distribution:
                raise RuntimeError("WSL2 mode is selected, but no WSL2 distribution is installed")
            args = build_wsl_bash_args(
                cmd_string,
                self.cwd,
                login=login,
                distribution=mode.distribution,
            )
        else:
            bash = _find_bash()
            # For native login-shell invocations, source the user's configured
            # shell init files so nvm/asdf/pyenv additions reach the snapshot.
            if login:
                init_files = _resolve_shell_init_files()
                if init_files:
                    cmd_string = _prepend_shell_init(cmd_string, init_files)
            args = [bash, "-l", "-c", cmd_string] if login else [bash, "-c", cmd_string]

        run_env = _make_run_env(self.env)
        _popen_cwd = self.cwd
        if mode and mode.resolved == "wsl2" and self.cwd.startswith("\\\\"):
            # CreateProcess cannot reliably use a WSL UNC directory as the host
            # working directory. wsl.exe --cd still enters the requested path.
            _popen_cwd = tempfile.gettempdir()

        _popen_kwargs = {"creationflags": windows_hide_flags()} if _IS_WINDOWS else {}

        proc = subprocess.Popen(
            args,
            text=True,
            env=run_env,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            start_new_session=True,
            cwd=_popen_cwd,
            **_popen_kwargs,
        )
        if not _IS_WINDOWS:
            try:
                proc._hermes_pgid = os.getpgid(proc.pid)
            except ProcessLookupError:
                pass

        if stdin_data is not None:
            _pipe_stdin(proc, stdin_data)

        return proc
'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"local _run_bash replacement count={count}")

    text = replace_once(
        text,
        "            if _IS_WINDOWS:\n                cwd_path = _msys_to_windows_path(cwd_path)\n",
        "            if _IS_WINDOWS:\n"
        "                mode = resolve_windows_execution_mode(self.cwd)\n"
        "                cwd_path = (\n"
        "                    wsl_to_windows_path(cwd_path, mode.distribution)\n"
        "                    if mode.resolved == \"wsl2\"\n"
        "                    else _msys_to_windows_path(cwd_path)\n"
        "                )\n",
        label="local cwd file bridge",
    )
    text = replace_once(
        text,
        "            normalized = _msys_to_windows_path(self.cwd) if _IS_WINDOWS else self.cwd\n"
        "            if normalized and os.path.isdir(normalized):\n",
        "            if _IS_WINDOWS:\n"
        "                mode = resolve_windows_execution_mode(prev_cwd)\n"
        "                normalized = (\n"
        "                    wsl_to_windows_path(self.cwd, mode.distribution)\n"
        "                    if mode.resolved == \"wsl2\"\n"
        "                    else _msys_to_windows_path(self.cwd)\n"
        "                )\n"
        "            else:\n"
        "                normalized = self.cwd\n"
        "            if normalized and os.path.isdir(normalized):\n",
        label="local stdout cwd bridge",
    )
    write(path, text)


def main() -> None:
    write("apps/desktop/electron/terminal-mode.ts", TERMINAL_MODE_TS)
    write("apps/desktop/electron/terminal-mode.test.ts", TERMINAL_MODE_TEST_TS)
    write("tools/environments/windows_execution_mode.py", WINDOWS_MODE_PY)
    write("tests/tools/test_windows_execution_mode.py", WINDOWS_MODE_TEST_PY)
    patch_main()
    patch_preload()
    patch_global_types()
    patch_rail()
    patch_local_environment()


if __name__ == "__main__":
    main()

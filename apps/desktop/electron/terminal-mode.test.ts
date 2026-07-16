import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  distributionFromWslPath,
  normalizeTerminalMode,
  parseWslDistributions,
  readTerminalMode,
  resolveWindowsTerminalMode,
  terminalModeConfigPath,
  toWslPath,
  writeTerminalMode
} from './terminal-mode'

describe('terminal mode', () => {
  it('normalizes unknown values to smart', () => {
    expect(normalizeTerminalMode('wsl2')).toBe('wsl2')
    expect(normalizeTerminalMode('bad')).toBe('smart')
  })

  it('reads and updates terminal.windows_execution_mode in config.yaml', () => {
    const hermesHome = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-terminal-mode-'))
    const configPath = terminalModeConfigPath(hermesHome)

    try {
      fs.writeFileSync(
        configPath,
        ['model:', '  provider: test', '', 'terminal:', '  timeout: 120', '  windows_execution_mode: smart', ''].join('\n'),
        'utf8'
      )

      expect(readTerminalMode(hermesHome)).toBe('smart')
      expect(writeTerminalMode(hermesHome, 'wsl2')).toBe('wsl2')
      expect(readTerminalMode(hermesHome)).toBe('wsl2')
      expect(fs.readFileSync(configPath, 'utf8')).toContain('  windows_execution_mode: wsl2')
      expect(fs.readFileSync(configPath, 'utf8')).toContain('  timeout: 120')
    } finally {
      fs.rmSync(hermesHome, { force: true, recursive: true })
    }
  })

  it('creates the terminal section when config.yaml does not contain one', () => {
    const hermesHome = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-terminal-mode-'))

    try {
      fs.writeFileSync(terminalModeConfigPath(hermesHome), 'model:\n  provider: test\n', 'utf8')
      writeTerminalMode(hermesHome, 'windows-native')

      expect(readTerminalMode(hermesHome)).toBe('windows-native')
      expect(fs.readFileSync(terminalModeConfigPath(hermesHome), 'utf8')).toContain(
        'terminal:\n  windows_execution_mode: windows-native'
      )
    } finally {
      fs.rmSync(hermesHome, { force: true, recursive: true })
    }
  })

  it('parses the null-padded output returned by wsl.exe', () => {
    expect(
      parseWslDistributions(
        'U\u0000b\u0000u\u0000n\u0000t\u0000u\u0000\r\u0000\n\u0000D\u0000e\u0000b\u0000i\u0000a\u0000n\u0000'
      )
    ).toEqual(['Ubuntu', 'Debian'])
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

  it('returns wsl2 with null distribution when configured as wsl2 but no distributions are installed', () => {
    expect(
      resolveWindowsTerminalMode({
        configuredMode: 'wsl2',
        cwd: 'C:\\Users\\shay\\project',
        isWindows: true,
        wslDistributions: []
      })
    ).toEqual({ distribution: null, mode: 'wsl2' })
  })

  it('maps Windows and WSL UNC paths', () => {
    expect(toWslPath('C:\\Users\\shay\\project', 'Ubuntu')).toBe('/mnt/c/Users/shay/project')
    expect(toWslPath('\\\\wsl$\\Ubuntu\\home\\shay\\project', 'Ubuntu')).toBe('/home/shay/project')
    expect(distributionFromWslPath('\\\\wsl.localhost\\Ubuntu\\home\\shay')).toBe('Ubuntu')
  })
})

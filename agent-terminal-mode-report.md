# Terminal mode integration report

## Electron shell helpers
3298:function resolveHermesBackend(backendArgs) {
6691:async function startHermes() {
8263:function terminalShellCommand(cwd) {
8310:function safeTerminalCwd(cwd) {
8322:function terminalShellEnv() {

## Backend environment wiring
33:import { buildDesktopBackendEnv, normalizeHermesHomeRoot } from './backend-env'
1474:    buildDesktopBackendEnv,
3263:    env: buildDesktopBackendEnv({
3287:    env: buildDesktopBackendEnv({
6548:        // the child process. Inherited TERMINAL_CWD (or a stale config bridge)
6550:        TERMINAL_CWD: hermesCwd,
6789:          TERMINAL_CWD: hermesCwd,

## Renderer integration
apps/desktop/src/app/right-sidebar/terminal/chrome.tsx:4:import { TerminalRail } from './rail'
apps/desktop/src/app/right-sidebar/terminal/chrome.tsx:21:      {terminals.length > 0 && <TerminalRail />}
apps/desktop/src/app/right-sidebar/terminal/rail.tsx:50:export function TerminalRail() {
apps/desktop/src/app/right-sidebar/terminal/rail.tsx:101:          <TerminalRailItem
apps/desktop/src/app/right-sidebar/terminal/rail.tsx:179:interface TerminalRailItemProps {
apps/desktop/src/app/right-sidebar/terminal/rail.tsx:187:function TerminalRailItem({ active, canCloseOthers, index, term, toggleHint }: TerminalRailItemProps) {
apps/desktop/src/app/right-sidebar/terminal/rail.test.tsx:6:import { TerminalRail } from './rail'
apps/desktop/src/app/right-sidebar/terminal/rail.test.tsx:9:describe('TerminalRail', () => {
apps/desktop/src/app/right-sidebar/terminal/rail.test.tsx:23:    const view = render(<TerminalRail />)

## Python local environment
423:    # spawn path (process_registry.spawn_local builds env via this function).
556:def _find_bash() -> str:
668:# invocation spawn_local uses. $SHELL values outside this set (fish, csh/tcsh,
679:    ``$SHELL`` on POSIX so that ``spawn_local`` uses the shell the user
694:    Only POSIX-sh-family shells are honoured: ``spawn_local`` invokes the
1019:class LocalEnvironment(BaseEnvironment):
1112:    def _run_bash(self, cmd_string: str, *, login: bool = False,

## Relevant tests
apps/desktop/src/store/windows.test.ts
apps/desktop/src/app/right-sidebar/terminal/terminals.test.ts
apps/desktop/src/app/right-sidebar/terminal/revive-buffer.test.ts
apps/desktop/src/app/right-sidebar/terminal/rail.test.tsx
apps/desktop/electron/wsl-clipboard-image.test.ts
apps/desktop/electron/windows-child-options.test.ts
apps/desktop/electron/windows-user-env.test.ts
apps/desktop/electron/session-windows.test.ts
apps/desktop/electron/terminal-mode.test.ts
apps/desktop/electron/windows-hermes-path.test.ts
apps/desktop/electron/wsl-path-bridge.test.ts
tests/test_windows_subprocess_no_window_flags.py
tests/cron/test_terminal_cwd_lock.py
tests/integration/test_modal_terminal.py
tests/integration/test_daytona_terminal.py
tests/cli/test_cli_terminal_response_sanitizer.py
tests/cli/test_terminal_interrupt_recovery.py
tests/cli/test_slash_confirm_windows.py
tests/cli/test_tui_terminal_reset_on_exit.py
tests/cli/test_cli_terminal_shortcuts.py
tests/hermes_cli/test_gateway_windows.py
tests/hermes_cli/test_gateway_wsl.py
tests/hermes_cli/test_dump_terminal_backend.py
tests/hermes_cli/test_kanban_worker_terminal_cwd.py
tests/hermes_cli/test_windows_native_docs.py
tests/hermes_cli/test_terminal_menu_fallbacks.py
tests/tools/test_terminal_tool_pty_fallback.py
tests/tools/test_code_execution_windows_env.py
tests/tools/test_terminal_tool.py
tests/tools/test_local_env_windows_msys.py
tests/tools/test_terminal_requirements.py
tests/tools/test_terminal_timeout_output.py
tests/tools/test_windows_compat.py
tests/tools/test_terminal_exit_semantics.py
tests/tools/test_terminal_foreground_timeout_cap.py
tests/tools/test_terminal_config_env_sync.py
tests/tools/test_terminal_none_command_guard.py
tests/tools/test_terminal_output_transform_hook.py
tests/tools/test_terminal_compound_background.py
tests/tools/test_windows_execution_mode.py
tests/tools/test_terminal_task_cwd.py
tests/tools/test_terminal_tool_requirements.py
tests/tools/test_windows_native_support.py
tests/tools/test_computer_use_null_pid_windows.py

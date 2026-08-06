# Agent instructions for LoginTO

## Project purpose
This repository automates Talisman Online on Windows: it logs accounts in
(client launch, credentials, server selection, character entry) and then
runs gameplay scripts against the logged-in clients. Multiple accounts can
run at once, each with its own window and its own set of enabled scripts.

Three techniques are used to talk to the game:
- **PostMessage input** — keystrokes and clicks injected into a specific
  window handle, so a client can be driven without holding focus.
- **Template matching** (OpenCV) — locating UI elements from the reference
  images under `templates/`. Used by the login flow.
- **Memory reading** — HP/mana/target/position read straight from the
  process (`MemoryReader`). Used by the gameplay scripts, since polling
  pixels for these is slow and fragile.

## Entry points
- `gui.py` — the graphical app (`python gui.py`). This is the primary way
  the project is used: account management, script cards, multi-client.
- `main.py` — terminal-only single login run, no interface
  (`python main.py`). Useful for debugging the login flow in isolation.

## Architecture
Three layers, with a strict communication rule:

    Presentation (src/ui)
        ↓  only through AutomationController
    Automation (src/app, src/services)
        ↓
    Infrastructure (src/infrastructure)

**The rule that matters most:** the GUI must never construct or call
`WindowService`, `VisionService`, `InputService`, `GameClient`, `BotEngine`
or workflows directly. Everything goes through
`src/app/automation_controller.py`. This was violated before and had to be
corrected; keep it intact.

The authoritative document is `.project/architecture/01_Architecture.md`.
Decisions are logged in `.project/decisions/` and progress in
`.project/meetings/DEV_LOG.md` — read the most recent DEV_LOG entries
before starting work, they carry context that the code does not.

## Key directories
- `src/ui/` — `main_window.py` builds the entire interface directly
  (top bar, script cards, client panel, console). `session_registry.py`
  tracks connected accounts.
- `src/app/` — `automation_controller.py` (the single door between GUI and
  core), `application.py`, `container.py` (DI), `state_manager.py`
  (combined session view), `automation_engine.py` (login orchestration).
- `src/services/bot/` — `bot_engine.py` (the per-session script loop),
  `script_registry.py` (the script catalogue), `scripts/` (one file per
  script).
- `src/services/game/` — `game_client.py` facade, `memory_reader.py`,
  `game_reader.py` (pixel reading), `game_session.py`.
- `src/domain/workflows/` — login, server and character workflows.
- `src/infrastructure/` — `window/`, `vision/`, `input/`, `game/launcher`,
  `logging/`. No business rules here.
- `src/config/settings.py` — the single source of truth for configuration
  (frozen dataclass, credentials from `.env`).
- `src/shared/` — constants, keys, offsets, delays, `event_bus.py`.
- `templates/` — reference images for template matching.
- `tools/` — standalone debugging utilities (window discovery, click
  testing, screenshots, memory scanning).
- `tests/` — pytest suite for the automation core.

Note: `config.py` at the repository root is only a compatibility shim that
re-exports `Settings` as module-level constants, kept so the scripts in
`tools/` keep working. **New code must import `src.config.settings`
directly.**

## Working conventions
- **Identifiers in English, prose in Portuguese.** Anything the
  interpreter reads — modules, classes, functions, variables, config
  keys, step kinds, test names — is written in English. Anything a
  person reads — comments, docstrings, log messages, `.project/` docs —
  stays in Portuguese, because that is where the game-specific context
  lives and it is worth nothing translated.
- **Rename as you touch.** New code is English from the start, and any
  Portuguese identifier in a block being edited gets renamed in the same
  change — the same files come up again and again here, so paying a few
  renames per visit is cheaper than one big-bang migration. Rename every
  call site in the same commit (`grep` the old name to zero) and keep
  the rename separate from behaviour changes inside the diff, so a
  broken test points at one or the other, never both.
- Keep changes compatible with Windows and Python 3.10+.
- Never hardcode credentials or secrets. Credentials come from `.env`
  (`TALISMAN_USER` / `TALISMAN_PASS`); saved accounts live in
  `accounts.json` and store passwords in plain text. `.env`,
  `accounts.json` and `gui_settings.json` are all gitignored and hold
  real user data — never paste their contents into commits, issues,
  logs or PR descriptions.
- Preserve the PostMessage-based input approach unless a fallback is
  explicitly required.
- Prefer values in `src/config/settings.py` over magic numbers.
- When adding new templates, keep the naming consistent with the existing
  files in `templates/`.
- **Adding a gameplay script**: create the class in
  `src/services/bot/scripts/` (it needs a `name` attribute and a `tick()`
  method, per the `BotScript` protocol in `bot_engine.py`), then add ONE
  line to `register_builtin_scripts()` in `script_registry.py`. Nothing
  else — the GUI cards, colours and icons are derived from the registry.
  The script's `name` must equal the descriptor's `display_name`, or the
  script will never be enabled (there is a test guarding this).
- Scripts must not depend on each other.
- **Never use `print()`.** Every module does
  `logger = get_logger(__name__)` (from `src.infrastructure.logging`)
  and logs with a level. Use `logger.exception(...)` inside `except`
  blocks so the traceback is preserved. Any thread that belongs to an
  account opens a `session_context(label)` so its lines identify which
  account they came from. See `.project/adr/ADR-003-Logging.md`.
- A script only runs when its feature flag is registered **and** enabled.
  Absence of a flag means OFF — treating "no state" as ON once made every
  script run with its card switched off.

## Verification
Before considering work complete, verify changes with:
- `python -m compileall .`
- `python -m pytest`

The test suite covers the automation core (BotEngine, ScriptRegistry,
SessionRegistry, StateManager, EventBus) and runs without win32, OpenCV,
Tkinter or a running game client. Install dev dependencies with
`pip install -r requirements-dev.txt`.

Workflows, the DI container and the GUI are **not** covered yet — changes
there need manual verification, and the game client is generally not
available during local work. Say so plainly when that is the case rather
than implying a change was verified.

## Notes
- The bot depends on specific UI templates, window titles and memory
  offsets. If a change affects matching or reading behaviour, update the
  relevant template names, thresholds (`match_threshold`) and offsets
  (`src/shared/offsets.py`) carefully.
- The default `client_path` in `settings.py` is a machine-specific
  absolute path. The GUI overrides and persists it in `gui_settings.json`;
  do not assume the default is valid.
- Do not assume the client or game window is available during local
  verification; use the available checks and report any environment
  limitations clearly.

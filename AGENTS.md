# Agent instructions for LoginTO

## Project purpose
This repository automates the login flow for Talisman Online on Windows. It uses Windows message injection, image-based screen matching, and configurable templates under the templates folder.

## Key files
- main.py: orchestrates the full login flow.
- config.py: central configuration, credentials, window title, template names, and thresholds.
- window_utils.py: window discovery and screen capture helpers.
- vision.py: image matching logic for locating UI elements.
- input_utils.py: simulated clicks and text input.
- templates/: reference images used by the bot.
- tools/: small utilities for discovering window titles, testing clicks, and capturing screenshots.

## Working conventions
- Keep changes compatible with Windows and Python 3.10+.
- Avoid hardcoding user credentials or secrets. Prefer environment variables or a local .env file.
- Preserve the existing approach of using PostMessage-based input unless a fallback is explicitly required.
- When adding new templates, keep the naming consistent with the existing files in templates/.
- Prefer configurable values in config.py over magic numbers.

## Verification
Before considering work complete, verify changes with:
- python -m compileall .

When relevant, also validate against the existing tooling:
- python tools/find_window_title.py
- python tools/test_click.py 400 300

## Notes
- The bot depends on specific UI templates and window titles. If a change affects matching behavior, update the relevant template names and thresholds carefully.
- Do not assume the client or game window is available during local verification; use the available checks and report any environment limitations clearly.

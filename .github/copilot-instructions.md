# Copilot instructions for LoginTO

This repository automates Talisman Online login on Windows using image recognition and Windows message injection.

## Repository overview
- The main entry point is main.py.
- Configuration lives in config.py.
- Window handling is in window_utils.py.
- Image matching is in vision.py.
- Input simulation is in input_utils.py.
- Reference images live in templates/.

## Important constraints
- Keep changes Windows-compatible and Python 3.10+ friendly.
- Do not hardcode credentials; use environment variables or a local .env file.
- Preserve the existing PostMessage-based interaction approach unless a fallback is explicitly requested.
- Keep template names and matching thresholds configurable in config.py.

## Validation
Use these commands when appropriate:
- python -m compileall .
- python tools/find_window_title.py
- python tools/test_click.py 400 300

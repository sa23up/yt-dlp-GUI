# Repository Guidelines

## Project Structure
- `yt_dlp_gui.py`: main application (CustomTkinter GUI + `yt-dlp` integration).
- `build.ps1`: Windows-focused Nuitka build script (standalone output).
- `pyproject.toml` / `uv.lock`: dependency metadata for `uv` (Python `>=3.12`).
- `README.md` / `README.en.md`: user-facing documentation.
- Local-only (ignored): `.venv/`, `build/`, `dist/`, `.serena/`.

## Build, Test, and Development Commands
- Install dependencies (recommended): `uv sync --dev`
- Run locally: `uv run python yt_dlp_gui.py`
- Update lockfile after changing dependencies: `uv lock`
- Build with Nuitka: `.\build.ps1 -Configuration Release` (outputs to `build/yt_dlp_gui.dist/`)
- Build with PyInstaller (optional): `pip install -U pyinstaller` then `pyinstaller -F -w yt_dlp_gui.py`

## Coding Style & Naming Conventions
- Indentation: 4 spaces; keep diffs focused (avoid reformat-only changes).
- Naming: `snake_case` for functions/variables; `PascalCase` for classes.
- UI text: add new strings to both `LANG["zh"]` and `LANG["en"]` using the same keys; fetch via the translation helper (e.g., `t("app_title")`).
- Responsiveness: keep downloads/parsing off the UI thread; update widgets via `root.after(...)`.

## Testing Guidelines
- There is no automated test suite yet. Validate changes with a quick smoke run:
  - Launch → open “Parse Formats” dialog → batch-select video/audio → start/cancel download → verify progress/log updates.
- If you add pure logic helpers, prefer `pytest` tests under `tests/` (e.g., `tests/test_i18n.py`).

## Commit & Pull Request Guidelines
- History uses short, imperative subjects (e.g., `Update README`, `Fix download link`, `Optimize Nuitka build`).
- PRs should include: what changed, how to test, screenshots/GIFs for UI changes, and any runtime assumptions (FFmpeg, cookies, EJS/runtime).


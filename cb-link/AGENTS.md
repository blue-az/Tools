# Repository Guidelines

## Project Structure & Module Organization
- `cb-display.sh` holds the Fedora host server logic for extend/mirror modes.
- `cb-connect.sh` is the Chromebook/Debian client connector.
- `cb-share.sh` supports reverse sharing (CB -> host).
- `Testing/TESTING.md` documents the manual test checklist.
- `README.md` is the user-facing workflow and command reference.

## Build, Test, and Development Commands
- No build step; these are executable Bash scripts.
- Run server actions: `./cb-display.sh extend|mirror|toggle|stop|status|cb`.
- Run client actions: `./cb-connect.sh f|m|mf|d|s`.
- Example (extend mode):
  - Host: `./cb-display.sh extend`
  - CB: `./cb-connect.sh`

## Coding Style & Naming Conventions
- Bash scripts with 4-space indentation and lower_snake_case functions.
- File naming: `cb-*.sh` for entry points; keep new scripts consistent.
- Prefer simple, explicit command pipelines; comment only for non-obvious logic.

## Testing Guidelines
- Manual testing only; follow `Testing/TESTING.md`.
- Update the checklist and results log after validating new behavior.
- If behavior changes, update `README.md` examples accordingly.

## Commit & Pull Request Guidelines
- Commit messages in short sentence case (e.g., "Update README for hostname.local approach").
- Keep changes focused; include rationale in the PR description.
- Mention environment assumptions (Fedora/Sway, Debian/Chromebook) when relevant.

## Security & Configuration Tips
- Firewall: open `5900/tcp` on the Fedora host when needed.
- Host resolution relies on mDNS (`*.local`); include IP fallback in docs.

# Sorta

Sorta is a command-line filesystem organizer. It scans your filesystem, finds duplicate and dormant files, organizes files by type, and helps keep your storage tidy.

## Features
- Scans directories with a readable summary — rich tables in a terminal, plain text when piped, or JSON for scripts
- Detects duplicate files (fast: first-chunk pre-hash + parallel hashing)
- Identifies large dormant files
- Organizes files into category folders: documents split into Word, Spreadsheets, Presentations, PDF, Text, and Ebooks (under a single `Documents/` parent), plus Images, Audio, Videos, Web, Archives, Applications, and Installers
- Keyword-targeted deletion (`delete --match`)
- Sends deletions to the native OS Trash by default, with a recoverable internal trash as fallback
- Preview-first: `--dry-run` on destructive commands, `-y` to auto-confirm
- Scheduled runs via cron, with an optional JSON audit log

## Usage
```bash
sorta /path/to/scan <command> [options]
# or without installing: python -m sorta.cli /path/to/scan <command> [options]
```

Commands:
- `scan` — scan and show a summary: total size, per-category breakdown, and the largest files with human-readable sizes and modified times (default when no command is given)
- `show-duplicates [--apply] [--strict-names] [--include-empty]` — list duplicate files; `--apply` deletes interactively (to trash). Empty files are excluded unless `--include-empty` is given.
- `show-dormant [--size MB] [--days N] [--apply]` — list large dormant files; `--apply` deletes interactively (to trash)
- `show-organization [--apply]` — suggest moving files into category folders; `--apply` moves interactively
- `delete --match KEYWORD [--match KEYWORD ...] [--apply]` — delete files whose name contains any of the keywords (case-insensitive substring). Previews by default; `--apply` deletes to trash. Refuses to run without at least one `--match`.
- `restore [--list] [--file NAME]` — list or restore files from trash
- `empty-trash` — permanently delete everything in trash
- `recommend` — show insights (largest files/folders, type breakdown, duplicates, dormant)
- `schedule --cron "<expr>" [--run CMD] [--report LOG] [--remove] [--list] [--dry-run]` — manage a recurring sorta run via the user's crontab. `--report LOG` appends each run's JSON output to a log file for an audit trail.

Global flags:
- `--json` — emit machine-readable JSON instead of formatted output (use for scripting and scheduled runs); returns the complete file set, not the human-view cap
- `--plain` — force plain-text output, disabling rich formatting
- `--limit N` — max files listed in `scan` output (default: 10)
- `--all` — list every file in `scan` output, no cap
- `-y`, `--yes` — assume yes to all interactive prompts. Deletions still go to trash; does not affect `empty-trash`.
- `--sorta-trash` — use sorta's recoverable internal trash instead of the native OS Trash.

### Trash behavior
By default, deletions go to the **native OS Trash** (Finder on macOS) so files appear in the system Trash and can be recovered with Put Back. This requires the optional `send2trash` package; without it, sorta falls back to an internal `.sorta_trash/` directory recoverable via `sorta restore`. Pass `--sorta-trash` to force the internal trash (and `restore`/`empty-trash`) regardless.

Deletions move files to a trash directory by default and can be restored until `empty-trash` is run.

Scheduled runs are restricted to read-only commands (default `recommend`): an unattended job has no one to confirm deletion prompts.

## Install
Recommended (isolated, puts `sorta` on your PATH) — using [pipx](https://pipx.pypa.io):
```bash
pipx install "sorta[enhanced] @ git+https://github.com/Hafizyishawu/Sorta.git"
```

Or with pip (ideally inside a virtualenv):
```bash
pip install "sorta[enhanced] @ git+https://github.com/Hafizyishawu/Sorta.git"
```

`[enhanced]` pulls in `rich` (formatted output) and `send2trash` (native OS Trash). Omit it for a zero-dependency install with plain output and the internal recoverable trash.

From a local clone:
```bash
pip install .            # or:  pip install '.[enhanced]'
```

Developing on Sorta? Use an editable install: `pip install -e '.[enhanced]'`.

## Requirements
- Python 3.8+
- Optional: `rich` (formatted tables/panels) and `send2trash` (native OS Trash) — installed by the `[enhanced]` extra above, or via `pip install -r requirements-optional.txt`. Without them, Sorta uses plain-text output and its internal recoverable trash.
- `pytest` for the test suite.

## Roadmap
- [x] File scanning
- [x] Duplicate detection
- [x] Dormant file management
- [x] File organization
- [x] Trash with restore
- [x] Recommendations and insights
- [x] Interactive CLI
- [x] Scheduled runs (cron)
- [x] CI (lint + tests)
- [x] v2: unified renderer (rich/plain/JSON), keyword delete, native OS Trash, `--dry-run`, faster duplicate detection, document sub-categories, `sorta` command

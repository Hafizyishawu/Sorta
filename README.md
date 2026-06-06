# Sorta

Sorta is an intelligent AI-powered filesystem management system. It scans your filesystem, finds duplicate and dormant files, organizes files by type, and helps keep your storage optimized and tidy.

## Features
- Scans directories and collects file metadata
- Detects duplicate files
- Identifies large dormant files (with user permission to delete)
- Organizes files into folders by type
- Supports audio, video, image, document, app, and setup file types

## Usage
```bash
python -m sorta.cli /path/to/scan <command> [options]
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
- `schedule --cron "<expr>" [--run CMD] [--remove] [--list] [--dry-run]` — manage a recurring sorta run via the user's crontab

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

## Requirements
- Python 3.7+
- pytest (for tests)
- `rich` (optional) — enables formatted tables and panels in an interactive terminal; without it, output falls back to plain text. Install with `pip install -r requirements-optional.txt`.

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

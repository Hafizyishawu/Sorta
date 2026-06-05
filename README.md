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
- `scan` — scan and show a file count (default when no command is given)
- `show-duplicates [--apply] [--strict-names] [--include-empty]` — list duplicate files; `--apply` deletes interactively (to trash). Empty files are excluded unless `--include-empty` is given.
- `show-dormant [--size MB] [--days N] [--apply]` — list large dormant files; `--apply` deletes interactively (to trash)
- `show-organization [--apply]` — suggest moving files into category folders; `--apply` moves interactively
- `restore [--list] [--file NAME]` — list or restore files from trash
- `empty-trash` — permanently delete everything in trash
- `recommend` — show insights (largest files/folders, type breakdown, duplicates, dormant)
- `schedule --cron "<expr>" [--run CMD] [--remove] [--list] [--dry-run]` — manage a recurring sorta run via the user's crontab

Deletions move files to a trash directory by default and can be restored until `empty-trash` is run.

Scheduled runs are restricted to read-only commands (default `recommend`): an unattended job has no one to confirm deletion prompts.

## Requirements
- Python 3.7+
- pytest (for tests)

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

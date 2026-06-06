# Changelog

All notable changes to Sorta are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-06

### Added
- Unified output renderer: rich tables in a terminal, plain text when piped,
  and `--json` for scripting — across `scan`, `recommend`, `show-duplicates`,
  `show-dormant`, and `show-organization`.
- `delete --match KEYWORD` — keyword-targeted deletion, scoped to the folder,
  case-insensitive, preview by default, and refuses to run without a filter.
- `--dry-run` on every destructive command — previews exactly what `--apply`
  would delete or move, changing nothing.
- Global flags: `-y`/`--yes`, `--all`, `--limit N`, `--plain`, `--json`,
  `--sorta-trash`, and `--version`. Flags parse before or after the subcommand.
- `schedule --report LOG` — appends each scheduled run's JSON output to a log
  file for an audit trail.
- `sorta` console command and `pyproject.toml` packaging, with an `[enhanced]`
  extra for `rich` + `send2trash`.
- Document sub-categories (Word, Spreadsheets, Presentations, PDF, Text,
  Ebooks) under a single `Documents/` parent, plus new `Web` and `Archives`
  categories and broader audio/video/image extension coverage.
- Live progress indicator while scanning large directories.

### Changed
- **Deletions now default to the native OS Trash** (via the optional
  `send2trash`), so files appear in the system Trash with Put Back. Falls back
  to the internal recoverable trash (`sorta restore`) when `send2trash` is
  absent or `--sorta-trash` is passed.
- Duplicate detection is significantly faster on large directories: a
  first-chunk pre-hash skips files that cannot match, and hashing runs in
  parallel. Results are unchanged.
- Minimum Python version corrected to 3.8 (the code uses the walrus operator).

### Fixed
- Organizer no longer creates nested `Documents/Documents/...` folders when run
  inside a `Documents` directory; it reuses existing sub-folders and is
  idempotent.
- `recommend` no longer prints malformed extensions (`..mp4`).

## [1.0.0] - 2026-06-05

### Added
- Initial release: directory scanning, content-hash duplicate detection
  (empty-file aware), large dormant-file insights, type-based organization,
  recoverable trash with restore, recommendations, and read-only cron
  scheduling. CI runs ruff, bandit, pip-audit, and the pytest suite.

[2.0.0]: https://github.com/Hafizyishawu/Sorta/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/Hafizyishawu/Sorta/releases/tag/v1.0.0

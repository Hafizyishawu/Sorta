import json
import sys
import time
from datetime import datetime

from sorta.extension_mapper import ExtensionMapper

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    _RICH_AVAILABLE = True
except ImportError:
    # rich is an optional dependency. Without it the CLI still produces
    # readable plain-text output, so the tool keeps a zero-dependency runtime.
    _RICH_AVAILABLE = False

_SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


class _ScanProgress:
    # A live "Scanning… N files" spinner on stderr (so it never pollutes stdout
    # or JSON). Becomes a no-op when rich is absent or stderr is not a terminal.
    def __init__(self, active):
        self._status = Console(stderr=True).status("Scanning…") if active else None

    def __enter__(self):
        if self._status:
            self._status.__enter__()
        return self

    def __exit__(self, *exc):
        if self._status:
            return self._status.__exit__(*exc)
        return False

    def update(self, count):
        if self._status:
            self._status.update(f"Scanning… {count} files")


def scan_progress():
    active = _RICH_AVAILABLE and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()
    return _ScanProgress(active)


def format_size(num_bytes):
    """Human-readable size using binary (1024) steps, matching the MB labels
    the rest of the tool already shows to users."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    size = float(num_bytes)
    for unit in _SIZE_UNITS[1:]:
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} {_SIZE_UNITS[-1]}"


def format_time(epoch, now=None):
    """Relative phrasing for recent timestamps, ISO date for anything older
    than a month. `now` is injectable so output is deterministic in tests."""
    now = time.time() if now is None else now
    delta = now - epoch
    if delta < 0:
        return datetime.fromtimestamp(epoch).strftime('%Y-%m-%d')
    if delta < 60:
        return "just now"
    if delta < 3600:
        minutes = int(delta // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if delta < 86400:
        hours = int(delta // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if delta < 30 * 86400:
        days = int(delta // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    return datetime.fromtimestamp(epoch).strftime('%Y-%m-%d')


def summarize(files):
    """Aggregate a scan into totals and a per-category breakdown, sorted by the
    space each category occupies so the heaviest groups surface first."""
    total_size = sum(f['size'] for f in files)
    by_category = {}
    for f in files:
        category = ExtensionMapper.get_category(f['extension'])
        count, size = by_category.get(category, (0, 0))
        by_category[category] = (count + 1, size + f['size'])
    categories = sorted(
        ([cat, count, size] for cat, (count, size) in by_category.items()),
        key=lambda row: row[2],
        reverse=True,
    )
    return {
        'count': len(files),
        'total_size': total_size,
        'categories': categories,
    }


def _should_use_rich(stream, plain):
    # Fall back to plain text when rich is missing, when the user asked for it,
    # or when output is piped/redirected (a TTY check avoids dumping escape
    # codes into files and scheduled-run logs).
    if plain or not _RICH_AVAILABLE:
        return False
    return hasattr(stream, 'isatty') and stream.isatty()


def _resolve_limit(limit, show_all, as_json):
    # `--all` always wins. An explicit `--limit` is honoured as given. With
    # neither, JSON returns the complete set (it feeds tooling) while the human
    # view caps at 10 so a large directory does not flood the terminal.
    if show_all:
        return None
    if limit is not None:
        return limit
    return None if as_json else 10


def _scan_plain_lines(files, summary, limit, now=None):
    lines = [
        f"Scanned {summary['count']} files, {format_size(summary['total_size'])} total.",
    ]
    if summary['categories']:
        lines.append("")
        lines.append("By category:")
        for category, count, size in summary['categories']:
            lines.append(f"  {category:<10} {count:>6}  {format_size(size)}")
    shown = files[:limit]
    if shown:
        lines.append("")
        lines.append("Files:")
        for f in shown:
            lines.append(
                f"  {format_size(f['size']):>10}  "
                f"{format_time(f['last_modified'], now=now):>14}  "
                f"{f['path']}"
            )
    remaining = summary['count'] - len(shown)
    if remaining > 0:
        lines.append(f"  ... and {remaining} more")
    return lines


def _scan_json(files, summary, limit):
    shown = files[:limit]
    return {
        'count': summary['count'],
        'total_size': summary['total_size'],
        'categories': [
            {'category': cat, 'count': count, 'size': size}
            for cat, count, size in summary['categories']
        ],
        'files': [
            {
                'path': f['path'],
                'size': f['size'],
                'last_modified': f['last_modified'],
                'extension': f['extension'],
            }
            for f in shown
        ],
        'truncated': max(summary['count'] - len(shown), 0),
    }


def _render_scan_rich(files, summary, limit, stream):
    console = Console(file=stream)
    breakdown = "\n".join(
        f"{category:<10} {count:>6}  {format_size(size)}"
        for category, count, size in summary['categories']
    ) or "no categorised files"
    console.print(Panel(
        f"[bold]{summary['count']}[/bold] files  ·  "
        f"[bold]{format_size(summary['total_size'])}[/bold] total\n\n{breakdown}",
        title="Scan",
        expand=False,
    ))
    shown = files[:limit]
    if shown:
        table = Table(show_edge=False, pad_edge=False)
        table.add_column("Size", justify="right")
        table.add_column("Modified", justify="right")
        table.add_column("Path", overflow="fold")
        for f in shown:
            table.add_row(
                format_size(f['size']),
                format_time(f['last_modified']),
                f['path'],
            )
        console.print(table)
    remaining = summary['count'] - len(shown)
    if remaining > 0:
        console.print(f"... and {remaining} more")


def render_scan(files, limit=None, show_all=False, plain=False, as_json=False, stream=None, now=None):
    """Single entry point for `scan` output. Routes to JSON (for scripting and
    scheduled runs), rich (interactive terminal), or plain text (everything
    else) so callers never decide formatting themselves."""
    stream = sys.stdout if stream is None else stream
    limit = _resolve_limit(limit, show_all, as_json)
    summary = summarize(files)
    if as_json:
        json.dump(_scan_json(files, summary, limit), stream, indent=2)
        stream.write("\n")
        return
    if _should_use_rich(stream, plain):
        _render_scan_rich(files, summary, limit, stream)
        return
    for line in _scan_plain_lines(files, summary, limit, now=now):
        print(line, file=stream)


def _files_json(files):
    return [{'path': f['path'], 'size': f['size']} for f in files]


def recommendations_json(recs):
    out = {}
    for rec in recs:
        kind = rec['type']
        if kind == 'largest_files':
            out['largest_files'] = _files_json(rec['files'])
        elif kind == 'file_type_breakdown':
            out['file_type_breakdown'] = [
                {'extension': ext or '', 'count': count} for ext, count in rec['breakdown']
            ]
        elif kind == 'dormant_files':
            out['dormant_files'] = _files_json(rec['files'])
        elif kind == 'duplicate_groups':
            out['duplicate_groups'] = [_files_json(group) for group in rec['groups']]
        elif kind == 'largest_folders':
            out['largest_folders'] = [
                {'folder': folder, 'size': size} for folder, size in rec['folders']
            ]
    return out


def _section_table(title, columns):
    table = Table(title=title, title_justify="left", show_edge=False, pad_edge=False)
    for name, justify in columns:
        table.add_column(name, justify=justify, overflow="fold")
    return table


def _render_recommendations_rich(recs, stream):
    console = Console(file=stream)
    for rec in recs:
        kind = rec['type']
        if kind == 'largest_files':
            table = _section_table("Largest files", [("Size", "right"), ("Path", "left")])
            for f in rec['files']:
                table.add_row(format_size(f['size']), f['path'])
            console.print(table)
        elif kind == 'file_type_breakdown':
            table = _section_table("File type breakdown", [("Extension", "left"), ("Count", "right")])
            for ext, count in rec['breakdown']:
                table.add_row(ext or "(no extension)", str(count))
            console.print(table)
        elif kind == 'dormant_files':
            table = _section_table("Dormant files (>180d, >50MB)", [("Size", "right"), ("Path", "left")])
            for f in rec['files']:
                table.add_row(format_size(f['size']), f['path'])
            console.print(table)
        elif kind == 'duplicate_groups':
            console.print(f"[bold]Duplicate groups:[/bold] {len(rec['groups'])}")
            for i, group in enumerate(rec['groups'], 1):
                table = _section_table(f"Group {i}", [("Size", "right"), ("Path", "left")])
                for f in group:
                    table.add_row(format_size(f['size']), f['path'])
                console.print(table)
        elif kind == 'largest_folders':
            table = _section_table("Largest folders", [("Size", "right"), ("Folder", "left")])
            for folder, size in rec['folders']:
                table.add_row(format_size(size), folder)
            console.print(table)


def render_recommendations(recs, plain=False, as_json=False, stream=None):
    stream = sys.stdout if stream is None else stream
    if as_json:
        json.dump(recommendations_json(recs), stream, indent=2)
        stream.write("\n")
        return
    if _should_use_rich(stream, plain):
        _render_recommendations_rich(recs, stream)
        return
    for rec in recs:
        kind = rec['type']
        if kind == 'largest_files':
            print("Largest files:", file=stream)
            for f in rec['files']:
                print(f"  {format_size(f['size']):>10}  {f['path']}", file=stream)
        elif kind == 'file_type_breakdown':
            print("File type breakdown:", file=stream)
            for ext, count in rec['breakdown']:
                # ext already includes its leading dot; printing ".{ext}" here
                # was the source of the doubled-dot "..mp4" bug.
                print(f"  {ext or '(no extension)'}: {count}", file=stream)
        elif kind == 'dormant_files':
            print("Dormant files (>180d, >50MB):", file=stream)
            for f in rec['files']:
                print(f"  {format_size(f['size']):>10}  {f['path']}", file=stream)
        elif kind == 'duplicate_groups':
            print(f"Duplicate groups: {len(rec['groups'])}", file=stream)
            for group in rec['groups']:
                print("  Group:", file=stream)
                for f in group:
                    print(f"    {format_size(f['size']):>10}  {f['path']}", file=stream)
        elif kind == 'largest_folders':
            print("Largest folders:", file=stream)
            for folder, size in rec['folders']:
                print(f"  {format_size(size):>10}  {folder}", file=stream)


def duplicates_json(groups):
    return {
        'group_count': len(groups),
        'duplicate_count': sum(len(g) - 1 for g in groups),
        'groups': [_files_json(g) for g in groups],
    }


def render_duplicates_json(groups, stream=None):
    stream = sys.stdout if stream is None else stream
    json.dump(duplicates_json(groups), stream, indent=2)
    stream.write("\n")


def render_duplicates(groups, plain=False, as_json=False, stream=None):
    """Display the duplicate findings (the index column lets the caller's
    interactive --apply flow reference each file)."""
    stream = sys.stdout if stream is None else stream
    if as_json:
        render_duplicates_json(groups, stream)
        return
    if not groups:
        print("No duplicate files found.", file=stream)
        return
    header = f"Found {sum(len(g) - 1 for g in groups)} duplicate files in {len(groups)} groups:"
    if _should_use_rich(stream, plain):
        console = Console(file=stream)
        console.print(header)
        for i, group in enumerate(groups, 1):
            table = _section_table(f"Group {i}", [("Idx", "right"), ("Size", "right"), ("Path", "left")])
            for idx, f in enumerate(group):
                table.add_row(str(idx), format_size(f['size']), f['path'])
            console.print(table)
        return
    print(header, file=stream)
    for i, group in enumerate(groups, 1):
        print(f"  Group {i}:", file=stream)
        for idx, f in enumerate(group):
            print(f"    [{idx}] {f['path']} ({format_size(f['size'])})", file=stream)


def dormant_json(dormant_files):
    return {
        'count': len(dormant_files),
        'files': [
            {'path': f['path'], 'size': f['size'], 'last_accessed': f['last_accessed']}
            for f in dormant_files
        ],
    }


def render_dormant_json(dormant_files, stream=None):
    stream = sys.stdout if stream is None else stream
    json.dump(dormant_json(dormant_files), stream, indent=2)
    stream.write("\n")


def render_dormant(dormant_files, plain=False, as_json=False, stream=None):
    stream = sys.stdout if stream is None else stream
    if as_json:
        render_dormant_json(dormant_files, stream)
        return
    if not dormant_files:
        print("No large dormant files found.", file=stream)
        return
    header = f"Found {len(dormant_files)} large dormant files:"
    if _should_use_rich(stream, plain):
        console = Console(file=stream)
        console.print(header)
        table = _section_table("", [("Size", "right"), ("Last accessed", "right"), ("Path", "left")])
        for f in dormant_files:
            table.add_row(format_size(f['size']), format_time(f['last_accessed']), f['path'])
        console.print(table)
        return
    print(header, file=stream)
    for f in dormant_files:
        print(f"  {f['path']} | {format_size(f['size'])} | Last accessed: {format_time(f['last_accessed'])}", file=stream)


def organization_json(suggestions):
    return {
        'count': len(suggestions),
        'moves': [
            {
                'source': s['source'],
                'target': s['target'],
                'category': s['category'],
                'group': s.get('group'),
            }
            for s in suggestions
        ],
    }


def render_organization(suggestions, plain=False, as_json=False, stream=None):
    stream = sys.stdout if stream is None else stream
    if as_json:
        json.dump(organization_json(suggestions), stream, indent=2)
        stream.write("\n")
        return
    if not suggestions:
        print("No files to organize.", file=stream)
        return
    header = f"Suggest moving {len(suggestions)} files:"
    if _should_use_rich(stream, plain):
        console = Console(file=stream)
        console.print(header)
        table = _section_table("", [("Category", "left"), ("From", "left"), ("To", "left")])
        for s in suggestions:
            table.add_row(s['category'], s['source'], s['target'])
        console.print(table)
        return
    print(header, file=stream)
    for s in suggestions:
        print(f"  {s['source']} -> {s['target']}  [{s['category']}]", file=stream)


def render_apply_summary(summary_line, items=None, columns=None, plain=False, stream=None, border_style="green"):
    """Pretty end-of-operation summary for destructive flows: a table of the
    affected files plus a styled summary line, with a plain fallback. Used for
    both completed --apply runs (green) and --dry-run previews (yellow)."""
    stream = sys.stdout if stream is None else stream
    if _should_use_rich(stream, plain):
        console = Console(file=stream)
        if items and columns:
            table = _section_table("", columns)
            for row in items:
                table.add_row(*row)
            console.print(table)
        console.print(Panel(summary_line, expand=False, border_style=border_style))
        return
    if items:
        for row in items:
            print("  " + "  ".join(row), file=stream)
    print(summary_line, file=stream)

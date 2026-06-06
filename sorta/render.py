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

import io
import json

from sorta import render


def test_format_size_steps():
    assert render.format_size(0) == "0 B"
    assert render.format_size(512) == "512 B"
    assert render.format_size(1024) == "1.0 KB"
    assert render.format_size(1536) == "1.5 KB"
    assert render.format_size(1024 * 1024) == "1.0 MB"
    assert render.format_size(int(1.4 * 1024 * 1024)) == "1.4 MB"
    assert render.format_size(5 * 1024 ** 3) == "5.0 GB"


def test_format_time_relative_and_absolute():
    now = 1_000_000_000
    assert render.format_time(now - 10, now=now) == "just now"
    assert render.format_time(now - 120, now=now) == "2 minutes ago"
    assert render.format_time(now - 3600, now=now) == "1 hour ago"
    assert render.format_time(now - 2 * 86400, now=now) == "2 days ago"
    # Older than a month falls back to an ISO date, not a vague phrase.
    assert render.format_time(now - 400 * 86400, now=now).count("-") == 2


def test_summarize_groups_by_category_sorted_by_size():
    files = [
        {'path': '/a.mp3', 'size': 100, 'extension': '.mp3', 'last_modified': 0},
        {'path': '/b.mp4', 'size': 5000, 'extension': '.mp4', 'last_modified': 0},
        {'path': '/c.txt', 'size': 10, 'extension': '.txt', 'last_modified': 0},
    ]
    summary = render.summarize(files)
    assert summary['count'] == 3
    assert summary['total_size'] == 5110
    # Video is largest, so it must come first.
    assert summary['categories'][0][0] == 'video'


def test_render_scan_plain_truncates_and_counts(tmp_path):
    files = [
        {'path': f'/f{i}.txt', 'size': i, 'extension': '.txt', 'last_modified': 0}
        for i in range(15)
    ]
    out = io.StringIO()
    render.render_scan(files, limit=10, plain=True, stream=out, now=0)
    text = out.getvalue()
    assert "Scanned 15 files" in text
    assert "... and 5 more" in text


def test_render_scan_all_shows_every_file():
    files = [
        {'path': f'/f{i}.txt', 'size': i, 'extension': '.txt', 'last_modified': 0}
        for i in range(25)
    ]
    out = io.StringIO()
    render.render_scan(files, show_all=True, plain=True, stream=out, now=0)
    text = out.getvalue()
    assert "more" not in text
    assert text.count("/f") == 25


def test_render_scan_json_returns_complete_set_by_default():
    files = [
        {'path': f'/f{i}.txt', 'size': i, 'extension': '.txt', 'last_modified': 0}
        for i in range(25)
    ]
    out = io.StringIO()
    render.render_scan(files, as_json=True, stream=out)
    payload = json.loads(out.getvalue())
    # JSON feeds tooling, so it must not silently cap at the human default of 10.
    assert len(payload['files']) == 25
    assert payload['truncated'] == 0


def test_render_scan_json_is_machine_readable():
    files = [
        {'path': '/a.mp3', 'size': 100, 'extension': '.mp3', 'last_modified': 123.0},
    ]
    out = io.StringIO()
    render.render_scan(files, as_json=True, stream=out)
    payload = json.loads(out.getvalue())
    assert payload['count'] == 1
    assert payload['total_size'] == 100
    assert payload['files'][0]['path'] == '/a.mp3'
    assert payload['truncated'] == 0


def test_plain_output_has_no_ansi_escape_codes():
    files = [{'path': '/a.txt', 'size': 1, 'extension': '.txt', 'last_modified': 0}]
    out = io.StringIO()
    render.render_scan(files, plain=True, stream=out, now=0)
    assert "\x1b[" not in out.getvalue()

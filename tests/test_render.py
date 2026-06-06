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


def test_recommendations_json_shape():
    recs = [
        {'type': 'largest_files', 'files': [{'path': '/a.mp4', 'size': 100}]},
        {'type': 'file_type_breakdown', 'breakdown': [('.mp4', 1), ('', 2)]},
        {'type': 'duplicate_groups', 'groups': [[{'path': '/x', 'size': 1}, {'path': '/y', 'size': 1}]]},
        {'type': 'largest_folders', 'folders': [('/d', 500)]},
    ]
    out = io.StringIO()
    render.render_recommendations(recs, as_json=True, stream=out)
    payload = json.loads(out.getvalue())
    assert payload['largest_files'][0]['path'] == '/a.mp4'
    assert payload['file_type_breakdown'][0] == {'extension': '.mp4', 'count': 1}
    assert payload['largest_folders'][0] == {'folder': '/d', 'size': 500}


def test_recommendations_plain_has_no_double_dot_extension():
    # Regression: the breakdown previously printed "..mp4" because it prefixed a
    # dot onto an extension that already had one.
    recs = [{'type': 'file_type_breakdown', 'breakdown': [('.mp4', 3), ('', 1)]}]
    out = io.StringIO()
    render.render_recommendations(recs, stream=out)
    text = out.getvalue()
    assert '..mp4' not in text
    assert '.mp4: 3' in text
    assert '(no extension): 1' in text


def test_recommendations_plain_uses_human_sizes():
    recs = [{'type': 'largest_files', 'files': [{'path': '/big.bin', 'size': 1024 * 1024}]}]
    out = io.StringIO()
    render.render_recommendations(recs, stream=out)
    text = out.getvalue()
    assert '1.0 MB' in text
    assert 'bytes' not in text


def test_duplicates_and_dormant_json_shapes():
    groups = [[{'path': '/a', 'size': 5}, {'path': '/b', 'size': 5}]]
    dj = render.duplicates_json(groups)
    assert dj['group_count'] == 1
    assert dj['duplicate_count'] == 1
    assert len(dj['groups'][0]) == 2

    dormant = [{'path': '/old.bin', 'size': 99, 'last_accessed': 12.0}]
    mj = render.dormant_json(dormant)
    assert mj['count'] == 1
    assert mj['files'][0] == {'path': '/old.bin', 'size': 99, 'last_accessed': 12.0}


def test_organization_json_shape():
    suggestions = [
        {'source': '/a.pdf', 'target': '/Documents/PDF/a.pdf', 'category': 'pdf', 'group': None},
    ]
    out = io.StringIO()
    render.render_organization(suggestions, as_json=True, stream=out)
    payload = json.loads(out.getvalue())
    assert payload['count'] == 1
    assert payload['moves'][0]['source'] == '/a.pdf'
    assert payload['moves'][0]['target'] == '/Documents/PDF/a.pdf'
    assert payload['moves'][0]['category'] == 'pdf'


def test_organization_plain_lists_moves():
    suggestions = [{'source': '/a.pdf', 'target': '/Documents/PDF/a.pdf', 'category': 'pdf', 'group': None}]
    out = io.StringIO()
    render.render_organization(suggestions, plain=True, stream=out)
    text = out.getvalue()
    assert "Suggest moving 1 files" in text
    assert "/a.pdf -> /Documents/PDF/a.pdf" in text


def test_scan_plain_output_snapshot():
    # Snapshot: locks the exact rendered scan output so formatting can't silently
    # regress. last_modified/now pinned to 0 for determinism ("just now").
    files = [
        {'path': '/x/a.mp4', 'size': 1500000, 'extension': '.mp4', 'last_modified': 0},
        {'path': '/x/b.txt', 'size': 2048, 'extension': '.txt', 'last_modified': 0},
    ]
    out = io.StringIO()
    render.render_scan(files, limit=10, plain=True, stream=out, now=0)
    assert out.getvalue() == (
        'Scanned 2 files, 1.4 MB total.\n'
        '\n'
        'By category:\n'
        '  video           1  1.4 MB\n'
        '  text            1  2.0 KB\n'
        '\n'
        'Files:\n'
        '      1.4 MB        just now  /x/a.mp4\n'
        '      2.0 KB        just now  /x/b.txt\n'
    )


def test_recommendations_plain_output_snapshot():
    recs = [
        {'type': 'largest_files', 'files': [{'path': '/x/a.mp4', 'size': 1500000}]},
        {'type': 'file_type_breakdown', 'breakdown': [('.mp4', 1), ('', 2)]},
        {'type': 'largest_folders', 'folders': [('/x', 1500000)]},
    ]
    out = io.StringIO()
    render.render_recommendations(recs, plain=True, stream=out)
    assert out.getvalue() == (
        'Largest files:\n'
        '      1.4 MB  /x/a.mp4\n'
        'File type breakdown:\n'
        '  .mp4: 1\n'
        '  (no extension): 2\n'
        'Largest folders:\n'
        '      1.4 MB  /x\n'
    )


def test_plain_output_has_no_ansi_escape_codes():
    files = [{'path': '/a.txt', 'size': 1, 'extension': '.txt', 'last_modified': 0}]
    out = io.StringIO()
    render.render_scan(files, plain=True, stream=out, now=0)
    assert "\x1b[" not in out.getvalue()

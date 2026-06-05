import time
import os
from sorta.scanner import FileScanner
from sorta.recommendations import get_recommendations


def _recs_by_type(recs):
    return {r['type']: r for r in recs}


def test_recommendations_cover_expected_sections(tmp_path):
    (tmp_path / "a.txt").write_text("same")
    (tmp_path / "b.txt").write_text("same")
    (tmp_path / "c.log").write_text("unique")

    files = FileScanner(str(tmp_path)).scan()
    recs = _recs_by_type(get_recommendations(files))

    assert 'largest_files' in recs
    assert 'file_type_breakdown' in recs
    assert 'largest_folders' in recs
    assert 'duplicate_groups' in recs
    assert len(recs['duplicate_groups']['groups']) == 1


def test_recommendations_flags_large_dormant_file(tmp_path):
    old_time = time.time() - 200 * 24 * 60 * 60
    big = tmp_path / "big_old.bin"
    big.write_bytes(b"0" * (60 * 1024 * 1024))
    os.utime(big, (old_time, old_time))

    files = FileScanner(str(tmp_path)).scan()
    recs = _recs_by_type(get_recommendations(files))

    assert 'dormant_files' in recs
    paths = [os.path.basename(f['path']) for f in recs['dormant_files']['files']]
    assert "big_old.bin" in paths


def test_recommendations_empty_directory_does_not_crash(tmp_path):
    recs = get_recommendations([])
    types = {r['type'] for r in recs}
    # Sections that always emit even with no files
    assert 'file_type_breakdown' in types
    assert 'largest_folders' in types

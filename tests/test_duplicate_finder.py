from sorta.scanner import FileScanner
from sorta.duplicate_finder import DuplicateFinder
import os

def test_find_duplicates(tmp_path):
    # Create duplicate files
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file3 = tmp_path / "c.txt"
    file1.write_text("hello world")
    file2.write_text("hello world")
    file3.write_text("different content")
    
    scanner = FileScanner(str(tmp_path))
    files = scanner.scan()
    finder = DuplicateFinder(files)
    duplicates = finder.find_duplicates()
    
    # Only a.txt and b.txt should be duplicates
    duplicate_paths = set()
    for group in duplicates:
        for file in group:
            duplicate_paths.add(os.path.basename(file['path']))
    assert "a.txt" in duplicate_paths
    assert "b.txt" in duplicate_paths
    assert "c.txt" not in duplicate_paths


def test_same_size_differing_first_chunk_are_not_duplicates(tmp_path):
    # Same size but different content in the first chunk: the quick-hash
    # pre-filter must rule them out (and never report them as duplicates).
    (tmp_path / "x.bin").write_bytes(b"A" * 20000)
    (tmp_path / "y.bin").write_bytes(b"B" * 20000)

    files = FileScanner(str(tmp_path)).scan()
    assert DuplicateFinder(files).find_duplicates() == []


def test_large_identical_files_past_first_chunk_are_duplicates(tmp_path):
    # Identical content larger than the chunk size must still be caught after
    # the pre-filter passes them through to a full hash.
    blob = (b"same-prefix" * 1000) + (b"tail" * 5000)
    (tmp_path / "p.bin").write_bytes(blob)
    (tmp_path / "q.bin").write_bytes(blob)
    (tmp_path / "r.bin").write_bytes(blob[:-4] + b"diff")

    files = FileScanner(str(tmp_path)).scan()
    duplicates = DuplicateFinder(files).find_duplicates()
    assert len(duplicates) == 1
    names = {os.path.basename(f['path']) for f in duplicates[0]}
    assert names == {"p.bin", "q.bin"}


def test_empty_files_are_not_duplicates(tmp_path):
    (tmp_path / "empty1.log").write_bytes(b"")
    (tmp_path / "empty2.log").write_bytes(b"")
    (tmp_path / "gitkeep").write_bytes(b"")

    files = FileScanner(str(tmp_path)).scan()
    duplicates = DuplicateFinder(files).find_duplicates()

    assert duplicates == []


def test_include_empty_flag_groups_empty_files(tmp_path):
    (tmp_path / "empty1.log").write_bytes(b"")
    (tmp_path / "empty2.log").write_bytes(b"")

    files = FileScanner(str(tmp_path)).scan()
    duplicates = DuplicateFinder(files, include_empty=True).find_duplicates()

    assert len(duplicates) == 1
    assert len(duplicates[0]) == 2

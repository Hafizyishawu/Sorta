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

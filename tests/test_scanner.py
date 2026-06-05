from sorta.scanner import FileScanner

def test_scan(tmp_path):
    # Create some files
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello")
    f2 = tmp_path / "file2.mp3"
    f2.write_bytes(b"\x00\x01")
    scanner = FileScanner(str(tmp_path))
    files = scanner.scan()
    assert len(files) == 2
    paths = [f['path'] for f in files]
    assert str(f1) in paths
    assert str(f2) in paths


def test_office_lock_and_partial_files_ignored_by_default(tmp_path):
    keep = tmp_path / "Report.docx"
    keep.write_text("real document")
    (tmp_path / "~$Report.docx").write_text("lock")
    (tmp_path / "movie.mp4.crdownload").write_text("partial")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "~$Deep.docx").write_text("nested lock")

    scanner = FileScanner(str(tmp_path))
    names = [f['path'].split("/")[-1] for f in scanner.scan()]

    assert "Report.docx" in names
    assert "~$Report.docx" not in names
    assert "movie.mp4.crdownload" not in names
    assert "~$Deep.docx" not in names

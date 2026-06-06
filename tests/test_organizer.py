import os
from sorta.scanner import FileScanner
from sorta.organizer import FileOrganizer
from sorta.extension_mapper import ExtensionMapper

def test_organization_suggestions(tmp_path):
    # Create files of different types
    f1 = tmp_path / "song.mp3"
    f1.write_bytes(b"audio")
    f2 = tmp_path / "movie.mp4"
    f2.write_bytes(b"video")
    f3 = tmp_path / "doc.pdf"
    f3.write_bytes(b"document")
    f4 = tmp_path / "random.xyz"
    f4.write_bytes(b"other")
    f5 = tmp_path / "budget.xlsx"
    f5.write_bytes(b"sheet")

    scanner = FileScanner(str(tmp_path))
    files = scanner.scan()
    organizer = FileOrganizer(files, str(tmp_path))
    suggestions = organizer.get_organization_suggestions()

    # Document sub-types are now their own categories.
    categories = [s['category'] for s in suggestions]
    assert 'audio' in categories
    assert 'video' in categories
    assert 'pdf' in categories
    assert 'spreadsheet' in categories
    assert all(s['category'] != 'other' for s in suggestions)

    # Check target paths, and that document sub-types nest under Documents/.
    for s in suggestions:
        assert os.path.basename(s['source']) == os.path.basename(s['target'])
        assert os.path.dirname(s['target']).endswith(ExtensionMapper.get_folder(s['category']))
    pdf_target = next(s['target'] for s in suggestions if s['category'] == 'pdf')
    assert os.path.join('Documents', 'PDF') in pdf_target


def test_running_inside_documents_does_not_nest_another_documents(tmp_path):
    # base_dir is itself named "Documents"; it must act as the single Documents
    # parent, so sub-types land directly inside it, not under Documents/Documents.
    base = tmp_path / "Documents"
    base.mkdir()
    (base / "thesis.docx").write_bytes(b"d")
    (base / "scan.pdf").write_bytes(b"p")

    files = FileScanner(str(base)).scan()
    suggestions = FileOrganizer(files, str(base)).get_organization_suggestions()

    targets = [s['target'] for s in suggestions]
    assert all(os.path.join("Documents", "Documents") not in t for t in targets)
    assert str(base / "Word" / "thesis.docx") in targets
    assert str(base / "PDF" / "scan.pdf") in targets


def test_organize_is_idempotent_after_apply(tmp_path):
    # After organizing once, a second pass on the same base produces no further
    # moves: files already sit in their destination, so nothing is re-created.
    base = tmp_path / "Documents"
    base.mkdir()
    (base / "thesis.docx").write_bytes(b"d")
    (base / "scan.pdf").write_bytes(b"p")

    files = FileScanner(str(base)).scan()
    for s in FileOrganizer(files, str(base)).get_organization_suggestions():
        os.makedirs(os.path.dirname(s['target']), exist_ok=True)
        os.rename(s['source'], s['target'])

    files_after = FileScanner(str(base)).scan()
    second_pass = FileOrganizer(files_after, str(base)).get_organization_suggestions()
    assert second_pass == []

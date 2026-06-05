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
    
    scanner = FileScanner(str(tmp_path))
    files = scanner.scan()
    organizer = FileOrganizer(files, str(tmp_path))
    suggestions = organizer.get_organization_suggestions()
    
    # Only known types should be suggested
    categories = [s['category'] for s in suggestions]
    assert 'audio' in categories
    assert 'video' in categories
    assert 'document' in categories
    assert all(s['category'] != 'other' for s in suggestions)
    
    # Check target paths
    for s in suggestions:
        assert os.path.basename(s['source']) == os.path.basename(s['target'])
        assert os.path.dirname(s['target']).endswith(ExtensionMapper.get_folder(s['category']))

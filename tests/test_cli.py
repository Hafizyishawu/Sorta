import builtins
from sorta import cli
from sorta.scanner import FileScanner
from sorta.trash_manager import TrashManager


def test_show_dormant_routes_deletion_through_trash(tmp_path, monkeypatch):
    f = tmp_path / "old.bin"
    f.write_bytes(b"0" * 1024)
    monkeypatch.setattr(builtins, "input", lambda *_: "y")

    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path))
    cli.show_dormant(files, size_threshold=0, days_dormant=0, apply=True, trash_manager=tm)

    assert not f.exists()
    idx = tm.list_trash()
    assert any(meta['original_path'] == str(f) for meta in idx.values())


def test_show_organization_moves_into_category_folder(tmp_path, monkeypatch):
    (tmp_path / "song.mp3").write_bytes(b"audio")
    monkeypatch.setattr(builtins, "input", lambda *_: "y")

    files = FileScanner(str(tmp_path)).scan()
    cli.show_organization(files, str(tmp_path), apply=True)

    assert (tmp_path / "Audio" / "song.mp3").exists()
    assert not (tmp_path / "song.mp3").exists()


def test_prompt_yes_no_defaults_to_no_on_eof(monkeypatch):
    def raise_eof(*_):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    assert cli.prompt_yes_no("Delete?") is False

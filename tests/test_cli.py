import builtins
import os
from sorta import cli
from sorta.scanner import FileScanner
from sorta.trash_manager import TrashManager


def test_show_dormant_routes_deletion_through_trash(tmp_path, monkeypatch):
    f = tmp_path / "old.bin"
    f.write_bytes(b"0" * 1024)
    monkeypatch.setattr(builtins, "input", lambda *_: "y")

    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path), use_os_trash=False)
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


def test_global_flags_accepted_after_subcommand(tmp_path, monkeypatch, capsys):
    # Regression: global flags like --all must parse whether they appear before
    # or after the subcommand. argparse otherwise routes post-subcommand flags
    # to the subparser and rejects them.
    (tmp_path / "a.txt").write_text("x")
    for argv in (
        ["sorta", str(tmp_path), "scan", "--all"],
        ["sorta", str(tmp_path), "--all", "scan"],
        ["sorta", str(tmp_path), "scan", "--json"],
        ["sorta", str(tmp_path), "--limit", "5", "scan"],
    ):
        monkeypatch.setattr("sys.argv", argv)
        cli.main()  # must not raise SystemExit on unrecognized arguments
    assert capsys.readouterr().out


def test_delete_matches_keyword_and_spares_others(tmp_path, monkeypatch):
    (tmp_path / "magentic_report.txt").write_text("x")
    (tmp_path / "apex_data.csv").write_text("y")
    (tmp_path / "keep_me.txt").write_text("z")

    def fail(*_):
        raise AssertionError("no prompt expected under -y")

    monkeypatch.setattr(builtins, "input", fail)
    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    cli.show_delete(files, keywords=["magentic", "apex"], apply=True, trash_manager=tm, assume_yes=True)

    assert not (tmp_path / "magentic_report.txt").exists()
    assert not (tmp_path / "apex_data.csv").exists()
    assert (tmp_path / "keep_me.txt").exists()


def test_dry_run_delete_reports_but_does_not_delete(tmp_path, monkeypatch, capsys):
    target = tmp_path / "apex_thing.log"
    target.write_text("x")

    def fail(*_):
        raise AssertionError("dry-run must not prompt")

    monkeypatch.setattr(builtins, "input", fail)
    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    cli.show_delete(files, keywords=["apex"], apply=True, trash_manager=tm, dry_run=True)

    assert target.exists()
    out = capsys.readouterr().out
    assert "[dry-run] Would delete" in out


def test_dry_run_organization_reports_but_does_not_move(tmp_path, capsys):
    (tmp_path / "song.mp3").write_bytes(b"a")
    files = FileScanner(str(tmp_path)).scan()
    cli.show_organization(files, str(tmp_path), apply=True, dry_run=True)

    assert (tmp_path / "song.mp3").exists()
    assert not (tmp_path / "Audio").exists()
    assert "[dry-run] Would move" in capsys.readouterr().out


def test_delete_preview_does_not_delete(tmp_path, capsys):
    target = tmp_path / "apex_thing.log"
    target.write_text("x")
    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    cli.show_delete(files, keywords=["apex"], apply=False, trash_manager=tm)

    assert target.exists()
    assert "Preview only" in capsys.readouterr().out


def test_delete_refuses_without_keyword(tmp_path, capsys):
    target = tmp_path / "anything.txt"
    target.write_text("x")
    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    cli.show_delete(files, keywords=[], apply=True, trash_manager=tm, assume_yes=True)

    assert target.exists()
    assert "Refusing to delete without a filter" in capsys.readouterr().out


def test_os_trash_mode_calls_send2trash_and_keeps_no_index(tmp_path, monkeypatch):
    import sorta.trash_manager as tmmod
    calls = []
    monkeypatch.setattr(tmmod, "SEND2TRASH_AVAILABLE", True)
    monkeypatch.setattr(tmmod, "_os_send2trash", lambda p: calls.append(p))

    f = tmp_path / "doc.txt"
    f.write_text("x")
    tm = TrashManager(str(tmp_path), use_os_trash=True)
    result = tm.move_to_trash(str(f))

    assert result is None
    assert calls == [os.path.abspath(str(f))]
    # No internal index is created when the OS owns the trashed file.
    assert tm.list_trash() == {}


def test_prompt_yes_no_defaults_to_no_on_eof(monkeypatch):
    def raise_eof(*_):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    assert cli.prompt_yes_no("Delete?") is False


def test_prompt_yes_no_assume_yes_skips_input(monkeypatch):
    def fail(*_):
        raise AssertionError("input() must not be called when assume_yes is set")

    monkeypatch.setattr(builtins, "input", fail)
    assert cli.prompt_yes_no("Delete?", assume_yes=True) is True


def test_assume_yes_deletes_dormant_without_prompting(tmp_path, monkeypatch):
    f = tmp_path / "old.bin"
    f.write_bytes(b"0" * 1024)

    def fail(*_):
        raise AssertionError("no prompt expected under -y")

    monkeypatch.setattr(builtins, "input", fail)
    files = FileScanner(str(tmp_path)).scan()
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    cli.show_dormant(files, size_threshold=0, days_dormant=0, apply=True, trash_manager=tm, assume_yes=True)

    assert not f.exists()
    assert any(meta['original_path'] == str(f) for meta in tm.list_trash().values())

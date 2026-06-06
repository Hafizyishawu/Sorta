import os
from sorta.trash_manager import TrashManager


def test_move_to_trash_removes_original_and_indexes(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("content")
    tm = TrashManager(str(tmp_path), use_os_trash=False)

    trash_path = tm.move_to_trash(str(f))

    assert not f.exists()
    assert os.path.exists(trash_path)
    idx = tm.list_trash()
    assert len(idx) == 1
    trash_name = next(iter(idx))
    assert idx[trash_name]['original_path'] == str(f)


def test_restore_round_trip_returns_file_to_origin(tmp_path):
    f = tmp_path / "sub" / "doc.txt"
    f.parent.mkdir()
    f.write_text("payload")
    tm = TrashManager(str(tmp_path), use_os_trash=False)

    tm.move_to_trash(str(f))
    assert not f.exists()

    trash_name = next(iter(tm.list_trash()))
    restored = tm.restore(trash_name)

    assert restored == str(f)
    assert f.exists()
    assert f.read_text() == "payload"
    assert tm.list_trash() == {}


def test_same_basename_same_second_does_not_collide(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    fa = tmp_path / "a" / "report.pdf"
    fb = tmp_path / "b" / "report.pdf"
    fa.write_text("A")
    fb.write_text("B")
    tm = TrashManager(str(tmp_path), use_os_trash=False)

    tm.move_to_trash(str(fa))
    tm.move_to_trash(str(fb))

    idx = tm.list_trash()
    assert len(idx) == 2
    originals = {meta['original_path'] for meta in idx.values()}
    assert originals == {str(fa), str(fb)}


def test_restore_refuses_to_overwrite_existing_file(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("original")
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    tm.move_to_trash(str(f))
    # A new file appears at the original path before restore.
    f.write_text("newer content")

    trash_name = next(iter(tm.list_trash()))
    try:
        tm.restore(trash_name)
        assert False, "expected ValueError"
    except ValueError:
        pass
    assert f.read_text() == "newer content"


def test_restore_unknown_name_raises(tmp_path):
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    try:
        tm.restore("does-not-exist")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_empty_trash_purges_files_and_index(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("x")
    tm = TrashManager(str(tmp_path), use_os_trash=False)
    trash_path = tm.move_to_trash(str(f))

    tm.empty_trash()

    assert not os.path.exists(trash_path)
    assert tm.list_trash() == {}

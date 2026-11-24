import os
from pathlib import Path
import zipfile

import pytest

from core.engine import FileMatcherEngine


@pytest.mark.parametrize("ids", [("SKU", "SKU-12", "SKU-12_A"), ("SKU-12_A", "SKU-12", "SKU")])
def test_longest_complete_id_wins_regardless_of_order(tmp_path, ids):
    for name in ("SKU-12-front.jpg", "SKU-12_A_front.jpg", "SKU-123.jpg", "SKUX.jpg", "SKU.jpg"):
        (tmp_path / name).write_bytes(b"file")
    engine = FileMatcherEngine()
    matched = engine.match_files(tmp_path, ids, None, False)
    assert {key: {Path(path).name for path in paths}
            for key, paths in matched.items()} == {
        "SKU-12": {"SKU-12-front.jpg"},
        "SKU-12_A": {"SKU-12_A_front.jpg"},
        "SKU": {"SKU.jpg", "SKU-123.jpg"},
    }


def test_rerun_archives_only_new_outputs_and_preserves_previous_run(tmp_path, monkeypatch):
    source = tmp_path / "source"
    dest = source / "dest"
    dest.mkdir(parents=True)
    archive_root = source / "dest_压缩包"
    archive_root.mkdir()
    (dest / "A_old.bin").write_bytes(b"old output")
    (archive_root / "A_legacy.bin").write_bytes(b"not a source")
    for name in ("A_one.bin", "A_two.bin", "B_one.bin"):
        (source / name).write_bytes(os.urandom(600))
    engine = FileMatcherEngine()

    def run(ids, size):
        monkeypatch.setattr(engine, "read_excel_ids", lambda *_: ids)
        return engine.run("ignored.xlsx", 0, str(source), str(dest), None,
                          recursive=True, enable_zip=True, zip_max_size=size)

    assert run(["A"], 700) == (2, 0, 0, [])
    first, = [path for path in archive_root.iterdir() if path.is_dir()]
    assert len(list(first.glob("*.zip"))) == 2

    assert run(["B"], 10000) == (1, 0, 0, [])
    second, = [path for path in archive_root.iterdir() if path.is_dir() and path != first]
    archive, = second.glob("*.zip")
    with zipfile.ZipFile(archive) as zf:
        assert zf.namelist() == ["B_one.bin"]
    assert len(list(first.glob("*.zip"))) == 2
    assert run(["B"], 10000) == (0, 1, 0, [])
    assert len([path for path in archive_root.iterdir() if path.is_dir()]) == 2


def test_archive_write_failure_leaves_no_published_directory(tmp_path, monkeypatch):
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "one.bin").write_bytes(b"data")
    def fail(*args, **kwargs):
        raise OSError("disk failure")
    monkeypatch.setattr(zipfile.ZipFile, "write", fail)
    with pytest.raises(OSError, match="disk failure"):
        FileMatcherEngine().create_zip_archives(str(dest), 1000, ["one.bin"])
    assert not list((tmp_path / "dest_压缩包").iterdir())

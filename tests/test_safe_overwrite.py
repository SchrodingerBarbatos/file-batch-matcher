"""覆盖前先准备替换文件，失败时不破坏源文件或旧目标。"""

import os
import shutil

import openpyxl
import pytest
from PIL import Image

from core.engine import FileMatcherEngine


@pytest.fixture
def job(tmp_path):
    src_dir = tmp_path / 'src'
    dst_dir = tmp_path / 'dst'
    src_dir.mkdir()
    dst_dir.mkdir()
    src = src_dir / '123_photo.png'
    dst = dst_dir / src.name
    Image.new('RGB', (3, 3), 'red').save(dst)
    excel = tmp_path / 'ids.xlsx'
    book = openpyxl.Workbook()
    book.active.append(['ID'])
    book.active.append(['123'])
    book.save(excel)

    engine = FileMatcherEngine(log_callback=lambda _message: None)

    def run(**kwargs):
        return engine.run(str(excel), 'A', str(src_dir), str(dst_dir),
                          {'.png'}, **kwargs)

    return src, dst, engine, run


@pytest.mark.parametrize('move', [False, True])
@pytest.mark.parametrize('overwrite', [False, True])
def test_empty_source_leaves_existing_destination(job, move, overwrite):
    src, dst, _, run = job
    src.touch()
    original = dst.read_bytes()

    expected = (0, 0, 1, []) if overwrite else (0, 1, 0, [])
    assert run(overwrite=overwrite, move_mode=move) == expected
    assert dst.read_bytes() == original
    assert src.is_file() and src.stat().st_size == 0
    assert list(dst.parent.iterdir()) == [dst]


@pytest.mark.parametrize('move', [False, True])
def test_valid_source_replaces_existing_destination(job, move):
    src, dst, _, run = job
    Image.new('RGB', (3, 3), 'blue').save(src)
    replacement = src.read_bytes()

    assert run(overwrite=True, move_mode=move) == (1, 0, 0, [])
    assert dst.read_bytes() == replacement
    assert src.exists() is not move
    assert list(dst.parent.iterdir()) == [dst]


@pytest.mark.parametrize('stage', ['copy', 'normalize', 'publish', 'resize', 'convert'])
def test_stage_failure_keeps_source_and_destination(job, monkeypatch, stage):
    src, dst, engine, run = job
    Image.new('RGB', (3, 3), 'blue').save(src, format='BMP' if stage == 'convert' else 'PNG')
    original = dst.read_bytes()
    source = src.read_bytes()

    def fail(*args):
        raise OSError('injected I/O failure')

    if stage == 'copy':
        def fail_after_partial_write(_src, staged):
            with open(staged, 'wb') as stream:
                stream.write(b'partial')
            raise OSError('injected copy failure')
        monkeypatch.setattr(shutil, 'copy2', fail_after_partial_write)
    elif stage == 'normalize':
        monkeypatch.setattr(engine, 'normalize_image_file', fail)
    elif stage == 'publish':
        monkeypatch.setattr(os, 'replace', fail)
    elif stage == 'resize':
        monkeypatch.setattr(engine, 'process_image', lambda *args: False)
    elif stage == 'convert':
        monkeypatch.setattr(engine, 'convert_image_format', lambda path, target: path)

    assert run(overwrite=True, move_mode=True, enable_resize=stage == 'resize',
               enable_convert=stage == 'convert') == (0, 0, 1, [])
    assert dst.read_bytes() == original
    assert src.read_bytes() == source
    assert list(dst.parent.iterdir()) == [dst]


def test_changed_suffix_preserves_other_destination(job):
    src, dst, _, run = job
    Image.new('RGB', (3, 3), 'blue').save(src, format='JPEG')
    replacement = src.read_bytes()
    other = dst.with_suffix('.jpg')
    Image.new('RGB', (3, 3), 'green').save(other)
    unrelated = other.read_bytes()

    assert run(overwrite=True, move_mode=True) == (1, 0, 0, [])
    assert not dst.exists()
    assert not src.exists()
    assert other.read_bytes() == unrelated
    assert dst.with_name('123_photo_1.jpg').read_bytes() == replacement


def test_conversion_and_resize_before_publication(job):
    src, dst, _, run = job
    Image.new('RGB', (3, 3), 'blue').save(src, format='BMP')

    assert run(overwrite=True, move_mode=True, enable_convert=True, enable_resize=True,
               max_width=8, max_height=6, target_format='PNG') == (1, 0, 0, [])
    assert not src.exists()
    with Image.open(dst) as image:
        assert image.format == 'PNG'
        assert image.size == (8, 6)
        assert image.getpixel((0, 0)) == (0, 0, 255)


def test_move_refuses_to_delete_source_hard_link(job):
    src, dst, _, run = job
    original = dst.read_bytes()
    try:
        os.link(dst, src)
    except OSError:
        pytest.skip('hard links are not supported on this filesystem')

    assert run(overwrite=True, move_mode=True) == (0, 1, 0, [])
    assert src.read_bytes() == original
    assert dst.read_bytes() == original


def test_cancel_during_staging_preserves_both_files(job, monkeypatch):
    src, dst, engine, run = job
    Image.new('RGB', (3, 3), 'blue').save(src)
    original = dst.read_bytes()
    source = src.read_bytes()
    normalize = engine.normalize_image_file

    def normalize_then_stop(path):
        result = normalize(path)
        engine.stop_event.set()
        return result

    monkeypatch.setattr(engine, 'normalize_image_file', normalize_then_stop)
    assert run(overwrite=True, move_mode=True) == (0, 0, 0, [])
    assert src.read_bytes() == source
    assert dst.read_bytes() == original
    assert list(dst.parent.iterdir()) == [dst]

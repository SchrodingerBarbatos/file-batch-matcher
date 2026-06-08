# -*- coding: utf-8 -*-
"""图片格式标准化 / 格式转换 / 打包过滤 的回归测试。"""

import os
import zipfile

import pytest
from PIL import Image

from core.engine import FileMatcherEngine


@pytest.fixture
def engine():
    """创建一个日志收集到列表的引擎实例。"""
    logs = []
    eng = FileMatcherEngine(log_callback=logs.append)
    eng._logs = logs
    return eng


@pytest.fixture
def tmp_dir(tmp_path):
    return str(tmp_path)


def _save_jpeg(path):
    """创建一个合法的 JPEG 文件。"""
    img = Image.new('RGB', (10, 10), color='red')
    img.save(path, format='JPEG')


def _save_png(path):
    """创建一个合法的 PNG 文件（带透明通道）。"""
    img = Image.new('RGBA', (10, 10), color=(0, 255, 0, 128))
    img.save(path, format='PNG')


# ---- normalize_image_file ----


class TestNormalizeImageFile:
    """normalize_image_file 的测试。"""

    def test_fake_jpg_with_png_content(self, engine, tmp_dir):
        """后缀 .jpg 但实际内容是 PNG → 修正为 .png。"""
        path = os.path.join(tmp_dir, "photo.jpg")
        _save_png(path)

        new_path, status, real_fmt = engine.normalize_image_file(path)

        assert status == 'fixed'
        assert real_fmt == 'PNG'
        assert new_path.endswith('.png')
        assert os.path.isfile(new_path)
        assert not os.path.exists(path)  # 原路径已重命名
        # 验证修正后文件仍可正常读取为 PNG
        with Image.open(new_path) as img:
            assert img.format == 'PNG'

    def test_fake_png_with_jpeg_content(self, engine, tmp_dir):
        """后缀 .png 但实际内容是 JPEG → 修正为 .jpg。"""
        path = os.path.join(tmp_dir, "image.png")
        _save_jpeg(path)

        new_path, status, real_fmt = engine.normalize_image_file(path)

        assert status == 'fixed'
        assert real_fmt == 'JPEG'
        assert new_path.endswith('.jpg')
        assert os.path.isfile(new_path)
        assert not os.path.exists(path)
        with Image.open(new_path) as img:
            assert img.format == 'JPEG'

    def test_zero_byte_file(self, engine, tmp_dir):
        """0 字节图片 → 返回 zero_byte 状态。"""
        path = os.path.join(tmp_dir, "empty.jpg")
        with open(path, 'wb'):
            pass  # 0 bytes

        new_path, status, real_fmt = engine.normalize_image_file(path)

        assert status == 'zero_byte'
        assert real_fmt is None
        assert os.path.exists(path)  # 文件不被删除
        assert any("0 字节" in log for log in engine._logs)

    def test_correct_suffix_no_change(self, engine, tmp_dir):
        """后缀与真实格式一致 → 返回 ok，不做任何修改。"""
        path = os.path.join(tmp_dir, "valid.jpg")
        _save_jpeg(path)

        new_path, status, real_fmt = engine.normalize_image_file(path)

        assert status == 'ok'
        assert real_fmt == 'JPEG'
        assert new_path == path
        assert os.path.isfile(path)

    def test_non_image_file_skipped(self, engine, tmp_dir):
        """非图片文件 → skipped，不做修改。"""
        path = os.path.join(tmp_dir, "readme.txt")
        with open(path, 'w') as f:
            f.write("hello")

        new_path, status, real_fmt = engine.normalize_image_file(path)

        assert status == 'skipped'
        assert real_fmt is None
        assert new_path == path

    def test_corrupted_image_skipped(self, engine, tmp_dir):
        """损坏的图片文件（数据截断）→ 被识别为真实格式或跳过。"""
        path = os.path.join(tmp_dir, "corrupted.jpg")
        # 写入合法 JPEG 头部但截断数据
        with open(path, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00')

        new_path, status, real_fmt = engine.normalize_image_file(path)
        # Pillow 可能仍能从头部识别格式（JPEG），也可能无法识别
        # 无论哪种情况，不应崩溃
        assert status in ('ok', 'skipped', 'fixed')


# ---- convert_image_format ----


class TestConvertImageFormat:
    """convert_image_format 的测试 — 标准格式绝不互转。"""

    def test_real_png_with_png_ext_target_jpeg_no_change(self, engine, tmp_dir):
        """规则 1: 真实 PNG + .png + target JPEG → 不转换，仍是 .png。"""
        src = os.path.join(tmp_dir, "photo.png")
        _save_png(src)
        src_size = os.path.getsize(src)

        result = engine.convert_image_format(src, 'JPEG')

        assert result == src  # 路径不变
        assert os.path.getsize(result) == src_size
        with Image.open(result) as img:
            assert img.format == 'PNG'

    def test_real_jpeg_with_jpg_ext_target_png_no_change(self, engine, tmp_dir):
        """规则 2: 真实 JPEG + .jpg + target PNG → 不转换，仍是 .jpg。"""
        src = os.path.join(tmp_dir, "photo.jpg")
        _save_jpeg(src)
        src_size = os.path.getsize(src)

        result = engine.convert_image_format(src, 'PNG')

        assert result == src
        assert os.path.getsize(result) == src_size
        with Image.open(result) as img:
            assert img.format == 'JPEG'

    def test_real_png_with_jpg_ext_fixes_suffix_only(self, engine, tmp_dir):
        """规则 3a: 真实 PNG + .jpg → 只修正为 .png，不转 JPEG。"""
        src = os.path.join(tmp_dir, "fake.jpg")
        _save_png(src)
        src_size = os.path.getsize(src)

        result = engine.convert_image_format(src, 'JPEG')

        assert result.endswith('.png')
        assert os.path.isfile(result)
        assert not os.path.exists(src)
        # 仅 rename，不应转码，文件大小不变
        assert os.path.getsize(result) == src_size
        with Image.open(result) as img:
            assert img.format == 'PNG'

    def test_real_jpeg_with_png_ext_fixes_suffix_only(self, engine, tmp_dir):
        """规则 3b: 真实 JPEG + .png → 只修正为 .jpg，不转 PNG。"""
        src = os.path.join(tmp_dir, "fake.png")
        _save_jpeg(src)
        src_size = os.path.getsize(src)

        result = engine.convert_image_format(src, 'PNG')

        assert result.endswith('.jpg')
        assert os.path.isfile(result)
        assert not os.path.exists(src)
        assert os.path.getsize(result) == src_size
        with Image.open(result) as img:
            assert img.format == 'JPEG'

    def test_bmp_to_jpeg(self, engine, tmp_dir):
        """规则 4: 真实 BMP + target JPEG → 转成 .jpg。"""
        src = os.path.join(tmp_dir, "image.bmp")
        img = Image.new('RGB', (10, 10), color='blue')
        img.save(src, format='BMP')

        result = engine.convert_image_format(src, 'JPEG')

        assert result.endswith('.jpg')
        assert os.path.isfile(result)
        assert not os.path.exists(src)
        with Image.open(result) as img:
            assert img.format == 'JPEG'

    def test_bmp_to_png(self, engine, tmp_dir):
        """规则 4: 真实 BMP + target PNG → 转成 .png。"""
        src = os.path.join(tmp_dir, "image.bmp")
        img = Image.new('RGB', (10, 10), color='green')
        img.save(src, format='BMP')

        result = engine.convert_image_format(src, 'PNG')

        assert result.endswith('.png')
        assert os.path.isfile(result)
        assert not os.path.exists(src)
        with Image.open(result) as img:
            assert img.format == 'PNG'

    def test_webp_to_jpeg(self, engine, tmp_dir):
        """规则 4: 真实 WebP + target JPEG → 转成 .jpg。"""
        src = os.path.join(tmp_dir, "image.webp")
        img = Image.new('RGB', (10, 10), color='red')
        img.save(src, format='WEBP')

        result = engine.convert_image_format(src, 'JPEG')

        assert result.endswith('.jpg')
        assert os.path.isfile(result)
        assert not os.path.exists(src)
        with Image.open(result) as img:
            assert img.format == 'JPEG'

    def test_already_correct_skips(self, engine, tmp_dir):
        """真实 JPEG + .jpg → 不论 target_format，直接返回。"""
        src = os.path.join(tmp_dir, "correct.jpg")
        _save_jpeg(src)

        result = engine.convert_image_format(src, 'JPEG')

        assert result == src
        assert os.path.isfile(src)


# ---- create_zip_archives 过滤 ----


class TestZipFiltering:
    """create_zip_archives 过滤问题图片的测试。"""

    def test_zero_byte_blocked_from_zip(self, engine, tmp_dir):
        """0 字节文件不进入压缩包。"""
        _save_jpeg(os.path.join(tmp_dir, "good.jpg"))
        with open(os.path.join(tmp_dir, "empty.bin"), 'wb'):
            pass  # 0 bytes

        engine.create_zip_archives(tmp_dir, max_zip_size=10_000_000)

        archive_dir = tmp_dir + "_压缩包"
        assert os.path.isdir(archive_dir)
        zips = [f for f in os.listdir(archive_dir) if f.endswith('.zip')]
        assert len(zips) == 1

        with zipfile.ZipFile(os.path.join(archive_dir, zips[0])) as zf:
            names = zf.namelist()
            assert "good.jpg" in names
            assert "empty.bin" not in names
        assert any("0 字节" in log and "empty.bin" in log for log in engine._logs)

    def test_fake_suffix_blocked_from_zip(self, engine, tmp_dir):
        """后缀与真实格式不一致的图片不进入压缩包。"""
        _save_jpeg(os.path.join(tmp_dir, "ok.jpg"))
        fake = os.path.join(tmp_dir, "fake.jpg")
        _save_png(fake)  # PNG 内容，.jpg 后缀

        engine.create_zip_archives(tmp_dir, max_zip_size=10_000_000)

        archive_dir = tmp_dir + "_压缩包"
        zips = [f for f in os.listdir(archive_dir) if f.endswith('.zip')]
        with zipfile.ZipFile(os.path.join(archive_dir, zips[0])) as zf:
            names = zf.namelist()
            assert "ok.jpg" in names
            assert "fake.jpg" not in names
        assert any("后缀不一致" in log and "fake.jpg" in log for log in engine._logs)

    def test_non_image_files_pass_through(self, engine, tmp_dir):
        """非图片文件不受后缀检查影响，正常打包。"""
        _save_jpeg(os.path.join(tmp_dir, "photo.jpg"))
        with open(os.path.join(tmp_dir, "data.csv"), 'w') as f:
            f.write("a,b,c")

        engine.create_zip_archives(tmp_dir, max_zip_size=10_000_000)

        archive_dir = tmp_dir + "_压缩包"
        zips = [f for f in os.listdir(archive_dir) if f.endswith('.zip')]
        with zipfile.ZipFile(os.path.join(archive_dir, zips[0])) as zf:
            names = zf.namelist()
            assert "photo.jpg" in names
            assert "data.csv" in names

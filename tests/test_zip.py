# -*- coding: utf-8 -*-
"""压缩打包逻辑的单元测试。"""

import os
import tempfile
import threading
import zipfile

import pytest

from core.engine import FileMatcherEngine


@pytest.fixture
def engine():
    """创建一个日志收集到列表的引擎实例。"""
    logs = []
    eng = FileMatcherEngine(log_callback=logs.append)
    eng._logs = logs  # 供测试断言用
    return eng


@pytest.fixture
def tmp_dir(tmp_path):
    """返回一个临时目录路径。"""
    return str(tmp_path)


def _create_files(directory, names_and_sizes):
    """在目录中创建指定名称和大小的测试文件。"""
    for name, size in names_and_sizes:
        path = os.path.join(directory, name)
        with open(path, 'wb') as f:
            f.write(os.urandom(size))


class TestCreateZipArchives:
    """create_zip_archives 方法的测试。"""

    def test_single_zip_no_split(self, engine, tmp_dir):
        """文件总大小未超过限制时，只生成一个压缩包。"""
        _create_files(tmp_dir, [("a.txt", 100), ("b.txt", 200)])
        engine.create_zip_archives(tmp_dir, max_zip_size=10000)

        archive_dir = tmp_dir + "_压缩包"
        assert os.path.isdir(archive_dir)
        zips = [f for f in os.listdir(archive_dir) if f.endswith('.zip')]
        assert len(zips) == 1

        # 验证 zip 内容
        with zipfile.ZipFile(os.path.join(archive_dir, zips[0])) as zf:
            assert set(zf.namelist()) == {"a.txt", "b.txt"}

    def test_split_when_exceeding_size(self, engine, tmp_dir):
        """文件超过大小限制时，自动分卷。"""
        # 创建两个 600 字节的文件，限制 1000 字节
        _create_files(tmp_dir, [("a.bin", 600), ("b.bin", 600)])
        engine.create_zip_archives(tmp_dir, max_zip_size=1000)

        archive_dir = tmp_dir + "_压缩包"
        zips = sorted(f for f in os.listdir(archive_dir) if f.endswith('.zip'))
        assert len(zips) >= 2

        # 所有文件都应该在某个 zip 中
        all_names = set()
        for z in zips:
            with zipfile.ZipFile(os.path.join(archive_dir, z)) as zf:
                all_names.update(zf.namelist())
        assert all_names == {"a.bin", "b.bin"}

    def test_empty_directory(self, engine, tmp_dir):
        """空目录应输出提示信息，不创建压缩包。"""
        engine.create_zip_archives(tmp_dir, max_zip_size=10000)
        assert any("没有文件" in log for log in engine._logs)
        archive_dir = tmp_dir + "_压缩包"
        assert not os.path.exists(archive_dir)

    def test_abort_cleans_up_partial_zip(self, engine, tmp_dir):
        """中止时应删除未完成的压缩包。"""
        # 创建多个小文件，确保有时间触发中止
        files = [(f"f{i}.bin", 100) for i in range(10)]
        _create_files(tmp_dir, files)

        # 在压缩开始前设置 stop_event
        engine.stop_event.set()
        engine.create_zip_archives(tmp_dir, max_zip_size=100000)

        archive_dir = tmp_dir + "_压缩包"
        # 应该已清理不完整的压缩包
        if os.path.exists(archive_dir):
            zips = [f for f in os.listdir(archive_dir) if f.endswith('.zip')]
            assert len(zips) == 0
        # 日志应提示已停止
        assert any("已停止" in log for log in engine._logs)

    def test_large_file_warning(self, engine, tmp_dir):
        """单个文件超过限制时应输出警告。"""
        _create_files(tmp_dir, [("huge.bin", 2000)])
        engine.create_zip_archives(tmp_dir, max_zip_size=1000)
        assert any("警告" in log and "huge.bin" in log for log in engine._logs)

    def test_progress_output(self, engine, tmp_dir):
        """文件数量 >= 50 时应输出进度。"""
        files = [(f"f{i}.bin", 10) for i in range(55)]
        _create_files(tmp_dir, files)
        engine.create_zip_archives(tmp_dir, max_zip_size=100000000)

        progress_logs = [l for l in engine._logs if "进度" in l]
        assert len(progress_logs) >= 1
        assert any("50/" in l for l in progress_logs)
        assert any("55/" in l for l in progress_logs)

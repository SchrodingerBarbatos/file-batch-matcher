# -*- coding: utf-8 -*-
"""
核心业务逻辑：Excel 读取、文件匹配、图片处理、格式转换。
与 UI 完全解耦，可独立使用。
"""

import os
import re
import shutil
import tempfile
import threading
import zipfile
from collections import defaultdict
from datetime import datetime

import pandas as pd
from PIL import Image


class FileMatcherEngine:
    """文件匹配复制引擎，纯业务逻辑，不含任何 UI 代码。"""

    def __init__(self, log_callback=None, stop_event=None, progress_callback=None):
        self.log_callback = log_callback or print
        self.stop_event = stop_event or threading.Event()
        self.progress_callback = progress_callback

    def log(self, message):
        self.log_callback(str(message))

    def _update_progress(self, processed, total):
        """更新进度并通知回调。"""
        if self.progress_callback and total > 0:
            self.progress_callback(int(processed / total * 100))

    # ---- 格式探测 / 标准化 ----

    # Pillow Image.format → 规范扩展名
    _FORMAT_TO_EXT = {
        'JPEG': '.jpg',
        'PNG': '.png',
        'WEBP': '.webp',
        'BMP': '.bmp',
        'GIF': '.gif',
        'TIFF': '.tiff',
        'AVIF': '.avif',
    }

    @staticmethod
    def detect_real_format(path):
        """用 Pillow 探测图片真实格式，返回 (pil_format, canonical_ext) 或 (None, None)。"""
        try:
            if os.path.getsize(path) == 0:
                return None, None
            with Image.open(path) as img:
                fmt = img.format
                ext = FileMatcherEngine._FORMAT_TO_EXT.get(fmt)
                if ext:
                    return fmt, ext
                return None, None
        except (IOError, OSError, SyntaxError, ValueError, KeyError):
            return None, None

    @staticmethod
    def _safe_rename(old_path, new_path):
        """安全重命名：目标已存在时自动追加计数器后缀。"""
        if not os.path.exists(new_path) or os.path.abspath(old_path) == os.path.abspath(new_path):
            os.rename(old_path, new_path)
            return new_path
        base, ext = os.path.splitext(new_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        new_path = f"{base}_{counter}{ext}"
        os.rename(old_path, new_path)
        return new_path

    def normalize_image_file(self, path):
        """标准化图片文件：0 字节报错，伪后缀修正。

        Returns:
            (new_path, status, real_fmt) — status 为 'ok', 'skipped', 'zero_byte', 'fixed'。
            real_fmt 为 Pillow 格式字符串（如 'JPEG'），非图片时为 None。
        """
        if not os.path.isfile(path):
            return path, 'skipped', None

        if os.path.getsize(path) == 0:
            self.log(f"[错误] 0 字节文件，已跳过: {os.path.basename(path)}")
            return path, 'zero_byte', None

        real_fmt, canonical_ext = self.detect_real_format(path)

        if real_fmt is None:
            # 非可识别图片，原样跳过
            return path, 'skipped', None

        current_ext = os.path.splitext(path)[1].lower()
        if current_ext == canonical_ext:
            return path, 'ok', real_fmt

        # 修正后缀
        base = os.path.splitext(path)[0]
        new_path = self._safe_rename(path, base + canonical_ext)
        self.log(f"[后缀修正] {os.path.basename(path)} -> {os.path.basename(new_path)} "
                 f"(真实格式: {real_fmt})")
        return new_path, 'fixed', real_fmt

    # ---- Excel 相关 ----

    @staticmethod
    def get_excel_engine(excel_path):
        ext = os.path.splitext(excel_path)[1].lower()
        if ext == '.xlsx':
            return 'openpyxl'
        if ext == '.xls':
            return 'xlrd'
        return None

    @staticmethod
    def read_excel(excel_path):
        engine = FileMatcherEngine.get_excel_engine(excel_path)
        if engine:
            return pd.read_excel(excel_path, engine=engine, dtype=str)
        return pd.read_excel(excel_path, dtype=str)

    @staticmethod
    def index_to_excel_letter(index):
        result = ""
        index += 1
        while index:
            index, rem = divmod(index - 1, 26)
            result = chr(65 + rem) + result
        return result

    @staticmethod
    def parse_column(column_str, display_to_name=None):
        column_str = column_str.strip()
        if display_to_name and column_str in display_to_name:
            return display_to_name[column_str]
        try:
            return int(column_str)
        except ValueError:
            pass
        if column_str.isalpha() and column_str.isascii():
            idx = 0
            for char in column_str.upper():
                idx = idx * 26 + (ord(char) - ord('A') + 1)
            return idx - 1
        return column_str

    @staticmethod
    def normalize_id(value):
        if value is None:
            return ""
        text = str(value).strip()
        if not text or text.lower() == 'nan':
            return ""
        if re.fullmatch(r'\d+\.0', text):
            text = text[:-2]
        return text

    def read_excel_ids(self, excel_path, column, display_to_name=None):
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")

        df = self.read_excel(excel_path)
        col_id = self.parse_column(column, display_to_name)

        if isinstance(col_id, int):
            if col_id < 0 or col_id >= len(df.columns):
                raise IndexError(f"列索引 {col_id} 超出范围，共 {len(df.columns)} 列。")
            series = df.iloc[:, col_id]
        else:
            if col_id not in df.columns:
                raise KeyError(f"列名 '{col_id}' 不存在。可用列名: {list(df.columns)}")
            series = df[col_id]

        seen = set()
        unique_ids = []
        for value in series.tolist():
            num = self.normalize_id(value)
            if num and num not in seen:
                seen.add(num)
                unique_ids.append(num)
        return unique_ids

    def load_column_names(self, excel_path):
        """加载 Excel 列名，返回 (choices, display_to_name) 列表。"""
        if not excel_path or not os.path.exists(excel_path):
            return [], {}
        try:
            df = self.read_excel(excel_path)
            columns = list(df.columns)
            choices = []
            display_to_name = {}
            for i, col in enumerate(columns):
                letter = self.index_to_excel_letter(i)
                display = f"{letter} (索引{i}) {col}"
                choices.append(display)
                display_to_name[display] = col
            return choices, display_to_name
        except ImportError:
            if excel_path.lower().endswith('.xls'):
                raise ImportError("读取 .xls 文件需要安装 xlrd：pip install xlrd")
            raise

    # ---- 文件匹配 ----

    @staticmethod
    def build_extensions(ext_text, no_ext_filter=False):
        if no_ext_filter:
            return None
        ext_text = ext_text.strip()
        if not ext_text:
            return None
        return {ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in ext_text.split()}

    def iter_files(self, src_dir, recursive, excluded_dirs=()):
        if recursive:
            excluded = {os.path.normcase(os.path.realpath(path)) for path in excluded_dirs}
            for root, directories, files in os.walk(src_dir):
                directories[:] = [name for name in directories
                                  if os.path.normcase(os.path.realpath(os.path.join(root, name))) not in excluded]
                if self.stop_event.is_set():
                    return
                for filename in files:
                    yield root, filename
        else:
            with os.scandir(src_dir) as entries:
                for entry in entries:
                    if self.stop_event.is_set():
                        return
                    if entry.is_file():
                        yield src_dir, entry.name

    def match_files(self, src_dir, ids, extensions, recursive, excluded_dirs=()):
        id_set = set(ids)
        matched = defaultdict(list)

        for root, filename in self.iter_files(src_dir, recursive, excluded_dirs):
            if self.stop_event.is_set():
                break

            if extensions:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in extensions:
                    continue

            # Prefer the longest complete ID, independent of Excel row order.
            # Test only possible boundaries, not every ID for every file.
            for end in range(len(filename), 0, -1):
                if end == len(filename) or not filename[end].isalnum():
                    prefix = filename[:end]
                    if prefix in id_set:
                        matched[prefix].append(os.path.join(root, filename))
                        break

        return matched

    # ---- 图片处理 ----

    def process_image(self, image_path, max_w=800, max_h=800, max_size=5000000):
        """安全处理图片：调整尺寸（拉伸到目标尺寸）、压缩大小。"""
        tmp_path = None
        try:
            if max_w <= 0 or max_h <= 0 or max_size <= 0:
                raise ValueError("宽、高、最大大小必须大于 0")

            # 用真实格式决定保存方式，而非文件后缀
            real_fmt, canonical_ext = self.detect_real_format(image_path)
            if real_fmt is None:
                raise ValueError("无法识别图片格式")
            save_format = real_fmt

            original_size = os.path.getsize(image_path)

            with Image.open(image_path) as img:
                # 仅 800×800 精确匹配且文件大小符合要求时跳过
                if img.width == max_w and img.height == max_h and original_size <= max_size:
                    self.log(f"[图片跳过] 尺寸与大小均符合要求: {os.path.basename(image_path)}")
                    return True

                # 直接拉伸到目标尺寸
                img = img.resize((max_w, max_h), Image.LANCZOS)

                # 按真实格式处理透明通道
                if save_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif save_format == 'JPEG' and img.mode != 'RGB':
                    img = img.convert('RGB')

                tmp_path = image_path + ".tmp"

                if save_format == 'PNG':
                    img.save(tmp_path, format='PNG', optimize=True)
                    png_size = os.path.getsize(tmp_path)
                    if png_size <= 0:
                        raise RuntimeError("临时文件大小为 0，已取消替换原图")
                    # 文件大小符合要求，直接替换
                    if png_size <= max_size:
                        os.replace(tmp_path, image_path)
                    elif img.mode in ('RGBA', 'LA', 'RGB', 'P'):
                        # 通过颜色量化（降为调色板模式）压缩 PNG
                        quantized = False
                        for colors in (256, 128, 64, 32):
                            q_img = img.quantize(colors=colors, method=2)
                            q_img.save(tmp_path, format='PNG', optimize=True)
                            q_size = os.path.getsize(tmp_path)
                            if q_size <= max_size:
                                os.replace(tmp_path, image_path)
                                quantized = True
                                self.log(f"[图片压缩] PNG 量化至 {colors} 色: "
                                         f"{os.path.basename(image_path)} ({png_size/1000:.0f}KB → {q_size/1000:.0f}KB)")
                                return True
                        # 量化到最小仍超限，使用最小量化结果
                        if not quantized:
                            os.replace(tmp_path, image_path)
                            self.log(f"[图片警告] PNG 即使量化到 32 色仍超出目标: "
                                     f"{os.path.basename(image_path)} ({q_size/1000:.0f}KB > {max_size/1000:.0f}KB)")
                    else:
                        os.replace(tmp_path, image_path)
                        self.log(f"[图片警告] PNG 格式无法压缩到目标大小: "
                                 f"{os.path.basename(image_path)} ({png_size/1000:.0f}KB > {max_size/1000:.0f}KB)")
                    self.log(f"[图片处理] {os.path.basename(image_path)}")
                    return True

                quality = 95
                while quality >= 20:
                    if save_format == 'JPEG':
                        img.save(tmp_path, format='JPEG', quality=quality, optimize=True)
                    elif save_format == 'WEBP':
                        img.save(tmp_path, format='WEBP', quality=quality, method=6)
                    else:
                        img.save(tmp_path, format=save_format)
                        break  # 无损格式不支持 quality 压缩，无需循环

                    if os.path.getsize(tmp_path) <= max_size:
                        break
                    quality -= 5

                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    os.replace(tmp_path, image_path)
                else:
                    raise RuntimeError("临时文件保存失败或大小为 0，已取消替换原图")

            self.log(f"[图片处理] {os.path.basename(image_path)}")
            return True

        except Exception as e:
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            self.log(f"[错误] 图片处理失败 {os.path.basename(image_path)}: {e}")
            return False

    def convert_image_format(self, image_path, target_format):
        """转换图片格式：修正伪后缀 / 非标准格式转码到目标格式。

        规则：
        - 真实格式是 JPEG/PNG：绝不跨格式转码，后缀错误时只修正后缀。
        - 真实格式非标准（BMP/WEBP/GIF/TIFF/AVIF）：按 target_format 转码。
        """
        tmp_path = None
        try:
            real_fmt, canonical_ext = self.detect_real_format(image_path)
            if real_fmt is None:
                self.log(f"[格式跳过] 无法识别的图片: {os.path.basename(image_path)}")
                return image_path

            if target_format not in ('JPEG', 'PNG'):
                self.log(f"[格式跳过] 不支持的目标格式: {target_format}")
                return image_path

            current_ext = os.path.splitext(image_path)[1].lower()

            # 真实格式是 JPEG/PNG：绝不跨格式转码，只修正后缀
            if real_fmt in ('JPEG', 'PNG'):
                if current_ext == canonical_ext:
                    self.log(f"[格式跳过] {real_fmt} 格式无需转换: {os.path.basename(image_path)}")
                    return image_path
                base = os.path.splitext(image_path)[0]
                new_path = self._safe_rename(image_path, base + canonical_ext)
                self.log(f"[后缀修正] {os.path.basename(image_path)} -> {os.path.basename(new_path)}")
                return new_path

            # 真实格式非标准：按 target_format 转码
            target_ext = '.jpg' if target_format == 'JPEG' else '.png'
            with Image.open(image_path) as img:
                base = os.path.splitext(image_path)[0]
                new_path = base + target_ext

                if target_format == 'JPEG':
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                tmp_path = new_path + ".tmp"

                if target_format == 'JPEG':
                    img.save(tmp_path, format='JPEG', quality=95, optimize=True)
                elif target_format == 'PNG':
                    img.save(tmp_path, format='PNG', optimize=True)

                if os.path.getsize(tmp_path) > 0:
                    os.replace(tmp_path, new_path)
                    if image_path != new_path and os.path.exists(image_path):
                        os.remove(image_path)
                    self.log(f"[格式转换] {os.path.basename(image_path)} ({real_fmt}) -> {os.path.basename(new_path)}")
                    return new_path
                else:
                    raise RuntimeError("转换后文件大小为 0")

        except Exception as e:
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            self.log(f"[错误] 格式转换失败 {os.path.basename(image_path)}: {e}")
            return image_path

    # ---- 压缩打包 ----

    def create_zip_archives(self, dst_dir, max_zip_size, filenames):
        """Archive this run's published files in a new directory, never older output."""
        dst_dir = os.path.normpath(dst_dir)
        files = []
        for name in sorted(set(filenames)):
            if name in (".", "..") or name != os.path.basename(name):
                raise ValueError("打包文件名必须是目标文件夹内的文件名")
            path = os.path.join(dst_dir, name)
            if not os.path.isfile(path):
                continue
            if not os.path.getsize(path):
                self.log(f"[压缩] 跳过 0 字节文件: {name}")
                continue
            real_fmt, _ = self.detect_real_format(path)
            canonical_ext = self._FORMAT_TO_EXT.get(real_fmt)
            if canonical_ext and os.path.splitext(name)[1].lower() != canonical_ext:
                self.log(f"[压缩] 跳过后缀不一致的图片: {name}")
                continue
            files.append(name)

        if not files:
            self.log("[压缩] 本次没有新文件需要打包")
            return None

        archive_dir = dst_dir + "_压缩包"
        os.makedirs(archive_dir, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".打包中-", dir=archive_dir) as staging:
            output = os.path.join(staging, "volumes")
            os.mkdir(output)
            zip_index = 1
            zip_path = os.path.join(output, f"output_{zip_index}.zip")
            current_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
            try:
                for i, filename in enumerate(files):
                    if self.stop_event.is_set():
                        self.log("[压缩] 已停止打包，未发布本次压缩包")
                        return None
                    filepath = os.path.join(dst_dir, filename)
                    file_size = os.path.getsize(filepath)
                    if file_size > max_zip_size:
                        self.log(f"[压缩] 警告: {filename} ({file_size / 1000000:.1f}MB) 超过单包限制")

                    actual_size = current_zip.fp.tell()
                    if actual_size > 0 and actual_size + file_size > max_zip_size:
                        current_zip.close()
                        zip_index += 1
                        zip_path = os.path.join(output, f"output_{zip_index}.zip")
                        current_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
                    current_zip.write(filepath, filename)
                    if (i + 1) % 50 == 0 or i + 1 == len(files):
                        self.log(f"[压缩] 进度: {i + 1}/{len(files)}")
            finally:
                current_zip.close()

            if self.stop_event.is_set():
                self.log("[压缩] 已停止打包，未发布本次压缩包")
                return None
            run_name = datetime.now().strftime("任务_%Y%m%d_%H%M%S_%f") + "_" + os.path.basename(staging).split("-", 1)[-1]
            run_dir = os.path.join(archive_dir, run_name)
            os.rename(output, run_dir)
        self.log(f"[压缩] 共生成 {zip_index} 个压缩包，保存在: {run_dir}")
        return run_dir

    # ---- 主处理流程 ----

    def _stage_and_publish(self, src_path, dst_path, overwrite, enable_convert,
                           target_format, enable_resize, max_width, max_height, max_size):
        """在目标目录的临时区准备文件；处理成功后才发布。"""
        filename = os.path.basename(dst_path)
        if os.path.getsize(src_path) == 0:
            self.log(f"[错误] 0 字节文件，已跳过: {filename}")
            return 'error', None

        dst_dir = os.path.dirname(dst_path)
        with tempfile.TemporaryDirectory(prefix='.matcher-', dir=dst_dir) as stage_dir:
            staged = os.path.join(stage_dir, filename)
            shutil.copy2(src_path, staged)
            staged, norm_status, real_fmt = self.normalize_image_file(staged)
            if norm_status == 'zero_byte':
                return 'error', None

            if enable_convert and real_fmt:
                normalized = staged
                staged = self.convert_image_format(staged, target_format)
                if (staged == normalized and real_fmt not in ('JPEG', 'PNG')
                        and target_format in ('JPEG', 'PNG')):
                    return 'error', None
                real_fmt, _ = self.detect_real_format(staged)

            if (enable_resize and real_fmt in ('JPEG', 'PNG', 'WEBP')
                    and not self.process_image(staged, max_width, max_height, max_size)):
                return 'error', None
            if not os.path.isfile(staged) or os.path.getsize(staged) == 0:
                raise OSError("待发布文件不存在或为空")
            if self.stop_event.is_set():
                return 'stopped', None

            final_path = os.path.join(dst_dir, os.path.basename(staged))
            same_name = os.path.normcase(final_path) == os.path.normcase(dst_path)
            old_destination = os.path.lexists(dst_path)
            if old_destination:
                if not overwrite:
                    self.log(f"[跳过] 目标已存在: {filename}")
                    return 'skipped', None
                if not os.path.isfile(dst_path):
                    raise OSError("目标路径不是文件，无法覆盖")

            if not same_name:
                # 改后缀时，不覆盖另一张已存在的图片。
                base, ext = os.path.splitext(final_path)
                index = 1
                while os.path.lexists(final_path):
                    final_path = f"{base}_{index}{ext}"
                    index += 1

            os.replace(staged, final_path)
            if not same_name and old_destination:
                # 新文件已落盘后，才清理旧后缀的目标文件。
                os.remove(dst_path)
        return 'ok', os.path.basename(final_path)

    def run(self, excel_path, column, src_dir, dst_dir, extensions,
            recursive=False, move_mode=False, overwrite=False,
            enable_resize=False, max_width=800, max_height=800, max_size=5000000,
            enable_convert=False, target_format="JPEG",
            enable_zip=False, zip_max_size=100 * 1000 * 1000,
            display_to_name=None):
        """
        主处理流程：读取 Excel -> 匹配文件 -> 复制/移动 -> 格式转换 -> 图片处理 -> 压缩打包。
        返回 (success, skipped, errors, unmatched_ids)。
        """
        # 防止源目录和目标目录相同导致数据丢失
        if os.path.normcase(os.path.realpath(src_dir)) == os.path.normcase(os.path.realpath(dst_dir)):
            if move_mode:
                self.log("[错误] 源文件夹与目标文件夹相同，移动模式会删除源文件，已取消操作。")
                return 0, 0, 0, []
            self.log("[警告] 源文件夹与目标文件夹相同，文件不会被复制。")

        self.log("正在读取 Excel 编号...")
        ids = self.read_excel_ids(excel_path, column, display_to_name)
        if self.stop_event.is_set():
            return 0, 0, 0, []
        if not ids:
            self.log("未找到有效编号，处理结束。")
            return 0, 0, 0, []
        self.log(f"共读取到 {len(ids)} 个唯一编号。")

        self.log("正在匹配文件...")
        matched = self.match_files(src_dir, ids, extensions, recursive,
                                   (dst_dir, os.path.normpath(dst_dir) + "_压缩包"))
        if self.stop_event.is_set():
            return 0, 0, 0, []

        matched_ids = set(matched.keys())
        unmatched = [num for num in ids if num not in matched_ids]
        total_files = sum(len(files) for files in matched.values())

        self.log(
            f"匹配统计：参与编号 {len(ids)}，匹配到 {len(matched_ids)} 个编号，"
            f"未匹配 {len(unmatched)} 个编号，匹配文件总数 {total_files}"
        )

        if unmatched:
            self.log("未匹配的编号（前10个）：")
            for num in unmatched[:10]:
                self.log(f"  {num}")
            if len(unmatched) > 10:
                self.log(f"  ... 共 {len(unmatched)} 个未匹配")

        if not matched:
            self.log("没有匹配到任何文件。")
            return 0, 0, 0, unmatched

        os.makedirs(dst_dir, exist_ok=True)
        success = 0
        skipped = 0
        errors = 0
        processed = 0
        published = set()

        for _, files in matched.items():
            for src_path in files:
                if self.stop_event.is_set():
                    self.log("已停止复制/移动。")
                    return success, skipped, errors, unmatched

                filename = os.path.basename(src_path)
                dst_path = os.path.join(dst_dir, filename)

                try:
                    if os.path.lexists(dst_path) and (
                            not overwrite or (os.path.exists(dst_path) and os.path.samefile(src_path, dst_path))):
                        self.log(f"[跳过] 目标已存在或与源文件相同: {filename}")
                        skipped += 1
                    else:
                        result, output_name = self._stage_and_publish(
                            src_path, dst_path, overwrite, enable_convert, target_format,
                            enable_resize, max_width, max_height, max_size)
                        if result == 'ok':
                            published.add(output_name)
                            if move_mode:
                                os.remove(src_path)
                                self.log(f"[移动] {filename}")
                            else:
                                self.log(f"[复制] {filename}")
                            success += 1
                        elif result == 'stopped':
                            self.log("已停止复制/移动。")
                            return success, skipped, errors, unmatched
                        elif result == 'skipped':
                            skipped += 1
                        else:
                            errors += 1
                except Exception as e:
                    self.log(f"[错误] 处理 {filename} 失败: {e}")
                    errors += 1

                processed += 1
                self._update_progress(processed, total_files)

        # 压缩打包
        if enable_zip and not self.stop_event.is_set():
            self.log("正在压缩打包...")
            try:
                self.create_zip_archives(dst_dir, zip_max_size, published)
            except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                self.log(f"[错误] 打包失败，未发布本次压缩包: {exc}")
                errors += 1

        self.log(f"操作完成：成功 {success}，跳过 {skipped}，错误 {errors}")
        return success, skipped, errors, unmatched

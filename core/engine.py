# -*- coding: utf-8 -*-
"""
核心业务逻辑：Excel 读取、文件匹配、图片处理、格式转换。
与 UI 完全解耦，可独立使用。
"""

import os
import re
import shutil
import threading
import zipfile
from collections import defaultdict

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

    def iter_files(self, src_dir, recursive):
        if recursive:
            for root, _, files in os.walk(src_dir):
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

    def match_files(self, src_dir, ids, extensions, recursive):
        id_set = set(ids)
        matched = defaultdict(list)

        for root, filename in self.iter_files(src_dir, recursive):
            if self.stop_event.is_set():
                break

            if extensions:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in extensions:
                    continue

            prefix = filename.split('_', 1)[0]
            if prefix in id_set:
                matched[prefix].append(os.path.join(root, filename))
                continue

            for num in ids:
                if filename.startswith(num):
                    # 确保编号后紧跟分隔符或文件结尾，避免误匹配
                    # 如 "123" 不应匹配 "12345_photo.jpg"
                    if len(filename) == len(num) or not filename[len(num)].isalnum():
                        matched[num].append(os.path.join(root, filename))
                        break

        return matched

    # ---- 图片处理 ----

    def process_image(self, image_path, max_w=800, max_h=800, max_size=5000000):
        """安全处理图片：调整尺寸（保持宽高比）、压缩大小。"""
        tmp_path = None
        try:
            if max_w <= 0 or max_h <= 0 or max_size <= 0:
                raise ValueError("宽、高、最大大小必须大于 0")

            ext = os.path.splitext(image_path)[1].lower()
            original_size = os.path.getsize(image_path)

            with Image.open(image_path) as img:
                # 使用 thumbnail 保持宽高比缩放
                img.thumbnail((max_w, max_h), Image.LANCZOS)

                dimension_ok = (img.width <= max_w and img.height <= max_h)
                size_ok = original_size <= max_size

                if dimension_ok and size_ok:
                    self.log(f"[图片跳过] 已符合要求: {os.path.basename(image_path)}")
                    return True

                if ext in ['.jpg', '.jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif ext in ['.jpg', '.jpeg'] and img.mode != 'RGB':
                    img = img.convert('RGB')

                tmp_path = image_path + ".tmp"

                if ext == '.png':
                    img.save(tmp_path, format='PNG', optimize=True)
                    if os.path.getsize(tmp_path) > 0:
                        os.replace(tmp_path, image_path)
                    else:
                        raise RuntimeError("临时文件大小为 0，已取消替换原图")
                    self.log(f"[图片处理] {os.path.basename(image_path)}")
                    return True

                quality = 95
                while quality >= 20:
                    if ext in ['.jpg', '.jpeg']:
                        img.save(tmp_path, format='JPEG', quality=quality, optimize=True)
                    elif ext == '.webp':
                        img.save(tmp_path, format='WEBP', quality=quality, method=6)
                    else:
                        img.save(tmp_path, format=img.format or 'PNG')
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
        """转换图片格式：非标准格式转为 JPEG/PNG。"""
        tmp_path = None
        try:
            with Image.open(image_path) as img:
                real_format = img.format

                # jpg/jpeg/png 已是常见格式，跳过转换
                if real_format in ('JPEG', 'PNG'):
                    self.log(f"[格式跳过] 已是常见格式: {os.path.basename(image_path)} ({real_format})")
                    return image_path

                base_name = os.path.splitext(image_path)[0]

                # 确定目标扩展名
                if target_format == 'JPEG':
                    new_ext = '.jpg'
                elif target_format == 'PNG':
                    new_ext = '.png'
                else:
                    self.log(f"[格式跳过] 不支持的目标格式: {target_format}")
                    return image_path

                new_path = base_name + new_ext

                # 转换为 JPEG 时处理透明度
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

                # 保存为目标格式
                if target_format == 'JPEG':
                    img.save(tmp_path, format='JPEG', quality=95, optimize=True)
                elif target_format == 'PNG':
                    img.save(tmp_path, format='PNG', optimize=True)

                if os.path.getsize(tmp_path) > 0:
                    os.replace(tmp_path, new_path)
                    if image_path != new_path and os.path.exists(image_path):
                        os.remove(image_path)
                    self.log(f"[格式转换] {os.path.basename(image_path)} ({real_format}) -> {os.path.basename(new_path)}")
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

    def create_zip_archives(self, dst_dir, max_zip_size):
        """将目标文件夹打包为 zip，超过大小限制时自动分卷。"""
        files = [f for f in os.listdir(dst_dir) if os.path.isfile(os.path.join(dst_dir, f))]
        if not files:
            self.log("[压缩] 没有文件需要打包")
            return

        archive_dir = dst_dir + "_压缩包"
        os.makedirs(archive_dir, exist_ok=True)

        zip_index = 1
        zip_path = os.path.join(archive_dir, f"output_{zip_index}.zip")
        current_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        total = len(files)

        aborted = False
        try:
            for i, filename in enumerate(sorted(files)):
                if self.stop_event.is_set():
                    aborted = True
                    self.log("[压缩] 用户中止，正在清理...")
                    break

                filepath = os.path.join(dst_dir, filename)
                file_size = os.path.getsize(filepath)

                # 单个文件超过大小限制时输出警告
                if file_size > max_zip_size:
                    self.log(f"[压缩] 警告: {filename} ({file_size / 1000000:.1f}MB) 超过单包限制，压缩包大小将超出预期")

                # 基于 zip 文件实际已写入大小判断是否需要分卷
                actual_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
                if actual_size > 0 and actual_size + file_size > max_zip_size:
                    current_zip.close()
                    self.log(f"[压缩] 已生成: {os.path.basename(zip_path)}")
                    zip_index += 1
                    zip_path = os.path.join(archive_dir, f"output_{zip_index}.zip")
                    current_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

                current_zip.write(filepath, filename)

                # 每 50 个文件输出一次进度
                if (i + 1) % 50 == 0 or i + 1 == total:
                    self.log(f"[压缩] 进度: {i + 1}/{total}")
        finally:
            current_zip.close()
            if aborted:
                # 删除当前未完成的压缩包
                try:
                    os.remove(zip_path)
                except OSError:
                    pass
                self.log("[压缩] 已停止打包，已清理未完成的压缩包")
                return

        self.log(f"[压缩] 已生成: {os.path.basename(zip_path)}")
        self.log(f"[压缩] 共生成 {zip_index} 个压缩包，保存在: {archive_dir}")

    # ---- 主处理流程 ----

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
        if os.path.abspath(src_dir) == os.path.abspath(dst_dir):
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
        matched = self.match_files(src_dir, ids, extensions, recursive)
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

        for _, files in matched.items():
            for src_path in files:
                if self.stop_event.is_set():
                    self.log("已停止复制/移动。")
                    return success, skipped, errors, unmatched

                filename = os.path.basename(src_path)
                dst_path = os.path.join(dst_dir, filename)

                if os.path.exists(dst_path):
                    if not overwrite:
                        self.log(f"[跳过] 目标已存在: {filename}")
                        skipped += 1
                        processed += 1
                        self._update_progress(processed, total_files)
                        continue
                    try:
                        if os.path.isfile(dst_path):
                            os.remove(dst_path)
                        else:
                            self.log(f"[错误] 目标路径不是文件，无法覆盖: {filename}")
                            errors += 1
                            processed += 1
                            self._update_progress(processed, total_files)
                            continue
                    except Exception as e:
                        self.log(f"[错误] 删除旧文件失败 {filename}: {e}")
                        errors += 1
                        processed += 1
                        self._update_progress(processed, total_files)
                        continue

                try:
                    if move_mode:
                        shutil.move(src_path, dst_path)
                        self.log(f"[移动] {filename}")
                    else:
                        shutil.copy2(src_path, dst_path)
                        self.log(f"[复制] {filename}")

                    if enable_convert:
                        ext = os.path.splitext(dst_path)[1].lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.avif']:
                            dst_path = self.convert_image_format(dst_path, target_format)

                    if enable_resize:
                        ext = os.path.splitext(dst_path)[1].lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                            self.process_image(dst_path, max_width, max_height, max_size)

                    success += 1
                except Exception as e:
                    self.log(f"[错误] 处理 {filename} 失败: {e}")
                    errors += 1

                processed += 1
                self._update_progress(processed, total_files)

        # 压缩打包
        if enable_zip and not self.stop_event.is_set() and (success > 0 or skipped > 0):
            self.log("正在压缩打包...")
            self.create_zip_archives(dst_dir, zip_max_size)

        self.log(f"操作完成：成功 {success}，跳过 {skipped}，错误 {errors}")
        return success, skipped, errors, unmatched

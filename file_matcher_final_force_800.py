#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图形界面版本：根据 Excel 指定列中的编号，批量匹配源文件夹中的文件，并复制/移动到目标文件夹。

核心功能：
1. 读取 Excel 指定列，自动跳过表头。
2. 将编号按字符串读取，避免长数字变成科学计数法或 .0。
3. 匹配源文件夹中文件名以编号开头的文件。
4. 支持复制/移动、递归搜索、扩展名过滤、覆盖、终止任务。
5. 使用线程执行耗时任务，并通过队列安全更新 Tkinter 日志。
"""

import os
import re
import shutil
import threading
import queue
from collections import defaultdict

import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image


DEFAULT_IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.svg'}


class FileMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件批量匹配复制工具")
        self.root.geometry("760x700")
        self.root.resizable(True, True)

        self.excel_path = tk.StringVar()
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.column_var = tk.StringVar()
        self.ext_var = tk.StringVar(value=".jpg .jpeg .png .bmp .webp")
        self.recursive_var = tk.BooleanVar(value=False)
        self.move_var = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.no_ext_filter_var = tk.BooleanVar(value=False)

        # 图片处理
        self.enable_resize_var = tk.BooleanVar(value=False)
        self.max_width_var = tk.StringVar(value="800")
        self.max_height_var = tk.StringVar(value="800")
        self.max_size_var = tk.StringVar(value="5000000")

        # 格式转换
        self.enable_convert_var = tk.BooleanVar(value=False)
        self.target_format_var = tk.StringVar(value="JPEG")

        self.thread = None
        self.running = False
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.unmatched_ids = []
        self.column_display_to_name = {}

        self.setup_ui()
        self.root.after(100, self.process_log_queue)

    # ---------------- UI ----------------
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.LabelFrame(main_frame, text="文件与路径设置", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(file_frame, text="Excel 文件:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(file_frame, textvariable=self.excel_path, width=50).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self.browse_excel).grid(row=0, column=2, padx=5, pady=2)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="编号所在列:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.column_combo = ttk.Combobox(file_frame, textvariable=self.column_var, width=47)
        self.column_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Label(file_frame, text="支持索引0开始、列字母A/B、或列名", font=("", 8)).grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)

        ttk.Label(file_frame, text="源文件夹:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(file_frame, textvariable=self.src_dir, width=50).grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self.browse_src).grid(row=2, column=2, padx=5, pady=2)

        ttk.Label(file_frame, text="目标文件夹:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(file_frame, textvariable=self.dst_dir, width=50).grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self.browse_dst).grid(row=3, column=2, padx=5, pady=2)

        option_frame = ttk.LabelFrame(main_frame, text="匹配选项", padding="5")
        option_frame.pack(fill=tk.X, pady=(0, 5))

        ext_frame = ttk.Frame(option_frame)
        ext_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ext_frame, text="允许的扩展名:").pack(side=tk.LEFT, padx=5)
        self.ext_entry = ttk.Entry(ext_frame, textvariable=self.ext_var, width=40)
        self.ext_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Label(ext_frame, text="空格分隔，如 .jpg .png", font=("", 8)).pack(side=tk.LEFT, padx=5)

        self.no_ext_cb = ttk.Checkbutton(
            option_frame,
            text="不限制扩展名（匹配所有文件）",
            variable=self.no_ext_filter_var,
            command=self.toggle_ext_entry,
        )
        self.no_ext_cb.pack(anchor=tk.W, padx=5, pady=2)

        cb_frame = ttk.Frame(option_frame)
        cb_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(cb_frame, text="递归搜索子文件夹", variable=self.recursive_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(cb_frame, text="移动文件（默认复制）", variable=self.move_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(cb_frame, text="目标存在时覆盖", variable=self.overwrite_var).pack(side=tk.LEFT, padx=5)

        img_frame = ttk.LabelFrame(option_frame, text="图片处理", padding="5")
        img_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            img_frame,
            text="启用图片尺寸/大小处理",
            variable=self.enable_resize_var
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2, columnspan=6)

        ttk.Label(img_frame, text="宽:").grid(row=1, column=0, padx=5)
        ttk.Entry(img_frame, textvariable=self.max_width_var, width=8).grid(row=1, column=1)

        ttk.Label(img_frame, text="高:").grid(row=1, column=2, padx=5)
        ttk.Entry(img_frame, textvariable=self.max_height_var, width=8).grid(row=1, column=3)

        ttk.Label(img_frame, text="最大大小(bytes):").grid(row=1, column=4, padx=5)
        ttk.Entry(img_frame, textvariable=self.max_size_var, width=12).grid(row=1, column=5)

        # 格式转换
        ttk.Checkbutton(
            img_frame,
            text="启用格式转换",
            variable=self.enable_convert_var
        ).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2, columnspan=2)

        ttk.Label(img_frame, text="目标格式:").grid(row=2, column=2, padx=5)
        format_combo = ttk.Combobox(img_frame, textvariable=self.target_format_var, values=["JPEG", "PNG"], width=8, state="readonly")
        format_combo.grid(row=2, column=3, padx=5)
        format_combo.current(0)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        self.run_btn = ttk.Button(btn_frame, text="开始匹配并复制", command=self.start_process)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="终止", command=self.stop_process, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.progress = ttk.Progressbar(btn_frame, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        output_frame = ttk.LabelFrame(main_frame, text="运行日志与结果", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.log_text = scrolledtext.ScrolledText(output_frame, height=12, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(bottom_frame, text="保存未匹配编号到文件", command=self.save_unmatched).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="清空日志", command=lambda: self.log_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)

        self.excel_path.trace_add('write', lambda *args: self.load_column_names())

    def browse_excel(self):
        path = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if path:
            self.excel_path.set(path)

    def browse_src(self):
        path = filedialog.askdirectory(title="选择源文件夹")
        if path:
            self.src_dir.set(path)

    def browse_dst(self):
        path = filedialog.askdirectory(title="选择目标文件夹")
        if path:
            self.dst_dir.set(path)

    def toggle_ext_entry(self):
        self.ext_entry.config(state=tk.DISABLED if self.no_ext_filter_var.get() else tk.NORMAL)

    # ---------------- 日志：线程安全 ----------------
    def log(self, message):
        self.log_queue.put(str(message))

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    # ---------------- Excel 相关 ----------------
    def get_excel_engine(self, excel_path):
        ext = os.path.splitext(excel_path)[1].lower()
        if ext == '.xlsx':
            return 'openpyxl'
        if ext == '.xls':
            return 'xlrd'
        return None

    def read_excel(self, excel_path):
        engine = self.get_excel_engine(excel_path)
        if engine:
            return pd.read_excel(excel_path, engine=engine, dtype=str)
        return pd.read_excel(excel_path, dtype=str)

    def load_column_names(self):
        path = self.excel_path.get().strip()
        if not path or not os.path.exists(path):
            return
        try:
            df = self.read_excel(path)
            columns = list(df.columns)
            choices = []
            self.column_display_to_name.clear()

            for i, col in enumerate(columns):
                letter = self.index_to_excel_letter(i)
                display = f"{letter} (索引{i}) {col}"
                choices.append(display)
                self.column_display_to_name[display] = col

            self.column_combo['values'] = choices
            if choices:
                self.column_combo.current(0)
        except ImportError as e:
            if path.lower().endswith('.xls'):
                messagebox.showerror("缺少依赖", "读取 .xls 文件需要安装 xlrd：\npip install xlrd")
            else:
                messagebox.showerror("缺少依赖", f"读取 Excel 失败：{e}")
        except Exception as e:
            messagebox.showwarning("提示", f"读取列名失败：{e}")

    @staticmethod
    def index_to_excel_letter(index):
        result = ""
        index += 1
        while index:
            index, rem = divmod(index - 1, 26)
            result = chr(65 + rem) + result
        return result

    def parse_column(self, column_str):
        column_str = column_str.strip()
        if column_str in self.column_display_to_name:
            return self.column_display_to_name[column_str]

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
        # 兼容 Excel 把长编号当数字读取后出现的 .0
        if re.fullmatch(r'\d+\.0', text):
            text = text[:-2]
        return text

    def read_excel_ids(self, excel_path, column):
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")

        df = self.read_excel(excel_path)
        col_id = self.parse_column(column)

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

    # ---------------- 匹配与复制 ----------------
    def build_extensions(self):
        if self.no_ext_filter_var.get():
            return None
        ext_text = self.ext_var.get().strip()
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

            # 先按下划线切分，可快速覆盖 2900000079960_1_2.jpg 这种格式
            prefix = filename.split('_', 1)[0]
            if prefix in id_set:
                matched[prefix].append(os.path.join(root, filename))
                continue

            # 兜底：兼容 2900000079960abc.jpg 这种“以编号开头”的文件名
            for num in ids:
                if filename.startswith(num):
                    matched[num].append(os.path.join(root, filename))
                    break

        return matched

    def start_process(self):
        if self.running:
            messagebox.showwarning("警告", "任务正在运行中")
            return

        excel = self.excel_path.get().strip()
        column = self.column_var.get().strip()
        src = self.src_dir.get().strip()
        dst = self.dst_dir.get().strip()

        if not excel:
            messagebox.showerror("错误", "请选择 Excel 文件")
            return
        if not column:
            messagebox.showerror("错误", "请输入或选择列标识")
            return
        if not src:
            messagebox.showerror("错误", "请选择源文件夹")
            return
        if not dst:
            messagebox.showerror("错误", "请选择目标文件夹")
            return
        if not os.path.isdir(src):
            messagebox.showerror("错误", "源文件夹不存在")
            return

        extensions = self.build_extensions()

        self.running = True
        self.stop_event.clear()
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start(10)
        self.log_text.delete(1.0, tk.END)
        self.unmatched_ids = []
        self.log("开始处理...")

        self.thread = threading.Thread(
            target=self.process_thread,
            args=(excel, column, src, dst, extensions),
            daemon=True,
        )
        self.thread.start()
        self.check_thread()

    def stop_process(self):
        if not self.running:
            return
        self.stop_event.set()
        self.log("收到终止请求，正在安全停止...")
        self.stop_btn.config(state=tk.DISABLED)

    def reset_ui(self):
        self.running = False
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress.stop()

    def check_thread(self):
        if self.thread and self.thread.is_alive():
            self.root.after(100, self.check_thread)
        else:
            self.reset_ui()
            if self.stop_event.is_set():
                self.log("任务已终止。")
            else:
                self.log("处理完毕。")

    def process_thread(self, excel, column, src, dst, extensions):
        try:
            self.log("正在读取 Excel 编号...")
            ids = self.read_excel_ids(excel, column)
            if self.stop_event.is_set():
                return
            if not ids:
                self.log("未找到有效编号，处理结束。")
                return
            self.log(f"共读取到 {len(ids)} 个唯一编号。")

            self.log("正在匹配文件...")
            matched = self.match_files(src, ids, extensions, self.recursive_var.get())
            if self.stop_event.is_set():
                return

            matched_ids = set(matched.keys())
            unmatched = [num for num in ids if num not in matched_ids]
            total_files = sum(len(files) for files in matched.values())
            self.unmatched_ids = unmatched

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
                return

            os.makedirs(dst, exist_ok=True)
            move_mode = self.move_var.get()
            overwrite = self.overwrite_var.get()
            success = 0
            skipped = 0
            errors = 0

            for _, files in matched.items():
                for src_path in files:
                    if self.stop_event.is_set():
                        self.log("已停止复制/移动。")
                        return

                    filename = os.path.basename(src_path)
                    dst_path = os.path.join(dst, filename)

                    if os.path.exists(dst_path):
                        if not overwrite:
                            self.log(f"[跳过] 目标已存在: {filename}")
                            skipped += 1
                            continue
                        try:
                            if os.path.isfile(dst_path):
                                os.remove(dst_path)
                            else:
                                self.log(f"[错误] 目标路径不是文件，无法覆盖: {filename}")
                                errors += 1
                                continue
                        except Exception as e:
                            self.log(f"[错误] 删除旧文件失败 {filename}: {e}")
                            errors += 1
                            continue

                    try:
                        if move_mode:
                            shutil.move(src_path, dst_path)
                            self.log(f"[移动] {filename}")
                        else:
                            shutil.copy2(src_path, dst_path)
                            self.log(f"[复制] {filename}")

                        # 格式转换（如果启用）
                        if self.enable_convert_var.get():
                            ext = os.path.splitext(dst_path)[1].lower()
                            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.avif']:
                                dst_path = self.convert_image_format(dst_path, self.target_format_var.get())

                        # 图片尺寸/大小处理（如果启用）
                        if self.enable_resize_var.get():
                            ext = os.path.splitext(dst_path)[1].lower()
                            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                                self.process_image(dst_path)

                        success += 1
                    except Exception as e:
                        self.log(f"[错误] 处理 {filename} 失败: {e}")
                        errors += 1

            self.log(f"操作完成：成功 {success}，跳过 {skipped}，错误 {errors}")
        except ImportError as e:
            self.log(f"缺少依赖: {e}")
            self.log("如果读取 .xls 文件失败，请安装：pip install xlrd")
        except Exception as e:
            self.log(f"发生异常: {e}")


    def process_image(self, image_path):
        """
        安全处理图片：
        1. 不直接覆盖原文件，先写入临时文件；
        2. 临时文件保存成功且大小大于 0 后，再替换原文件；
        3. 如果图片本身已满足尺寸和大小要求，则不处理，避免无意义重写；
        4. 避免 JPG 遇到 RGBA/透明通道时报错导致 0KB。
        """
        tmp_path = None
        try:
            max_w = int(self.max_width_var.get())
            max_h = int(self.max_height_var.get())
            max_size = int(self.max_size_var.get())

            if max_w <= 0 or max_h <= 0 or max_size <= 0:
                raise ValueError("宽、高、最大大小必须大于 0")

            original_size = os.path.getsize(image_path)
            ext = os.path.splitext(image_path)[1].lower()

            with Image.open(image_path) as img:
                # 只有尺寸和大小都完全符合才跳过
                dimension_ok = (
                    img.width == max_w and
                    img.height == max_h
                )

                size_ok = original_size <= max_size

                if dimension_ok and size_ok:
                    self.log(f"[图片跳过] 已符合要求: {os.path.basename(image_path)}")
                    return True

                img = img.copy()

                # 强制修改为指定尺寸
                img = img.resize((max_w, max_h), Image.LANCZOS)

                # JPG 不支持透明通道，必须转 RGB
                if ext in ['.jpg', '.jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif ext in ['.jpg', '.jpeg'] and img.mode != 'RGB':
                    img = img.convert('RGB')

                tmp_path = image_path + ".tmp" + ext

                # PNG 基本无法靠 quality 明显压缩，保存一次即可
                if ext == '.png':
                    img.save(tmp_path, optimize=True)
                    if os.path.getsize(tmp_path) > 0:
                        os.replace(tmp_path, image_path)
                    else:
                        raise RuntimeError("临时文件大小为 0，已取消替换原图")
                    self.log(f"[图片处理] {os.path.basename(image_path)}")
                    return True

                # JPG / WEBP 逐步降低质量，直到小于限制或达到最低质量
                quality = 95
                last_good_tmp = None

                while quality >= 20:
                    if ext in ['.jpg', '.jpeg']:
                        img.save(tmp_path, quality=quality, optimize=True)
                    elif ext == '.webp':
                        img.save(tmp_path, quality=quality, method=6)
                    else:
                        img.save(tmp_path)

                    if os.path.getsize(tmp_path) <= max_size:
                        last_good_tmp = tmp_path
                        break

                    quality -= 5

                # 即使无法压到目标大小，也保留最后一次非 0KB 的处理结果
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    os.replace(tmp_path, image_path)
                else:
                    raise RuntimeError("临时文件保存失败或大小为 0，已取消替换原图")

            self.log(f"[图片处理] {os.path.basename(image_path)}")
            return True

        except Exception as e:
            # 出错时删除临时文件，不动原图
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            self.log(f"[错误] 图片处理失败 {os.path.basename(image_path)}: {e}")
            return False

    def convert_image_format(self, image_path, target_format):
        """
        转换图片格式：
        1. 使用 img.format 获取真实格式，避免伪装扩展名
        2. JPEG/PNG 保持不变
        3. 其他格式转换为目标格式
        """
        tmp_path = None
        try:
            with Image.open(image_path) as img:
                real_format = img.format  # 获取真实格式

                # 标准格式不转换
                if real_format in ['JPEG', 'PNG']:
                    self.log(f"[格式跳过] 已是标准格式: {os.path.basename(image_path)} ({real_format})")
                    return image_path

                # 非标准格式转换
                base_name = os.path.splitext(image_path)[0]

                if target_format == 'JPEG':
                    new_ext = '.jpg'
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                else:  # PNG
                    new_ext = '.png'

                new_path = base_name + new_ext
                tmp_path = new_path + ".tmp" + new_ext

                if target_format == 'JPEG':
                    img.save(tmp_path, quality=95, optimize=True)
                else:
                    img.save(tmp_path, optimize=True)

                if os.path.getsize(tmp_path) > 0:
                    os.replace(tmp_path, new_path)
                    # 删除原文件（如果扩展名不同）
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

    def save_unmatched(self):
        if not self.unmatched_ids:
            messagebox.showinfo("提示", "没有未匹配的编号可保存。")
            return
        filepath = filedialog.asksaveasfilename(
            title="保存未匹配编号",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for num in self.unmatched_ids:
                    f.write(num + '\n')
            self.log(f"未匹配编号已保存到: {filepath}")
            messagebox.showinfo("成功", f"已保存到 {filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")


def main():
    root = tk.Tk()
    FileMatcherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

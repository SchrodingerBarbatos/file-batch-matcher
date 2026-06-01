# -*- coding: utf-8 -*-
"""QThread 工作线程"""

import traceback

from PySide6.QtCore import QThread, Signal


class WorkerThread(QThread):
    """后台工作线程，执行匹配复制任务。"""
    finished_signal = Signal()
    log_signal = Signal(str)
    progress_signal = Signal(int)

    def __init__(self, engine, kwargs):
        super().__init__()
        self.engine = engine
        self.kwargs = kwargs
        self.result = None  # 存储引擎返回值
        # 设置进度回调（保留原有回调）
        original_callback = self.engine.progress_callback

        def combined_callback(p):
            if original_callback:
                original_callback(p)
            self.progress_signal.emit(p)

        self.engine.progress_callback = combined_callback

    def run(self):
        try:
            self.result = self.engine.run(**self.kwargs)
        except Exception as e:
            self.log_signal.emit(f"\n[错误] {e}")
            self.log_signal.emit(traceback.format_exc())
        finally:
            self.finished_signal.emit()

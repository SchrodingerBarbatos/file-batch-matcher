# -*- coding: utf-8 -*-
"""QThread 工作线程"""

from PySide6.QtCore import QThread, Signal


class WorkerThread(QThread):
    """后台工作线程，执行匹配复制任务。"""
    finished_signal = Signal()
    log_signal = Signal(str)

    def __init__(self, engine, kwargs):
        super().__init__()
        self.engine = engine
        self.kwargs = kwargs
        self.result = None  # 存储引擎返回值

    def run(self):
        try:
            self.result = self.engine.run(**self.kwargs)
        except Exception as e:
            self.log_signal.emit(f"\n[错误] {e}")
            import traceback
            self.log_signal.emit(traceback.format_exc())
        finally:
            self.finished_signal.emit()

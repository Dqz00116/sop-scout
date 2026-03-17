"""
全局取消标志管理器

用于在 GraphService 和节点之间共享取消状态。
"""
import threading
from typing import Dict

class CancelManager:
    """全局取消标志管理器"""

    def __init__(self):
        self.cancelled_runs: Dict[str, bool] = {}
        self.lock = threading.Lock()

    def mark_cancelled(self, run_id: str):
        """标记某个 run_id 为已取消"""
        with self.lock:
            self.cancelled_runs[run_id] = True

    def is_cancelled(self, run_id: str) -> bool:
        """检查某个 run_id 是否已被取消"""
        with self.lock:
            return self.cancelled_runs.get(run_id, False)

    def clear(self, run_id: str):
        """清除某个 run_id 的取消标志"""
        with self.lock:
            self.cancelled_runs.pop(run_id, None)

# 全局单例
cancel_manager = CancelManager()
